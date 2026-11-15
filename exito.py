import re
import time
import random
import requests
from bs4 import BeautifulSoup
from config import SCRAPER_API_KEY, SCRAPER_API_URL, MIN_DESCUENTO, MAX_DESCUENTO


def _extraer_precios_tarjeta_exito(prod):
    """
    Lee los precios de la tarjeta de Éxito distinguiendo explícitamente:
    - Precio Normal (tachado / mayor)
    - Precio Tarjeta Éxito (el menor cuando hay precio exclusivo con tarjeta)
    - Precio Otros Medios (marcado con 'Otros' o precio público general)
    """
    texto_completo = prod.get_text(separator=" | ", strip=True)
    precios_raw = re.findall(r'\$\s*[\d\.]+', texto_completo)

    valores = []
    for pr in precios_raw:
        num = int(re.sub(r'[^\d]', '', pr) or 0)
        if num > 30000 and num not in valores:
            valores.append(num)

    valores.sort(reverse=True)
    if len(valores) < 2:
        return None, None, None

    precio_normal = valores[0]

    # Buscar si existe precio marcado explícitamente como "Otros"
    match_otros = re.search(r'\$\s*([\d\.]+)\s*\|?\s*Otros', texto_completo, re.IGNORECASE)
    precio_otros_explicit = int(re.sub(r'[^\d]', '', match_otros.group(1))) if match_otros else None

    if len(valores) >= 3:
        # Hay Precio Normal + Precio Otros Medios + Precio Tarjeta Éxito
        if precio_otros_explicit and precio_otros_explicit in valores[1:]:
            precio_otros = precio_otros_explicit
            candidatos_tarjeta = [v for v in valores[1:] if v != precio_otros]
            precio_tarjeta = min(candidatos_tarjeta) if candidatos_tarjeta else precio_otros
        else:
            # En Éxito, cuando hay 3 precios, el intermedio es Otros y el menor es Tarjeta Éxito
            precio_otros = valores[1]
            precio_tarjeta = valores[2]
    else:
        # Solo hay 2 precios (Normal y Oferta general para todos los medios)
        precio_otros = valores[1]
        precio_tarjeta = valores[1]

    return precio_normal, precio_tarjeta, precio_otros


def extraer_exito():
    print(f"--- [ÉXITO] Rastreando Ofertas Reales Ordenadas por Descuento (>= {MIN_DESCUENTO}%) ---")
    urls = [
        "https://www.exito.com/hogar?sort=discount_desc",
        "https://www.exito.com/electrodomesticos?sort=discount_desc",
        "https://www.exito.com/tecnologia/televisores?sort=discount_desc",
        "https://www.exito.com/tecnologia/celulares?sort=discount_desc",
        "https://www.exito.com/moda-y-accesorios?sort=discount_desc",
        "https://www.exito.com/deportes-y-tiempo-libre?sort=discount_desc",
    ]

    ofertas = []
    enlaces_vistos = set()

    for url in urls:
        time.sleep(random.uniform(1.5, 3.0))
        payload = {
            "api_key": SCRAPER_API_KEY,
            "url": url,
            "render": "true",
            "country_code": "co",
        }
        try:
            res = requests.get(SCRAPER_API_URL, params=payload, timeout=90)
            print(f"  -> {url} | HTTP {res.status_code}")
            if res.status_code != 200:
                continue

            soup = BeautifulSoup(res.text, "html.parser")
            tarjetas = soup.find_all(["article", "li", "div"], attrs={"data-fs-product-card": True})
            if not tarjetas:
                tarjetas = soup.find_all(
                    ["article", "div"],
                    class_=lambda x: x and any(
                        k in str(x).lower() for k in ("productcard", "product-card", "galleryitem")
                    ),
                )

            print(f"     Tarjetas detectadas: {len(tarjetas)}")

            for prod in tarjetas:
                link_elem = prod.find("a", href=lambda h: h and ("/p" in h or "-p" in h))
                if not link_elem:
                    continue

                enlace_raw = link_elem["href"]
                enlace = f"https://www.exito.com{enlace_raw}" if enlace_raw.startswith("/") else enlace_raw
                enlace = enlace.split("?")[0]
                if enlace in enlaces_vistos:
                    continue

                nombre_elem = prod.find(
                    ["h3", "h2", "span"],
                    class_=lambda x: x and ("name" in str(x).lower() or "title" in str(x).lower()),
                )
                nombre = nombre_elem.get_text(strip=True) if nombre_elem else link_elem.get("title", "").strip()
                if not nombre or len(nombre) < 6:
                    continue

                # Validar imagen real (descartar placeholders)
                img_elem = prod.find("img")
                imagen = ""
                if img_elem:
                    for attr in ("src", "data-src", "srcset"):
                        cand = img_elem.get(attr)
                        if cand and "http" in str(cand) and "placeholder" not in str(cand).lower():
                            imagen = str(cand).split()[0]
                            break
                        elif cand and str(cand).startswith("//"):
                            imagen = "https:" + str(cand).split()[0]
                            break

                if not imagen:
                    continue

                precio_normal, precio_tarjeta, precio_otros = _extraer_precios_tarjeta_exito(prod)
                if not precio_normal or not precio_otros or precio_normal <= precio_otros:
                    continue

                mejor_precio = min(precio_tarjeta, precio_otros)
                descuento = int(((precio_normal - mejor_precio) / precio_normal) * 100)

                if MIN_DESCUENTO <= descuento <= MAX_DESCUENTO:
                    enlaces_vistos.add(enlace)
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
        except Exception as e:
            print(f"Error en Éxito ({url}): {e}")

    print(f"Éxito aportó: {len(ofertas)} ofertas reales de {MIN_DESCUENTO}%+")
    return ofertas
