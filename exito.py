import re
import requests
from config import SCRAPER_API_KEY, SCRAPER_API_URL, MIN_DESCUENTO, MAX_DESCUENTO


def _extraer_precio_tarjeta_vtex(offer, precio_otros):
    """
    Detecta en los metadatos de promociones/teasers de VTEX si existe un precio
    exclusivo más bajo para Tarjeta Éxito / aliados. Si no existe, retorna precio_otros.
    """
    candidatos = []
    for campo in ("PromotionTeasers", "Teasers"):
        teasers = offer.get(campo) or []
        for t in teasers:
            texto_teaser = str(t).lower()
            if any(k in texto_teaser for k in ("tarjeta", "exito", "éxito", "tuya", "aliad")):
                nums = re.findall(r'\d{5,9}', str(t))
                for n in nums:
                    val = int(n)
                    if 30000 < val < precio_otros:
                        candidatos.append(val)
    return min(candidatos) if candidatos else precio_otros


def extraer_exito():
    print(f"--- [ÉXITO] Rastreando Catálogo Oficial VTEX (>= {MIN_DESCUENTO}%) ---")
    # Departamentos principales de Éxito ordenados por Mayor Descuento Real
    categorias_vtex = [
        "fq=C:/1/",   # Tecnología
        "fq=C:/2/",   # Electrodomésticos
        "fq=C:/3/",   # Hogar y Muebles
        "fq=C:/4/",   # Mercado / Despensa
        "fq=C:/6/",   # Deportes y Tiempo Libre
        "fq=C:/11/",  # Moda y Accesorios
    ]

    ofertas = []
    enlaces_vistos = set()

    for filtro_cat in categorias_vtex:
        # Barremos 2 páginas de 50 productos (100 mejores descuentos por departamento)
        for inicio in (0, 50):
            fin = inicio + 49
            api_url = (
                f"https://www.exito.com/api/catalog_system/pub/products/search"
                f"?{filtro_cat}&O=OrderByBestDiscountDESC&_from={inicio}&_to={fin}"
            )
            payload = {
                "api_key": SCRAPER_API_KEY,
                "url": api_url,
                "country_code": "co",
            }
            try:
                res = requests.get(SCRAPER_API_URL, params=payload, timeout=60)
                if res.status_code not in (200, 206):
                    continue

                productos = res.json()
                if not isinstance(productos, list) or not productos:
                    break

                encontrados_en_lote = 0

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

                    # Validar imagen real en HD
                    imagenes = items[0].get("images") or []
                    imagen = imagenes[0].get("imageUrl", "") if imagenes else ""
                    if not imagen or "placeholder" in imagen.lower():
                        continue

                    # Obtener precios reales del vendedor principal con stock disponible
                    sellers = items[0].get("sellers") or []
                    offer = None
                    for s in sellers:
                        co = s.get("commertialOffer") or {}
                        if co.get("AvailableQuantity", 0) > 0 and co.get("Price", 0) > 0:
                            offer = co
                            break

                    if not offer:
                        continue

                    precio_normal = int(round(float(offer.get("ListPrice") or 0)))
                    precio_otros = int(round(float(offer.get("Price") or 0)))

                    if precio_otros <= 30000 or precio_normal <= precio_otros:
                        continue

                    precio_tarjeta = _extraer_precio_tarjeta_vtex(offer, precio_otros)
                    mejor_precio = min(precio_tarjeta, precio_otros)

                    descuento = int(((precio_normal - mejor_precio) / precio_normal) * 100)

                    if MIN_DESCUENTO <= descuento <= MAX_DESCUENTO:
                        enlaces_vistos.add(enlace)
                        encontrados_en_lote += 1
                        ofertas.append({
                            "Nombre": nombre,
                            "Precio Normal": f"${precio_normal:,.0f}".replace(",", "."),
                            "Precio Tarjeta": f"${precio_tarjeta:,.0f}".replace(",", "."),
                            "Precio Oferta": f"${precio_otros:,.0f}".replace(",", "."),
                            "Descuento": f"-{descuento}%",
                            "Enlace Directo": enlace,
                            "Imagen": imagen,
                            "Almacen": "Éxito",
                        })

                # Como viene ordenado de mayor a menor descuento, si en este lote
                # ya no hay ofertas >= MIN_DESCUENTO, pasamos al siguiente departamento
                if encontrados_en_lote == 0 and inicio > 0:
                    break

            except Exception as e:
                print(f"Error en Éxito VTEX ({filtro_cat} {inicio}-{fin}): {e}")

    print(f"Éxito aportó: {len(ofertas)} ofertas reales de {MIN_DESCUENTO}%+")
    return ofertas
