import re
import requests
from bs4 import BeautifulSoup
from config import SCRAPER_API_KEY, SCRAPER_API_URL, MIN_DESCUENTO, MAX_DESCUENTO

def extraer_exito():
    print(f"--- [ÉXITO] Rastreando Ofertas Reales (>= {MIN_DESCUENTO}%) ---")
    urls = [
        "https://www.exito.com/hogar",
        "https://www.exito.com/electrodomesticos",
        "https://www.exito.com/tecnologia/televisores",
        "https://www.exito.com/tecnologia/celulares",
        "https://www.exito.com/moda-y-accesorios"
    ]

    ofertas = []
    enlaces_vistos = set()

    for url in urls:
        payload = {
            'api_key': SCRAPER_API_KEY,
            'url': url,
            'render': 'true',
            'country_code': 'co'
        }
        try:
            res = requests.get(SCRAPER_API_URL, params=payload, timeout=90)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                tarjetas = soup.find_all(["article", "li", "div"], attrs={"data-fs-product-card": True})
                if not tarjetas:
                    tarjetas = soup.find_all(["article", "div"], class_=lambda x: x and ("productcard" in str(x).lower() or "product-card" in str(x).lower() or "galleryitem" in str(x).lower()))

                for prod in tarjetas:
                    link_elem = prod.find("a", href=lambda h: h and ("/p" in h or "-p" in h))
                    if not link_elem:
                        continue

                    enlace_raw = link_elem['href']
                    enlace = f"https://www.exito.com{enlace_raw}" if enlace_raw.startswith("/") else enlace_raw
                    if enlace in enlaces_vistos:
                        continue

                    nombre_elem = prod.find(["h3", "h2", "span"], class_=lambda x: x and ("name" in str(x).lower() or "title" in str(x).lower()))
                    nombre = nombre_elem.get_text(strip=True) if nombre_elem else link_elem.get("title", "").strip()
                    if not nombre or len(nombre) < 6:
                        continue

                    img_elem = prod.find("img")
                    imagen = "https://via.placeholder.com/200?text=Exito"
                    if img_elem:
                        src_candidates = [img_elem.get("src"), img_elem.get("data-src"), img_elem.get("srcset")]
                        for cand in src_candidates:
                            if cand and "http" in str(cand):
                                imagen = cand.split()[0]
                                break
                            elif cand and str(cand).startswith("//"):
                                imagen = "https:" + cand.split()[0]
                                break

                    texto = prod.get_text(separator=" ", strip=True)
                    precios_raw = re.findall(r'\$\s*[\d\,\.]+', texto)
                    precios_num = sorted(list(set([
                        int(re.sub(r'[^\d]', '', pr)) for pr in precios_raw
                        if int(re.sub(r'[^\d]', '', pr) or 0) > 30000
                    ])), reverse=True)

                    if len(precios_num) < 2:
                        continue

                    precio_normal = precios_num[0]
                    precio_oferta = precios_num[-1]
                    precio_tarjeta = precios_num[-2] if len(precios_num) >= 3 else precio_oferta

                    if precio_oferta <= 0 or precio_normal <= precio_oferta:
                        continue

                    descuento = int(((precio_normal - precio_oferta) / precio_normal) * 100)

                    if MIN_DESCUENTO <= descuento <= MAX_DESCUENTO:
                        enlaces_vistos.add(enlace)
                        ofertas.append({
                            "Nombre": nombre,
                            "Precio Normal": f"${precio_normal:,.0f}".replace(",", "."),
                            "Precio Tarjeta": f"${precio_tarjeta:,.0f}".replace(",", "."),
                            "Precio Oferta": f"${precio_oferta:,.0f}".replace(",", "."),
                            "Descuento": f"-{descuento}%",
                            "Enlace Directo": enlace,
                            "Imagen": imagen,
                            "Almacen": "Éxito"
                        })
        except Exception as e:
            print(f"Error en Éxito ({url}): {e}")

    print(f"Éxito aportó: {len(ofertas)} ofertas reales de 50%+")
    return ofertas
