import json
import re
from playwright.sync_api import sync_playwright

def formatear_pesos(valor):
    return f"${int(round(valor)):,}".replace(",", ".")

def es_producto_valido_comercialmente(nombre, slug, sellers):
    texto_check = f"{nombre} {slug}".lower()
    palabras_prohibidas = ["reacondicionado", "refurbished", "usado", "exhibicion", "open box", "seminuevo", "reales"]
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
    print("Iniciando extracción auditada de Éxito (Catálogo API + Auditoría de Precios)...")
    ofertas_validas = []
    urls_vistas = set()
    productos_crudos = []

    # URLs de la API de catálogo oficial de VTEX para Éxito ordenadas por mayor descuento
    endpoints_catalogo = [
        ("televisores", "https://www.exito.com/api/catalog_system/pub/products/search?fq=C:/1000003/&O=OrderByDiscountDESC&_from=0&_to=49"),
        ("celulares", "https://www.exito.com/api/catalog_system/pub/products/search?fq=C:/1000010/&O=OrderByDiscountDESC&_from=0&_to=49"),
        ("computadores", "https://www.exito.com/api/catalog_system/pub/products/search?fq=C:/1000004/&O=OrderByDiscountDESC&_from=0&_to=49"),
        ("electrodomesticos", "https://www.exito.com/api/catalog_system/pub/products/search?fq=C:/1000001/&O=OrderByDiscountDESC&_from=0&_to=49"),
        ("hogar", "https://www.exito.com/api/catalog_system/pub/products/search?fq=C:/1000002/&O=OrderByDiscountDESC&_from=0&_to=49")
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

            # Establecer sesión legítima en la home para pasar WAF de Akamai
            print("Estableciendo sesión legítima con Akamai...")
            page.goto("https://www.exito.com/", wait_until="domcontentloaded", timeout=40000)
            page.wait_for_timeout(3000)

            for cat_nombre, api_url in endpoints_catalogo:
                print(f"Consultando catálogo oficial de {cat_nombre}...")
                try:
                    resultado = page.evaluate(
                        """async (url) => {
                            const resp = await fetch(url, { credentials: 'include' });
                            if (!resp.ok) return { status: resp.status, data: [] };
                            return { status: resp.status, data: await resp.json() };
                        }""",
                        api_url
                    )

                    if resultado.get("status") == 200 and isinstance(resultado.get("data"), list):
                        items_api = resultado["data"]
                        print(f"-> {len(items_api)} productos obtenidos en {cat_nombre}")
                        productos_crudos.extend(items_api)
                    else:
                        print(f"-> Aviso: API respondió estado {resultado.get('status')} en {cat_nombre}")
                except Exception as api_err:
                    print(f"Error consultando {cat_nombre}: {api_err}")

            browser.close()

        print(f"Total bruto recolectado para auditoría: {len(productos_crudos)}")

        for prod in productos_crudos:
            nombre = prod.get("productName", "").strip()
            slug = prod.get("linkText", "")
            if not slug:
                continue

            url_producto = f"https://www.exito.com/{slug}/p"
            if url_producto in urls_vistas:
                continue

            items = prod.get("items", [])
            if not items:
                continue

            # Validar vendedor oficial de Éxito y stock disponible
            vende_exito = False
            oferta_valida = None
            for item in items:
                for seller in item.get("sellers", []):
                    s_name = str(seller.get("sellerName", "")).lower()
                    s_id = str(seller.get("sellerId", ""))
                    comm = seller.get("commertialOffer", {})
                    if ("exito" in s_name or s_id == "1") and comm.get("AvailableQuantity", 0) > 0:
                        vende_exito = True
                        oferta_valida = comm
                        break
                if vende_exito:
                    break

            if not vende_exito or not oferta_valida:
                continue

            if not es_producto_valido_comercialmente(nombre, slug, items[0].get("sellers", [])):
                continue

            precio_lista = float(oferta_valida.get("ListPrice", 0))
            precio_oferta = float(oferta_valida.get("Price", 0))

            # Validación matemática estricta antimentiras
            if precio_lista <= 0 or precio_oferta <= 0 or precio_oferta >= precio_lista:
                continue

            # Extracción limpia exclusiva de Tarjeta Éxito (ignorando Addi / terceros)
            precio_tarjeta_real = None
            for teaser in oferta_valida.get("teasers", []):
                t_name = str(teaser.get("name", "")).lower()
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

            # Filtro comercial estricto de la vitrina (50% a 85% reales verificados)
            if 50 <= porcentaje_descuento <= 85:
                imagenes = items[0].get("images", [])
                imagen_url = imagenes[0].get("imageUrl", "https://via.placeholder.com/200") if imagenes else "https://via.placeholder.com/200"

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
        print(f"Total ofertas reales verificadas de Éxito (>= 50%): {len(ofertas_validas)}")
        return ofertas_validas

    except Exception as e:
        print(f"Error general en extracción auditada de Éxito: {e}")
        return []

if __name__ == "__main__":
    resultados = extraer_exito()
    print(json.dumps(resultados, indent=2, ensure_ascii=False))
