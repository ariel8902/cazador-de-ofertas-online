import re
import requests
from bs4 import BeautifulSoup
from config import SCRAPER_API_KEY, SCRAPER_API_URL, MIN_DESCUENTO, MAX_DESCUENTO

def extraer_alkosto():
    print(f"--- [ALKOSTO] Rastreando Ofertas Reales (>= {MIN_DESCUENTO}%) ---")
    urls = [
        "https://www.alkosto.com/celulares/c/BI_FE_101",
        "https://www.alkosto.com/tecnologia/c/BI_FE_104",
        "https://www.alkosto.com/electrodomesticos/c/BI_FE_105",
        "https://www.alkosto.com/televisores-audio-video/c/BI_FE_103",
        "https://www.alkosto.com/hogar/c/BI_FE_107"
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
                tarjetas = soup.select("li.product__item, div.product__item, li[class*='product']")

                for prod in tarjetas:
                    link_elem = prod.find("a", href=lambda h: h and "/p/" in h)
                    if not link_elem:
                        continue

                    enlace_raw = link_elem['href']
                    enlace = f"https://www.alkosto.com{enlace_raw}" if enlace_raw.startswith("/") else enlace_raw
                    if enlace in enlaces_vistos:
                        continue

                    nombre_elem = prod.find(["h2", "h3", "h4"], class_=lambda x: x and ("title" in str(x).lower() or "name" in str(x).lower()))
                    nombre = nombre_elem.get_text(strip=True) if nombre_elem else link_elem.get_text(strip=True)
                    if not nombre or len(nombre) < 6:
                        continue

                    img_elem = prod.find("img")
                    imagen = "https://via.placeholder.com/200?text=Alkosto"
                    if img_elem:
                        src = img_elem.get("data-src") or img_elem.get("src") or img_elem.get("srcset")
                        if src and "http" in str(src):
                            imagen = src.split()[0]
                        elif src and str(src).startswith("//"):
                            imagen = "https:" + src.split()[0]
                        elif src and str(src).startswith("/"):
                            imagen = "https://www.alkosto.com" + src.split()[0]

                    texto = prod.get_text(separator=" ", strip=True)
                    precios_raw = re.findall(r'\$\s*[\d\.\,]+', texto)
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
                            "Almacen": "Alkosto"
                        })
        except Exception as e:
            print(f"Error en Alkosto ({url}): {e}")

    print(f"Alkosto aportó: {len(ofertas)} ofertas reales de 50%+")
    return ofertas
