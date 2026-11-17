import json
import time
import random
import urllib.parse
import requests
from config import SCRAPER_API_KEY, SCRAPER_API_URL, MIN_DESCUENTO, MAX_DESCUENTO


def _consultar_graphql_exito(termino, after=0, first=50):
    """Consulta la API GraphQL oficial de Éxito FastStore vía ScraperAPI (sin render, 1 crédito)."""
    variables = {
        "first": first,
        "after": str(after),
        "sort": "discount_desc",
        "term": termino,
        "selectedFacets": [{"key": "channel", "value": "{\"salesChannel\":\"1\",\"regionId\":\"\"}"}],
    }
    params_gql = urllib.parse.urlencode({
        "operationName": "ProductsQuery",
        "variables": json.dumps(variables, separators=(",", ":")),
    })
    url_gql = f"https://www.exito.com/api/graphql?{params_gql}"

    payload = {
        "api_key": SCRAPER_API_KEY,
        "url": url_gql,
        "render": "false",
        "country_code": "co",
        "keep_headers": "true",
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Referer": f"https://www.exito.com/s?q={urllib.parse.quote(termino)}&sort=discount_desc",
    }

    for intento in range(2):
        try:
            res = requests.get(SCRAPER_API_URL, params=payload, headers=headers, timeout=45)
            print(f"  -> GraphQL '{termino}' | HTTP {res.status_code}")
            if res.status_code == 200:
                return res.json()
            if res.status_code >= 500 and intento == 0:
                time.sleep(random.uniform(2.0, 3.5))
                continue
            break
        except Exception as e:
            print(f"  -> Error GraphQL ({termino}): {e}")
            if intento == 0:
                time.sleep(2)
    return {}


def extraer_exito():
    print(f"--- [ÉXITO] Extracción GraphQL FastStore Ordenada por Descuento (>= {MIN_DESCUENTO}%) ---")
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
        time.sleep(random.uniform(1.0, 2.0))
        data = _consultar_graphql_exito(termino, after=0, first=50)
        edges = (
            data.get("data", {})
            .get("search", {})
            .get("products", {})
            .get("edges", [])
        )
        if not edges:
            print(f"     Término '{termino}': 0 nodos devueltos")
            continue

        encontrados_termino = 0
        for edge in edges:
            node = edge.get("node") or {}
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

            # Extraer precios reales desde las ofertas del nodo GraphQL
            precios_lista = []
            precios_venta = []
            precio_tarjeta = None

            for of in lista_ofertas:
                disponible = str(of.get("availability") or "")
                if "InStock" not in disponible and int(of.get("quantity") or 1) <= 0:
                    continue
                lp = int(float(of.get("listPrice") or 0))
                sp = int(float(of.get("price") or 0))
                if lp > 30000:
                    precios_lista.append(lp)
                if sp > 10000:
                    precios_venta.append(sp)

                # Detectar si existe precio diferencial de Tarjeta Éxito en teasers/seller
                seller_name = str(of.get("seller", {}).get("identifier") or "").lower()
                if "tarjeta" in seller_name and sp > 10000:
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

        print(f"     Término '{termino}': {len(edges)} analizados -> {encontrados_termino} ofertas >= {MIN_DESCUENTO}%")

    print(f"Éxito aportó: {len(ofertas)} ofertas reales de {MIN_DESCUENTO}%+")
    return ofertas
