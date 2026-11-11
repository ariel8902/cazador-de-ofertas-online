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
    y proxy residencial de Colombia para evitar bloqueos de Ktronix.
    """
    endpoint = "http://api.scraperapi.com"
    payload = {
        'api_key': SCRAPER_API_KEY,
        'url': url_destino,
        'render': 'true',        # Renderiza el contenido dinámico de Ktronix
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
            print(f"    ⚠️ [KTRONIX] ScraperAPI devolvió estado {response.status_code} para URL: {url_destino}")
            return None
    except Exception as e:
        print(f"    ❌ [KTRONIX] Error de conexión con ScraperAPI: {str(e)}")
        return None

def extraer_ktronix():
    """
    Extrae ofertas reales de Ktronix capturando la grilla de productos
    a través de ScraperAPI sin requerir un navegador Playwright local.
    """
    print("\n--- [KTRONIX] Iniciando extractor con ScraperAPI ---")
    ofertas = []
    categorias_urls = [
        ("Tecnología", "https://www.ktronix.com/tecnologia/c/BI_FE_104"),
        ("Electrodomésticos", "https://www.ktronix.com/electrodomesticos/c/BI_FE_105"),
        ("Celulares", "https://www.ktronix.com/celulares/c/BI_FE_101")
    ]

    for cat_nombre, url in categorias_urls:
        try:
            print(f"    [KTRONIX] Rastreando categoría: {cat_nombre} -> {url}")
            html_content = _solicitar_html_scraperapi(url)
            
            if not html_content:
                continue

            soup = BeautifulSoup(html_content, "html.parser")

            productos = (
                soup.find_all("form", class_=lambda x: x and "product-item" in x.lower()) or
                soup.find_all("li", class_=lambda x: x and ("product" in x.lower() or "item" in x.lower())) or
                soup.find_all("div", class_=lambda x: x and "product-item" in x.lower())
            )

            print(f"    📊 [{cat_nombre}] Tarjetas detectadas en pantalla: {len(productos)}")

            for prod in productos:
                try:
                    nombre_elem = prod.find(["h2", "h3", "a", "span"], class_=lambda x: x and ("name" in x.lower() or "title" in x.lower()))
                    nombre = nombre_elem.get_text(strip=True) if nombre_elem else None

                    if not nombre or len(nombre) < 6 or any(bad in nombre.lower() for bad in ["mi cuenta", "mi perfil", "direcciones", "paga a cuotas", "0% interés"]):
                        continue

                    link_elem = prod.find("a", href=True)
                    if not link_elem:
                        continue
                    href = link_elem['href']
                    enlace = f"https://www.ktronix.com{href}" if href.startswith("/") else href

                    precios = prod.find_all(["span", "div", "p"], class_=lambda x: x and "price" in x.lower())
                    textos_precio = [p.get_text(strip=True) for p in precios if "$" in p.get_text()]

                    precio_normal = "Consultar tienda"
                    precio_oferta = "Ver Oferta"
                    if len(textos_precio) >= 2:
                        precio_normal = textos_precio[0]
                        precio_oferta = textos_precio[1]
                    elif len(textos_precio) == 1:
                        precio_oferta = textos_precio[0]

                    imagen_url = None
                    imgs = prod.find_all("img")
                    for img in imgs:
                        src = img.get("src") or img.get("data-src") or img.get("srcset")
                        if src and not any(bad in src.lower() for bad in ["banner", "logo", "svg", "icon", "header"]):
                            imagen_url = src.split(",")[0].split()[0]
                            break

                    if imagen_url and imagen_url.startswith("//"):
                        imagen_url = "https:" + imagen_url

                    descuento = "Oferta"
                    texto_completo = prod.get_text()
                    match_pct = re.search(r'(-\d+%|\d+%\s*OFF|\d+%)', texto_completo, re.IGNORECASE)
                    if match_pct:
                        descuento = match_pct.group(1)

                    ofertas.append({
                        "Nombre": nombre,
                        "Precio Normal": precio_normal,
                        "Precio Oferta": precio_oferta,
                        "Descuento": descuento,
                        "Enlace Directo": enlace,
                        "Imagen": imagen_url or "https://via.placeholder.com/200?text=Ktronix+Oferta",
                        "Almacen": "Ktronix",
                        "Categoria": cat_nombre
                    })

                except Exception:
                    continue

            time.sleep(random.uniform(1.0, 2.0))

        except Exception as e:
            print(f"❌ Error extrayendo {cat_nombre} en Ktronix: {str(e)}")

    unicas = {o['Enlace Directo']: o for o in ofertas}.values()
    return list(unicas)
