import os
import time
import random
import re
import requests
from bs4 import BeautifulSoup

# API Key de ScraperAPI
SCRAPER_API_KEY = os.getenv('SCRAPER_API_KEY', '392e8624ae3a6701c44394bc61223b66')

def _solicitar_html_scraperapi(url_destino):
    """
    Realiza la petición HTTP a través de ScraperAPI con renderizado JS
    y proxy residencial de Colombia para evitar bloqueos de Alkosto.
    """
    endpoint = "http://api.scraperapi.com"
    payload = {
        'api_key': SCRAPER_API_KEY,
        'url': url_destino,
        'render': 'true',        # Renderiza el contenido dinámico
        'country_code': 'co',     # Proxy residencial en Colombia
        'keep_headers': 'true'
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(endpoint, params=payload, headers=headers, timeout=90)
        if response.status_code == 200:
            return response.text
        else:
            print(f"    ⚠️ [ALKOSTO] ScraperAPI devolvió estado {response.status_code} para URL: {url_destino}")
            return None
    except Exception as e:
        print(f"    ❌ [ALKOSTO] Error de conexión con ScraperAPI: {str(e)}")
        return None

def extraer_alkosto(page_param=None):
    print("\n--- [ALKOSTO] Iniciando extractor con ScraperAPI ---")
    ofertas = []
    url_target = "https://www.alkosto.com/ofertas/c/ofertas-alkosto"

    try:
        print(f"    [ALKOSTO] Rastreando vitrina de ofertas: {url_target}")
        html_content = _solicitar_html_scraperapi(url_target)

        if not html_content:
            return []

        soup = BeautifulSoup(html_content, "html.parser")

        # Selectores optimizados para la cuadrícula de productos en Alkosto
        tarjetas = soup.select("li.product-item, div.product__item, div.search-result-product, div[class*='product-card']")
        if not tarjetas:
            tarjetas = soup.select("article[class*='product'], div[class*='cluster'], div.product-item")

        print(f"    📊 [ALKOSTO] Tarjetas detectadas en HTML: {len(tarjetas)}")

        for prod in tarjetas:
            try:
                texto_tarjeta = prod.get_text(separator=" ", strip=True)
                if not texto_tarjeta or len(texto_tarjeta) < 20:
                    continue

                # Captura de porcentajes de descuento entre 40% y 100%
                match_pct = re.search(r'(?:-\s*)?([4-9][0-9]|100)\s*%', texto_tarjeta)
                if not match_pct:
                    continue

                descuento_num = int(match_pct.group(1))
                if descuento_num < 40:
                    continue

                descuento_txt = f"-{descuento_num}%"

                # Extracción de enlaces de producto
                link_elem = prod.find("a", href=lambda h: h and '/p/' in h) or prod.find("a", href=True)
                if not link_elem:
                    continue

                href = link_elem['href']
                if not href or '/p/' not in href:
                    continue

                enlace_producto = href if href.startswith("http") else f"https://www.alkosto.com{href}"

                # Extracción de URL de imagen
                img_elem = prod.find("img")
                img_url = ""
                if img_elem:
                    img_url = img_elem.get("src") or img_elem.get("data-src") or ""
                    if img_url.startswith("//"):
                        img_url = "https:" + img_url

                # Extracción del nombre
                nombre_elem = prod.find(["h3", "h2", "span"], class_=lambda x: x and ("name" in x.lower() or "title" in x.lower()))
                if nombre_elem:
                    nombre = nombre_elem.get_text(strip=True)
                else:
                    lineas = [l.strip() for l in texto_tarjeta.split() if len(l.strip()) > 3]
                    nombre = next((l for l in lineas if '$' not in l and '%' not in l), "Producto en Descuento Masivo")

                # Procesamiento numérico de precios
                precios_raw = re.findall(r'\$\s*[\d\.\,]+', texto_tarjeta)
                precios_num = []
                for pr in precios_raw:
                    num = re.sub(r'[^\d]', '', pr)
                    if num and int(num) > 50000:
                        precios_num.append(int(num))

                precios_num = sorted(list(set(precios_num)), reverse=True)
                if not precios_num:
                    continue

                precio_alto = precios_num[0]
                precio_oferta = precios_num[-1] if len(precios_num) >= 2 else precio_alto

                print(f"    🔥 [GANGÓN CAPTURADO {descuento_txt}] {nombre[:30]} | Precio: ${precio_oferta:,.0f}")

                ofertas.append({
                    "Nombre": nombre,
                    "Precio Normal": f"${precio_alto:,.0f}".replace(",", "."),
                    "Precio Oferta": f"${precio_oferta:,.0f}".replace(",", "."),
                    "Descuento": descuento_txt,
                    "Enlace Directo": enlace_producto,
                    "Imagen": img_url if img_url.startswith("http") else "https://via.placeholder.com/200?text=Alkosto",
                    "Almacen": "Alkosto",
                    "Categoria": "Ofertas Alkosto"
                })

            except Exception:
                continue

        time.sleep(random.uniform(1.0, 2.0))

    except Exception as e:
        print(f"❌ --- [Error crítico en Alkosto] {str(e)} ---")

    unicas = {o['Enlace Directo']: o for o in ofertas}.values()
    return list(unicas)
