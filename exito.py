import json
import urllib.parse
from playwright.sync_api import sync_playwright

def formatear_pesos(valor):
    return f"${int(round(valor)):,}".replace(",", ".")

def extraer_exito():
    print("Iniciando navegador real (Chromium) para obtener sesión válida en Éxito...")
    ofertas_validas = []

    variables = {
        "first": 16,
        "after": "0",
        "sort": "discount_desc",
        "term": "",
        "selectedFacets": [
            {"key": "category-1", "value": "tecnologia"},
            {"key": "category-2", "value": "celulares"},
            {"key": "channel", "value": '{"salesChannel":"1","regionId":""}'},
            {"key": "locale", "value": "es-CO"}
        ]
    }

    query_params = urllib.parse.urlencode({
        "operationName": "SearchQuery",
        "variables": json.dumps(variables, separators=(",", ":"))
    })
    api_url = f"https://www.exito.com/api/graphql?{query_params}"

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

            page.goto("https://www.exito.com/tecnologia/celulares?order=discount_desc", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(6000)

            resultado = page.evaluate(
                """async (url) => {
                    const resp = await fetch(url, {
                        method: 'GET',
                        headers: { 'Accept': 'application/json' }
                    });
                    const text = await resp.text();
                    return { status: resp.status, body: text };
                }""",
                api_url
            )
            browser.close()

        status = resultado.get("status")
        print(f"Código de estado GraphQL interno: {status}")

        if status != 200:
            print(f"Respuesta no exitosa: {resultado.get('body', '')[:200]}")
            return []

        data = json.loads(resultado["body"])
        edges = data.get("data", {}).get("search", {}).get("products", {}).get("edges", [])
        print(f"Productos recibidos en el bloque: {len(edges)}")

        for edge in edges:
            node = edge.get("node", {})
            nombre = node.get("name", "Sin nombre")
            slug = node.get("slug", "")
            url_producto = f"https://www.exito.com/{slug}/p" if slug else "#"

            imagenes = node.get("image", [])
            imagen_url = imagenes[0].get("url", "https://via.placeholder.com/200") if imagenes else "https://via.placeholder.com/200"

            offers = node.get("offers", {}).get("offers", [])
            oferta_activa = next((o for o in offers if o.get("quantity", 0) > 0), None)

            if not oferta_activa:
                continue

            precio_lista = float(oferta_activa.get("listPrice", 0))
            precio_oferta = float(oferta_activa.get("price", 0))

            if precio_lista <= 0 or precio_oferta <= 0:
                continue

            precio_tarjeta = precio_oferta

            for seller in node.get("sellers", []):
                offer = seller.get("commertialOffer", {})
                if offer.get("AvailableQuantity", 0) > 0:
                    for teaser in offer.get("teasers", []):
                        t_name = teaser.get("name", "")
                        if "exito1" in t_name.lower() or "tabladeprecios" in t_name.lower():
                            for param in teaser.get("effects", {}).get("parameters", []):
                                if param.get("name") == "PromotionalPriceTableItemsDiscount":
                                    descuento_tabla = float(param.get("value", 0))
                                    precio_calculado = precio_lista - descuento_tabla
                                    if 0 < precio_calculado < precio_tarjeta:
                                        precio_tarjeta = precio_calculado

            mejor_precio = min(precio_oferta, precio_tarjeta)
            porcentaje_descuento = round((1 - (mejor_precio / precio_lista)) * 100)

            if porcentaje_descuento >= 50:
                ofertas_validas.append({
                    "Almacen": "Éxito",
                    "Nombre": nombre,
                    "Imagen": imagen_url,
                    "Precio Normal": formatear_pesos(precio_lista),
                    "Precio Tarjeta": formatear_pesos(precio_tarjeta),
                    "Precio Oferta": formatear_pesos(precio_oferta),
                    "Descuento": f"{porcentaje_descuento}% OFF",
                    "Enlace Directo": url_producto
                })

        print(f"Ofertas >= 50% filtradas: {len(ofertas_validas)}")
        return ofertas_validas

    except Exception as e:
        print(f"Error controlado en Playwright: {e}")
        return []

if __name__ == "__main__":
    resultados = extraer_exito()
    print(json.dumps(resultados, indent=2, ensure_ascii=False))
