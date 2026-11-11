import os
import time
import random
import re
import requests
from bs4 import BeautifulSoup
import config
from notificador import enviar_alerta_telegram

# API Key de ScraperAPI
SCRAPER_API_KEY = os.getenv('SCRAPER_API_KEY', '392e8624ae3a6701c44394bc61223b66')

def limpiar_precio(texto_precio):
    numeros = re.sub(r'[^\d]', '', texto_precio)
    return int(numeros) if numeros else 0

def _solicitar_html_scraperapi(url_destino):
    """
    Realiza la petición HTTP a través de ScraperAPI con renderizado JS
    y proxy residencial de Colombia para saltar protecciones de Falabella.
    """
    endpoint = "http://api.scraperapi.com"
    payload = {
        'api_key': SCRAPER_API_KEY,
        'url': url_destino,
        'render': 'true',        # Obligatorio para renderizar pods dinámicos de Falabella
        'country_code': 'co',     # IP residencial en Colombia
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
            print(f"    ⚠️ [FALABELLA] ScraperAPI devolvió estado {response.status_code} para URL: {url_destino}")
            return None
    except Exception as e:
        print(f"    ❌ [FALABELLA] Error de conexión con ScraperAPI: {str(e)}")
        return None

def extraer_falabella(categoria="Ofertas", url_busqueda="https://www.falabella.com.co/falabella-co/category/cat70007/Tecnologia"):
    """
    Extrae ofertas de Falabella usando ScraperAPI en lugar de Playwright local,
    conservando la detección de desfases y alertas a Telegram.
    """
    print(f"\n[+] 🐝 Doña Abeja rastreando Falabella con ScraperAPI - Categoría: {categoria}")
    ofertas = []

    html_content = _solicitar_html_scraperapi(url_busqueda)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    
    # Captura de tarjetas de productos en la grilla de Falabella
    productos = soup.select("div[id*='testId-pod'], div[class*='pod-item'], div.search-results-4-grid")
    print(f"    📊 Tarjetas detectadas en Falabella: {len(productos)}")

    for card in productos[:15]:
        try:
            enlace_element = card.find("a", href=lambda h: h and '/product/' in h)
            if not enlace_element:
                continue

            href = enlace_element.get('href')
            if not href:
                continue

            # Saneamiento quirúrgico definitivo del enlace
            href_limpio = href.strip().split('?')[0]
            match = re.search(r'(/falabella-co/product/\d+/[^/?]+)', href_limpio)
            if match:
                enlace_producto = f"https://www.falabella.com.co{match.group(1)}"
            else:
                match_base = re.search(r'(/falabella-co/product/\d+)', href_limpio)
                if match_base:
                    enlace_producto = f"https://www.falabella.com.co{match_base.group(1)}"
                else:
                    enlace_producto = f"https://www.falabella.com.co{href_limpio}"

            texto_tarjeta = card.get_text(separator="\n", strip=True)
            lineas = [l.strip() for l in texto_tarjeta.split('\n') if l.strip()]

            nombre = None
            for linea in lineas:
                if '$' not in linea and len(linea) > 12 and not any(k in linea.lower() for k in ['envío', 'agregar', 'patrocinado', 'por ']):
                    nombre = linea
                    break

            if not nombre:
                continue

            precios_raw = [l for l in lineas if '$' in l]
            precios_num = [limpiar_precio(p) for p in precios_raw if limpiar_precio(p) > 0]
            precios_unicos = list(dict.fromkeys(precios_num))

            if len(precios_unicos) < 2:
                continue

            precio_max = max(precios_unicos)
            precios_validos = [p for p in precios_unicos if p >= (precio_max * 0.25)]

            if len(precios_validos) >= 2:
                precio_alto = max(precios_validos)

                if len(precios_validos) >= 3:
                    precio_oferta_general = sorted(precios_validos)[1]
                    precio_tarjeta = min(precios_validos)
                    descuento_general = ((precio_alto - precio_oferta_general) / precio_alto) * 100

                    if descuento_general >= config.UMBRAL_DESCUENTO_MINIMO:
                        print(f"    🔥 ¡DESFASE FALABELLA! {nombre[:45]} -> URL LIMPIA: {enlace_producto}")
                        enviar_alerta_telegram(
                            config.TELEGRAM_BOT_TOKEN,
                            config.TELEGRAM_CHAT_ID,
                            "Falabella",
                            categoria,
                            f"{nombre} (💳 Con Tarjeta Tienda: ${precio_tarjeta:,})",
                            precio_alto,
                            precio_oferta_general,
                            descuento_general,
                            enlace_producto
                        )
                        ofertas.append({
                            "Nombre": nombre,
                            "Precio Normal": f"${precio_alto:,.0f}".replace(",", "."),
                            "Precio Oferta": f"${precio_oferta_general:,.0f}".replace(",", "."),
                            "Descuento": f"-{descuento_general:.0f}%",
                            "Enlace Directo": enlace_producto,
                            "Almacen": "Falabella",
                            "Categoria": categoria
                        })
                else:
                    precio_bajo = min(precios_validos)
                    descuento = ((precio_alto - precio_bajo) / precio_alto) * 100

                    if descuento >= config.UMBRAL_DESCUENTO_MINIMO:
                        print(f"    🔥 ¡DESFASE FALABELLA! {nombre[:45]} -> URL LIMPIA: {enlace_producto}")
                        enviar_alerta_telegram(
                            config.TELEGRAM_BOT_TOKEN,
                            config.TELEGRAM_CHAT_ID,
                            "Falabella",
                            categoria,
                            nombre,
                            precio_alto,
                            precio_bajo,
                            descuento,
                            enlace_producto
                        )
                        ofertas.append({
                            "Nombre": nombre,
                            "Precio Normal": f"${precio_alto:,.0f}".replace(",", "."),
                            "Precio Oferta": f"${precio_bajo:,.0f}".replace(",", "."),
                            "Descuento": f"-{descuento:.0f}%",
                            "Enlace Directo": enlace_producto,
                            "Almacen": "Falabella",
                            "Categoria": categoria
                        })
        except Exception:
            continue

        time.sleep(random.uniform(0.3, 0.6))

    unicas = {o['Enlace Directo']: o for o in ofertas}.values()
    return list(unicas)
