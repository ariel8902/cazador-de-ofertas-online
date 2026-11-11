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
    Realiza la petición HTTP a través de ScraperAPI con bypass antibloqueo
    y renderizado de JavaScript para sitios VTEX (Éxito).
    """
    endpoint = "http://api.scraperapi.com"
    payload = {
        'api_key': SCRAPER_API_KEY,
        'url': url_destino,
        'render': 'true',        # Renderiza el JavaScript (VTEX reactivo)
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
            print(f"    ⚠️ [ÉXITO] ScraperAPI devolvió estado {response.status_code} para URL: {url_destino}")
            return None
    except Exception as e:
        print(f"    ❌ [ÉXITO] Error de conexión con ScraperAPI: {str(e)}")
        return None

def extraer_exito(pagina=1, categoria="Ofertas", url_busqueda="https://www.exito.com/ofertas"):
    print("\n--- [ÉXITO] Iniciando extractor con ScraperAPI ---")
    ofertas = []

    # Determinar las URLs a rastrear
    if url_busqueda and isinstance(url_busqueda, str) and url_busqueda.startswith("http") and url_busqueda != "https://www.exito.com/ofertas":
        categorias_urls = [(categoria if isinstance(categoria, str) else "Ofertas", url_busqueda)]
    else:
        categorias_urls = [
            ("Tecnología", "https://www.exito.com/tecnologia"),
            ("Electrodomésticos", "https://www.exito.com/electrodomesticos"),
            ("Celulares", "https://www.exito.com/celulares")
        ]

    for cat_nombre, url in categorias_urls:
        try:
            print(f"    [ÉXITO] Rastreando categoría: {cat_nombre} -> {url}")
            html_content = _solicitar_html_scraperapi(url)
            
            if not html_content:
                continue

            soup = BeautifulSoup(html_content, "html.parser")

            # Captura de tarjetas de productos
            productos = soup.find_all("article") or soup.find_all("div", class_=lambda x: x and ("product" in x.lower() or "item" in x.lower()))
            print(f"    📊 [{cat_nombre}] Tarjetas detectadas en pantalla: {len(productos)}")

            for prod in productos:
                try:
                    # Nombre del producto
                    nombre_elem = prod.find(["h3", "h2", "span"], class_=lambda x: x and ("name" in x.lower() or "title" in x.lower() or "brand" in x.lower()))
                    nombre = nombre_elem.get_text(strip=True) if nombre_elem else None

                    # Enlace directo
                    link_elem = prod.find("a", href=True)
                    if not link_elem:
                        continue
                    enlace_raw = link_elem['href']
                    enlace = f"https://www.exito.com{enlace_raw}" if enlace_raw.startswith("/") else enlace_raw

                    # Imagen
                    img_elem = prod.find("img")
                    imagen_url = None
                    if img_elem:
                        imagen_url = img_elem.get("src") or img_elem.get("data-src") or img_elem.get("srcset")
                        if imagen_url and imagen_url.startswith("//"):
                            imagen_url = "https:" + imagen_url

                    # Parseo numérico de precios por Regex
                    texto_tarjeta = prod.get_text(separator=" ", strip=True)
                    precios_raw = re.findall(r'\$\s*[\d\.\,]+', texto_tarjeta)
                    precios_num = []
                    for pr in precios_raw:
                        num = int(re.sub(r'[^\d]', '', pr))
                        if num > 10000:
                            precios_num.append(num)

                    precios_num = sorted(list(set(precios_num)), reverse=True)
                    if not precios_num:
                        continue

                    precio_alto = precios_num[0]
                    precio_oferta = precios_num[-1] if len(precios_num) >= 2 else precio_alto

                    # Descuento
                    desc_elem = prod.find(["span", "div"], class_=lambda x: x and "discount" in x.lower())
                    if desc_elem:
                        descuento = desc_elem.get_text(strip=True)
                    else:
                        match_pct = re.search(r'([1-9][0-9])\s*%', texto_tarjeta)
                        descuento = f"-{match_pct.group(1)}%" if match_pct else "Oferta"

                    if nombre and enlace:
                        ofertas.append({
                            "Nombre": nombre,
                            "Precio Normal": f"${precio_alto:,.0f}".replace(",", "."),
                            "Precio Oferta": f"${precio_oferta:,.0f}".replace(",", "."),
                            "Descuento": descuento,
                            "Enlace Directo": enlace,
                            "Imagen": imagen_url or "https://via.placeholder.com/200?text=Exito+Oferta",
                            "Almacen": "Éxito",
                            "Categoria": cat_nombre
                        })
                except Exception:
                    continue

            time.sleep(random.uniform(1.0, 2.0))
        except Exception as e:
            print(f"❌ Error extrayendo {cat_nombre} en Éxito: {str(e)}")

    # Filtrar duplicados por Enlace Directo
    unicas = {o['Enlace Directo']: o for o in ofertas}.values()
    return list(unicas)
