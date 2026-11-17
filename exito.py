import json
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
    print("Iniciando navegador real (Chromium) con interceptación nativa en Éxito...")
    ofertas_validas = []
    urls_vistas = set()
    bloques_capturados = []

    rutas_categorias = [
        "https://www.exito.com/tecnologia/celulares?order=discount_desc",
        "https://www.exito.com/tecnologia/televisores?order=discount_desc",
        "https://www.exito.com/tecnologia/computadores?order=discount_desc",
        "https://www.exito.com/electrodomesticos?order=discount_desc",
        "https://www.exito.com/hogar?order=discount_desc"
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

            def interceptar_respuesta(response):
                try:
                    if "/api/graphql" in response.url and "SearchQuery" in response.url and response.status == 200:
                        data = response.json()
                        edges = data.get("data", {}).get("search", {}).get("products", {}).get("edges", [])
                        if edges:
                            bloques_capturados.extend(edges)
                except Exception:
                    pass

            page.on("response", interceptar_respuesta)

            for url_cat in rutas_categorias:
                print(f"Explorando categoría: {url_cat}")
                try:
                    page.goto(url_cat, wait_until="domcontentloaded", timeout=40000)
                    page.wait_for_timeout(4500)
                    # Scroll suave para disparar carga completa de vitrina
                    page.evaluate("window.scrollBy(0, 900)")
                    page.wait_for_timeout(1500)
                except Exception as nav_err:
                    print(f"Aviso navegando {url_cat}: {nav_err}")

            browser.close()

        print(f"Total nodos de productos interceptados nativamente: {len(bloques_capturados)}")

        for edge in bloques_capturados:
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

            precio_tarjeta_real = None
            for seller in sellers:
                if "exito" not in str(seller.get("sellerName", "")).lower() and str(seller.get("sellerId", "")) != "1":
                    continue
                offer = seller.get("commertialOffer", {})
                if offer.get("AvailableQuantity", 0) > 0:
                    for teaser in offer.get("teasers", []):
                        t_name = teaser.get("name", "").lower()
                        if "exito1" in t_name or "tabladeprecios" in t_name or "tarjeta" in t_name:
                            for param in teaser.get("effects", {}).get("parameters", []):
                                if param.get("name") == "PromotionalPriceTableItemsDiscount":
                                    descuento_tabla = float(param.get("value", 0))
                                    precio_calc = precio_lista - descuento_tabla
                                    if 0 < precio_calc < precio_oferta:
                                        if precio_tarjeta_real is None or precio_calc < precio_tarjeta_real:
                                            precio_tarjeta_real = precio_calc

            mejor_precio = precio_tarjeta_real if precio_tarjeta_real is not None else precio_oferta
            porcentaje_descuento = round((1 - (mejor_precio / precio_lista)) * 100)

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

        ofertas_validas.sort(key=lambda x: int(x["Descuento"].replace("% OFF", "")), reverse=True)
        print(f"Total ofertas comerciales válidas de Éxito (>= 50%): {len(ofertas_validas)}")
        return ofertas_validas

    except Exception as e:
        print(f"Error controlado en Playwright (Éxito): {e}")
        return []

if __name__ == "__main__":
    resultados = extraer_exito()
    print(json.dumps(resultados, indent=2, ensure_ascii=False))
