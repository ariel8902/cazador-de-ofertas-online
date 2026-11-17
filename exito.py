import json
import urllib.parse
from playwright.sync_api import sync_playwright

def formatear_pesos(valor):
    return f"${int(round(valor)):,}".replace(",", ".")

def es_producto_valido_comercialmente(nombre, slug, sellers):
    texto_check = f"{nombre} {slug}".lower()
    palabras_prohibidas = ["reacondicionado", "refurbished", "usado", "exhibicion", "open box", "seminuevo"]
    if any(palabra in texto_check for palabra in palabras_prohibidas):
        return False

    if "-mp-" in slug.lower():
        return False

    vende_exito = any(
        "exito" in str(s.get("sellerName", "")).lower() or str(s.get("sellerId", "")) == "1"
        for s in sellers
    )
    return vende_exito

def extraer_exito():
    print("Iniciando extracción profesional de Éxito (GraphQL SearchQuery + Auditoría Estricta)...")
    ofertas_validas = []
    urls_vistas = set()

    categorias_objetivo = [
        [{"key": "category-1", "value": "tecnologia"}, {"key": "category-2", "value": "celulares"}],
        [{"key": "category-1", "value": "tecnologia"}, {"key": "category-2", "value": "televisores"}],
        [{"key": "category-1", "value": "tecnologia"}, {"key": "category-2", "value": "computadores"}],
        [{"key": "category-1", "value": "electrodomesticos"}],
        [{"key": "category-1", "value": "hogar"}]
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

            # Establecer sesión legítima inicial para superar Akamai
            print("Estableciendo sesión legítima con Akamai...")
            page.goto("https://www.exito.com/tecnologia?order=discount_desc", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(5000)

            for cat_facets in categorias_objetivo:
                facets = cat_facets + [
                    {"key": "channel", "value": '{"salesChannel":"1","regionId":""}'},
                    {"key": "locale", "value": "es-CO"}
                ]
                variables = {
                    "first": 24,
                    "after": "0",
                    "sort": "discount_desc",
                    "term": "",
                    "selectedFacets": facets
                }
                query_params = urllib.parse.urlencode({
                    "operationName": "SearchQuery",
                    "variables": json.dumps(variables, separators=(",", ":"))
                })
                api_url = f"https://www.exito.com/api/graphql?{query_params}"

                print(f"Consultando GraphQL SearchQuery para facetas: {cat_facets}")
                resultado = page.evaluate(
                    """async (url) => {
                        const resp = await fetch(url, {
                            method: 'GET',
                            headers: { 'Accept': 'application/json' },
                            credentials: 'include'
                        });
                        const text = await resp.text();
                        return { status: resp.status, body: text };
                    }""",
                    api_url
                )

                if resultado.get("status") != 200:
                    print(f"Alerta HTTP {resultado.get('status')} en categoría {cat_facets}")
                    continue

                try:
                    data = json.loads(resultado["body"])
                    edges = data.get("data", {}).get("search", {}).get("products", {}).get("edges", [])
                except Exception as parse_err:
                    print(f"Error parseando JSON de GraphQL: {parse_err}")
                    continue

                for edge in edges:
                    node = edge.get("node", {})
                    nombre = node.get("name", "Sin nombre").strip()
                    slug = node.get("slug", "")
                    if not slug:
                        continue

                    url_producto = f"https://www.exito.com/{slug}/p"
                    if url_producto in urls_vistas:
                        continue

                    sellers = node.get("sellers", [])
                    if not es_producto_valido_comercialmente(nombre, slug, sellers):
                        continue

                    offers = node.get("offers", {}).get("offers", [])
                    oferta_activa = next((o for o in offers if o.get("quantity", 0) > 0), None)
                    if not oferta_activa:
                        continue

                    precio_lista = float(oferta_activa.get("listPrice", 0))
                    precio_oferta = float(oferta_activa.get("price", 0))
                    if precio_lista <= 0 or precio_oferta <= 0 or precio_oferta >= precio_lista:
                        continue

                    # Extracción y aislamiento estricto de Tarjeta Éxito (excluyendo Addi/terceros)
                    precio_tarjeta_real = None
                    for seller in sellers:
                        if "exito" not in str(seller.get("sellerName", "")).lower() and str(seller.get("sellerId", "")) != "1":
                            continue
                        offer = seller.get("commertialOffer", {})
                        if offer.get("AvailableQuantity", 0) > 0:
                            for teaser in offer.get("teasers", []):
                                t_name = teaser.get("name", "").lower()
                                if ("tarjeta" in t_name and "exito" in t_name) or "exito1" in t_name:
                                    if "addi" in t_name or "puntos" in t_name:
                                        continue
                                    for param in teaser.get("effects", {}).get("parameters", []):
                                        if param.get("name") == "PromotionalPriceTableItemsDiscount":
                                            descuento_tabla = float(param.get("value", 0))
                                            precio_calc = precio_lista - descuento_tabla
                                            if 0 < precio_calc < precio_oferta:
                                                if precio_tarjeta_real is None or precio_calc < precio_tarjeta_real:
                                                    precio_tarjeta_real = precio_calc

                    mejor_precio = precio_tarjeta_real if precio_tarjeta_real is not None else precio_oferta
                    porcentaje_descuento = round((1 - (mejor_precio / precio_lista)) * 100)

                    # Auditoría comercial estricta: rango real verificado 50% - 85%
                    if 50 <= porcentaje_descuento <= 85:
                        imagenes = node.get("image", [])
                        imagen_url = imagenes[0].get("url", "https://via.placeholder.com/200") if imagenes else "https://via.placeholder.com/200"

                        urls_vistas.add(url_producto)
                        ofertas_validas.append({
                            "Almacen": "Éxito",
                            "Nombre": nombre,
                            "Imagen": imagen_url,
                            "Precio Normal": formatear_pesos(precio_lista),
                            "Precio Tarjeta": formatear_pesos(precio_tarjeta_real) if precio_tarjeta_real else None,
                            "Precio Oferta": formatear_pesos(precio_oferta),
                            "Descuento": f"{porcentaje_descuento}% OFF",
                            "Enlace Directo": url_producto
                        })

            browser.close()

        ofertas_validas.sort(key=lambda x: int(x["Descuento"].replace("% OFF", "")), reverse=True)
        print(f"Total ofertas reales verificadas de Éxito (>= 50%): {len(ofertas_validas)}")
        return ofertas_validas

    except Exception as e:
        print(f"Error general controlado en extracción profesional (Éxito): {e}")
        return []

if __name__ == "__main__":
    resultados = extraer_exito()
    print(json.dumps(resultados, indent=2, ensure_ascii=False))
