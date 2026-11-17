import time
import random
import requests
from config import SCRAPER_API_KEY, SCRAPER_API_URL, MIN_DESCUENTO, MAX_DESCUENTO


def _consultar_api_json_exito(url_api):
    """Consulta la API JSON interna de Éxito pasando por IP colombiana de ScraperAPI (sin render pesado)."""
    payload = {
        "api_key": SCRAPER_API_KEY,
        "url": url_api,
        "render": "false",
        "country_code": "co",
        "keep_headers": "true",
    }
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Referer": "https://www.exito.com/",
    }
    for intento in range(2):
        try:
            res = requests.get(SCRAPER_API_URL, params=payload, headers=headers, timeout=45)
            print(f"  -> API JSON | HTTP {res.status_code} | {url_api.split('?')[0]}")
            if res.status_code in (200, 206):
                return res.json()
            if res.status_code >= 500 and intento == 0:
                time.sleep(random.uniform(2.0, 3.5))
                continue
            break
        except Exception as e:
            print(f"  -> Error API JSON ({url_api}): {e}")
            if intento == 0:
                time.sleep(2)
    return []


def _extraer_precios_vtex(oferta_comercial):
    """Extrae Precio Normal, Precio Otros Medios y Precio Tarjeta Éxito desde el JSON oficial."""
    precio_normal = int(oferta_comercial.get("ListPrice") or 0)
    precio_otros = int(oferta_comercial.get("Price") or 0)
    precio_tarjeta = precio_otros

    # Revisar promociones/teasers exclusivos de Tarjeta Éxito si existen en el JSON
    teasers = oferta_comercial.get("PromotionTeasers") or oferta_comercial.get("Teasers") or []
    for teaser in teasers:
        nombre_promo = str(teaser.get("Name") or teaser.get("<Name>k__BackingField") or "").lower()
        if "tarjeta" in nombre_promo or "exito" in nombre_promo or "éxito" in nombre_promo:
            efectos = teaser.get("Effects") or teaser.get("<Effects>k__BackingField") or {}
            params = efectos.get("Parameters") or efectos.get("<Parameters>k__BackingField") or []
            for p in params:
                nombre_param = str(p.get("Name") or p.get("<Name>k__BackingField") or "")
                valor_param = str(p.get("Value") or p.get("<Value>k__BackingField") or "")
                if "PromotionalPrice" in nombre_param or "PercentualDiscount" in nombre_param:
                    try:
                        val_num = float(valor_param.replace(",", "."))
                        if "Percentual" in nombre_param and 0 < val_num < 95:
                            cand = int(precio_normal * (1 - val_num / 100.0))
                            if 10000 < cand < precio_tarjeta:
                                precio_tarjeta = cand
                        elif val_num > 10000 and int(val_num) < precio_tarjeta:
                            precio_tarjeta = int(val_num)
                    except ValueError:
                        pass

    return precio_normal, precio_tarjeta, precio_otros


def extraer_exito():
    print(f"--- [ÉXITO] Extracción JSON Directa Ordenada por Descuento (>= {MIN_DESCUENTO}%) ---")
    # Consultas por palabras clave y categorías principales ordenadas por mayor descuento en VTEX
    consultas = [
        "televisor",
        "celular",
        "portatil",
        "nevera",
        "lavadora",
        "freidora",
        "colchon",
        "sofa",
        "tenis",
        "reloj",
        "bicicleta",
        "audifonos",
    ]

    ofertas = []
    enlaces_vistos = set()

    for termino in consultas:
        # Cada bloque trae 50 productos estructurados en ~1.5 segundos
        url_api = (
            f"https://www.exito.com/api/catalog_system/pub/products/search/{termino}"
            f"?O=OrderByBestDiscountDESC&_from=0&_to=49"
        )
        time.sleep(random.uniform(1.0, 2.0))
        productos = _consultar_api_json_exito(url_api)
        if not isinstance(productos, list) or not productos:
            continue

        encontrados_termino = 0
        for prod in productos:
            nombre = (prod.get("productName") or "").strip()
            link_text = (prod.get("linkText") or "").strip()
            if not nombre or not link_text:
                continue

            enlace = f"https://www.exito.com/{link_text}/p"
            if enlace in enlaces_vistos:
                continue

            items = prod.get("items") or []
            if not items:
                continue

            # Tomar el primer SKU disponible con stock real y foto HD
            item_valido = None
            oferta_valida = None
            imagen_hd = ""

            for item in items:
                imagenes = item.get("images") or []
                url_img = imagenes[0].get("imageUrl", "") if imagenes else ""
                if not url_img or "placeholder" in url_img.lower():
                    continue

                for seller in item.get("sellers") or []:
                    comm = seller.get("commertialOffer") or {}
                    stock = int(comm.get("AvailableQuantity") or 0)
                    lp = int(comm.get("ListPrice") or 0)
                    sp = int(comm.get("Price") or 0)
                    if stock > 0 and lp > 30000 and sp > 10000 and lp > sp:
                        item_valido = item
                        oferta_valida = comm
                        imagen_hd = url_img
                        break
                if oferta_valida:
                    break

            if not oferta_valida or not imagen_hd:
                continue

            precio_normal, precio_tarjeta, precio_otros = _extraer_precios_vtex(oferta_valida)
            mejor_precio = min(precio_tarjeta, precio_otros)
            descuento = int(((precio_normal - mejor_precio) / precio_normal) * 100)

            if MIN_DESCUENTO <= descuento <= MAX_DESCUENTO:
                enlaces_vistos.add(enlace)
                encontrados_termino += 1
                ofertas.append({
                    "Nombre": nombre,
                    "Precio Normal": f"${precio_normal:,.0f}".replace(",", "."),
                    "Precio Tarjeta": f"${precio_tarjeta:,.0f}".replace(",", "."),
                    "Precio Oferta": f"${precio_otros:,.0f}".replace(",", "."),
                    "Descuento": f"-{descuento}%",
                    "Enlace Directo": enlace,
                    "Imagen": imagen_hd,
                    "Almacen": "Éxito",
                })

        print(f"     Término '{termino}': {len(productos)} analizados -> {encontrados_termino} ofertas >= {MIN_DESCUENTO}%")

    print(f"Éxito aportó: {len(ofertas)} ofertas reales de {MIN_DESCUENTO}%+")
    return ofertas
