import re
import json
import time
import random
import urllib.parse
import requests
from bs4 import BeautifulSoup
from config import SCRAPER_API_KEY, SCRAPER_API_URL, MIN_DESCUENTO, MAX_DESCUENTO


def _descargar_pagina_rapida(url):
    """Descarga la página pública de Éxito con IP Colombia sin render pesado (1 crédito, ~2s)."""
    payload = {
        "api_key": SCRAPER_API_KEY,
        "url": url,
        "render": "false",
        "country_code": "co",
        "keep_headers": "true",
    }
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Accept-Language": "es-CO,es;q=0.9",
    }
    for intento in range(2):
        try:
            res = requests.get(SCRAPER_API_URL, params=payload, headers=headers, timeout=45)
            print(f"  -> {url} | HTTP {res.status_code}")
            if res.status_code == 200:
                return res.text
            if res.status_code >= 500 and intento == 0:
                time.sleep(random.uniform(2.0, 3.5))
                continue
            break
        except Exception as e:
            print(f"  -> Error conexión ({url}): {e}")
            if intento == 0:
                time.sleep(2)
    return None


def _buscar_productos_en_json(obj, acumulados):
    """Recorre recursivamente el JSON __NEXT_DATA__ buscando nodos de producto de FastStore."""
    if isinstance(obj, dict):
        if "slug" in obj and ("offers" in obj or "isVariantOf" in obj):
            acumulados.append(obj)
        for v in obj.values():
            _buscar_productos_en_json(v, acumulados)
    elif isinstance(obj, list):
        for item in obj:
            _buscar_productos_en_json(item, acumulados)


def _extraer_desde_next_data(html, enlaces_vistos):
    """Extrae productos reales en JSON puro desde el script __NEXT_DATA__ incrustado en la página."""
    soup = BeautifulSoup(html, "html.parser")
    script_nd = soup.find("script", id="__NEXT_DATA__")
    if not script_nd or not script_nd.string:
        return []

    try:
        data = json.loads(script_nd.string)
    except Exception:
        return []

    nodos = []
    _buscar_productos_en_json(data, nodos)
    resultados = []

    for node in nodos:
        nombre = (node.get("isVariantOf", {}).get("name") or node.get("name") or "").strip()
        slug = (node.get("slug") or "").strip()
        if not nombre or not slug:
            continue

        enlace = f"https://www.exito.com/{slug}/p"
        if enlace in enlaces_vistos:
            continue

        imagenes = node.get("image") or []
        imagen_hd = imagenes[0].get("url", "") if imagenes else ""
        if not imagen_hd or "placeholder" in imagen_hd.lower():
            continue

        offers_block = node.get("offers") or {}
        lista_ofertas = offers_block.get("offers") or []
        if not lista_ofertas:
            continue

        precios_lista = []
        precios_venta = []
        precio_tarjeta = None

        for of in lista_ofertas:
            disp = str(of.get("availability") or "")
            if "OutOfStock" in disp:
                continue
            lp = int(float(of.get("listPrice") or 0))
            sp = int(float(of.get("price") or 0))
            if lp > 30000:
                precios_lista.append(lp)
            if sp > 10000:
                precios_venta.append(sp)

            seller_id = str(of.get("seller", {}).get("identifier") or "").lower()
            if "tarjeta" in seller_id and sp > 10000:
                precio_tarjeta = sp

        if not precios_lista or not precios_venta:
            continue

        precio_normal = max(precios_lista)
        precio_otros = min(precios_venta)
        if not precio_tarjeta or precio_tarjeta > precio_otros:
            precio_tarjeta = precio_otros

        if precio_normal <= precio_otros:
            continue

        mejor_precio = min(precio_tarjeta, precio_otros)
        descuento = int(((precio_normal - mejor_precio) / precio_normal) * 100)

        if MIN_DESCUENTO <= descuento <= MAX_DESCUENTO:
            enlaces_vistos.add(enlace)
            resultados.append({
                "Nombre": nombre,
                "Precio Normal": f"${precio_normal:,.0f}".replace(",", "."),
                "Precio Tarjeta": f"${precio_tarjeta:,.0f}".replace(",", "."),
                "Precio Oferta": f"${precio_otros:,.0f}".replace(",", "."),
                "Descuento": f"-{descuento}%",
                "Enlace Directo": enlace,
                "Imagen": imagen_hd,
                "Almacen": "Éxito",
            })

    return resultados


def extraer_exito():
    print(f"--- [ÉXITO] Extracción JSON __NEXT_DATA__ Ordenada por Descuento (>= {MIN_DESCUENTO}%) ---")
    urls = [
        "https://www.exito.com/hogar?order=discount_desc&page=1",
        "https://www.exito.com/electrodomesticos?order=discount_desc&page=1",
        "https://www.exito.com/tecnologia/televisores?order=discount_desc&page=1",
        "https://www.exito.com/tecnologia/celulares?order=discount_desc&page=1",
        "https://www.exito.com/tecnologia/computadores?order=discount_desc&page=1",
        "https://www.exito.com/moda-y-accesorios?order=discount_desc&page=1",
        "https://www.exito.com/deportes?order=discount_desc&page=1",
        "https://www.exito.com/s?q=oferta&sort=discount_desc",
        "https://www.exito.com/s?q=descuento&sort=discount_desc",
    ]

    ofertas = []
    enlaces_vistos = set()

    for url in urls:
        time.sleep(random.uniform(1.0, 2.0))
        html = _descargar_pagina_rapida(url)
        if not html:
            continue

        nuevas = _extraer_desde_next_data(html, enlaces_vistos)
        print(f"     Ofertas JSON reales extraídas en esta URL: {len(nuevas)}")
        ofertas.extend(nuevas)

    print(f"Éxito aportó: {len(ofertas)} ofertas reales de {MIN_DESCUENTO}%+")
    return ofertas
