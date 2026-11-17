import json
import re
from playwright.sync_api import sync_playwright

def formatear_pesos(valor):
    return f"${int(round(valor)):,}".replace(",", ".")

def es_producto_limpio(nombre, slug):
    texto = f"{nombre} {slug}".lower()
    prohibidos = ["reacondicionado", "refurbished", "usado", "exhibicion", "open box", "seminuevo"]
    if any(p in texto for p in prohibidos):
        return False
    if "-mp-" in slug.lower():
        return False
    return True

def extraer_precio_tarjeta_exito(commertial_offer, precio_oferta):
    """
    Extrae ÚNICAMENTE el descuento explícito de Tarjeta Éxito.
    Ignora Addi, Puntos Colombia u otros medios para evitar precios cruzados.
    """
    precio_tarjeta = None
    for teaser in commertial_offer.get("teasers", []):
        nombre_teaser = str(teaser.get("name", "")).lower()
        # Filtramos estrictamente promociones de Tarjeta Éxito (exito1 / tarjeta exito)
        if ("tarjeta" in nombre_teaser and "exito" in nombre_teaser) or "exito1" in nombre_teaser:
            if "addi" in nombre_teaser:
                continue
            for param in teaser.get("effects", {}).get("parameters", []):
                p_name = param.get("name", "")
                p_val = float(param.get("value", 0))
                if p_name == "PromotionalPriceTableItemsDiscount" and p_val > 0:
                    # En VTEX catalog API, este valor se descuenta sobre el precio base o lista según regla
                    candidato = precio_oferta - p_val if p_val < precio_oferta else None
                    if candidato and 0 < candidato < precio_oferta:
                        if precio_tarjeta is None or candidato < precio_tarjeta:
                            precio_tarjeta = candidato
                elif p_name == "PercentualDiscount" and 0 < p_val < 90:
                    candidato = precio_oferta * (1 - (p_val / 100.0))
                    if 0 < candidato < precio_oferta:
                        if precio_tarjeta is None or candidato < precio_tarjeta:
                            precio_tarjeta = candidato
    return precio_tarjeta

def extraer_exito():
    print("Iniciando extracción verificada de Éxito (Candidatos + Validación de Ficha Real)...")
    ofertas_validas = []
    candidatos = {}  # product_id -> {"slug": ..., "nombre": ..., "imagen": ...}

    busquedas = [
        ("celulares", "https://www.exito.com/s?q=celular&sort=discount_desc&page=1"),
        ("celulares", "https://www.exito.com/s?q=celular&sort=discount_desc&page=2"),
        ("televisores", "https://www.exito.com/s?q=televisor&sort=discount_desc&page=1"),
        ("televisores", "https://www.exito.com/s?q=televisor&sort=discount_desc&page=2"),
        ("computadores", "https://www.exito.com/s?q=portatil&sort=discount_desc&page=1"),
        ("computadores", "https://www.exito.com/s?q=portatil&sort=discount_desc&page=2"),
        ("electrodomesticos", "https://www.exito.com/s?q=nevera&sort=discount_desc&page=1"),
        ("electrodomesticos", "https://www.exito.com/s?q=lavadora&sort=discount_desc&page=1"),
        ("hogar", "https://www.exito.com/s?q=freidora&sort=discount_desc&page=1"),
        ("hogar", "https://www.exito.com/s?q=colchon&sort=discount_desc&page=1"),
    ]

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                locale="es-CO",
                timezone_id="America/Bogota"
            )
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page = context.new_page()

            def interceptar_busqueda(response):
                try:
                    if "/api/graphql" in response.url and "SearchQuery" in response.url and response.status == 200:
                        data = response.json()
                        edges = data.get("data", {}).get("search", {}).get("products", {}).get("edges", [])
                        for edge in edges:
                            node = edge.get("node", {})
                            nombre = node.get("name", "").strip()
                            slug = node.get("slug", "")
                            if not slug or not es_producto_limpio(nombre, slug):
                                continue

                            # Extraer ID numérico de producto del slug o del nodo
                            prod_id = str(node.get("id", "")).split("-")[0]
                            if not prod_id.isdigit():
                                match_id = re.search(r"-(\d+)$", slug)
                                prod_id = match_id.group(1) if match_id else ""

                            if not prod_id or prod_id in candidatos:
                                continue

                            # Pre-filtro rápido: vendido por Éxito y descuento aparente >= 40%
                            sellers = node.get("sellers", [])
                            vende_exito = any(
                                "exito" in str(s.get("sellerName", "")).lower() or str(s.get("sellerId", "")) == "1"
                                for s in sellers
                            )
                            if not vende_exito:
                                continue

                            offers = node.get("offers", {}).get("offers", [])
                            of_act = next((o for o in offers if o.get("quantity", 0) > 0), None)
                            if not of_act:
                                continue

                            l_price = float(of_act.get("listPrice", 0))
                            s_price = float(of_act.get("price", 0))
                            if l_price > 0 and s_price > 0 and (1 - s_price / l_price) >= 0.35:
                                imgs = node.get("image", [])
                                img_url = imgs[0].get("url", "https://via.placeholder.com/200") if imgs else "https://via.placeholder.com/200"
                                candidatos[prod_id] = {
                                    "slug": slug,
                                    "nombre": nombre,
                                    "imagen": img_url
                                }
                except Exception:
                    pass

            page.on("response", interceptar_busqueda)

            # FASE 1: Recolectar candidatos reales navegando búsquedas ordenadas por descuento
            for categoria, url_busqueda in busquedas:
                try:
                    page.goto(url_busqueda, wait_until="domcontentloaded", timeout=35000)
                    page.wait_for_timeout(3200)
                except Exception as nav_err:
                    print(f"Aviso en {categoria}: {nav_err}")

            print(f"Candidatos preseleccionados para verificación en ficha real: {len(candidatos)}")

            # FASE 2: Verificar precio exacto contra la API de ficha real de cada candidato
            for prod_id, info in candidatos.items():
                try:
                    api_ficha = f"https://www.exito.com/api/catalog_system/pub/products/search?fq=productId:{prod_id}"
                    res_ficha = page.evaluate(
                        """async (url) => {
                            const r = await fetch(url, { credentials: 'include' });
                            if (!r.ok) return { status: r.status, data: null };
                            return { status: r.status, data: await r.json() };
                        }""",
                        api_ficha
                    )

                    if res_ficha.get("status") != 200 or not res_ficha.get("data"):
                        continue

                    producto_real = res_ficha["data"][0]
                    items = producto_real.get("items", [])
                    if not items:
                        continue

                    # Buscar vendedor Éxito con stock real en la ficha
                    oferta_verificada = None
                    for item in items:
                        for seller in item.get("sellers", []):
                            s_name = str(seller.get("sellerName", "")).lower()
                            s_id = str(seller.get("sellerId", ""))
                            comm = seller.get("commertialOffer", {})
                            if ("exito" in s_name or s_id == "1") and comm.get("AvailableQuantity", 0) > 0:
                                oferta_verificada = comm
                                break
                        if oferta_verificada:
                            break

                    if not oferta_verificada:
                        continue

                    precio_normal = float(oferta_verificada.get("ListPrice", 0))
                    precio_otros = float(oferta_verificada.get("Price", 0))

                    if precio_normal <= 0 or precio_otros <= 0 or precio_otros >= precio_normal:
                        continue

                    precio_tarjeta = extraer_precio_tarjeta_exito(oferta_verificada, precio_otros)
                    mejor_precio = precio_tarjeta if precio_tarjeta is not None else precio_otros
                    descuento_real = round((1 - (mejor_precio / precio_normal)) * 100)

                    # Filtro comercial estricto: 50% a 85% real verificado en ficha
                    if 50 <= descuento_real <= 85:
                        ofertas_validas.append({
                            "Almacen": "Éxito",
                            "Nombre": info["nombre"],
                            "Imagen": info["imagen"],
                            "Precio Normal": formatear_pesos(precio_normal),
                            "Precio Tarjeta": formatear_pesos(precio_tarjeta) if precio_tarjeta else None,
                            "Precio Oferta": formatear_pesos(precio_otros),
                            "Descuento": f"{descuento_real}% OFF",
                            "Enlace Directo": f"https://www.exito.com/{info['slug']}/p"
                        })

                    page.wait_for_timeout(400)  # Pausa corta entre consultas de ficha

                except Exception as ficha_err:
                    print(f"Error verificando ficha {prod_id}: {ficha_err}")

            browser.close()

        ofertas_validas.sort(key=lambda x: int(x["Descuento"].replace("% OFF", "")), reverse=True)
        print(f"Total ofertas reales verificadas de Éxito (>= 50%): {len(ofertas_validas)}")
        return ofertas_validas

    except Exception as e:
        print(f"Error general en Playwright (Éxito): {e}")
        return []

if __name__ == "__main__":
    resultados = extraer_exito()
    print(json.dumps(resultados, indent=2, ensure_ascii=False))
