import json
import requests

def extraer_exito():
    base_url = "https://www.exito.com/api/graphql"
    
    # Consulta puntual de 16 ítems ordenados por mayor descuento
    variables = {
        "first": 16,
        "after": "0",
        "sort": "discount_desc",
        "term": "",
        "selectedFacets": [
            {"key": "category-1", "value": "tecnologia"},
            {"key": "category-2", "value": "celulares"},
            {"key": "channel", "value": '{"salesChannel":"1","regionId":""}'},
            {"key": "locale", "value": "es-CO"}
        ]
    }
    
    params = {
        "operationName": "SearchQuery",
        "variables": json.dumps(variables, separators=(",", ":"))
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.exito.com/tecnologia/celulares?order=discount_desc"
    }

    print("Iniciando consulta puntual a Éxito GraphQL...")
    ofertas_validas = []

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=20)
        print(f"Código de estado HTTP: {response.status_code}")
        
        if response.status_code != 200:
            print("La respuesta no fue 200. Deteniendo ejecución para evitar bloqueos.")
            return []

        data = response.json()
        edges = data.get("data", {}).get("search", {}).get("products", {}).get("edges", [])
        print(f"Productos recibidos en el bloque: {len(edges)}")

        for edge in edges:
            node = edge.get("node", {})
            nombre = node.get("name", "Sin nombre")
            slug = node.get("slug", "")
            url_producto = f"https://www.exito.com/{slug}/p" if slug else ""
            
            imagenes = node.get("image", [])
            imagen_url = imagenes[0].get("url", "") if imagenes else ""

            offers = node.get("offers", {}).get("offers", [])
            oferta_activa = next((o for o in offers if o.get("quantity", 0) > 0), None)
            
            if not oferta_activa:
                continue

            precio_lista = float(oferta_activa.get("listPrice", 0))
            precio_oferta = float(oferta_activa.get("price", 0))

            if precio_lista <= 0 or precio_oferta <= 0:
                continue

            precio_tarjeta = precio_oferta
            medio_pago_especial = None
            
            for seller in node.get("sellers", []):
                offer = seller.get("commertialOffer", {})
                if offer.get("AvailableQuantity", 0) > 0:
                    for teaser in offer.get("teasers", []):
                        t_name = teaser.get("name", "")
                        if "exito1" in t_name.lower() or "tabladeprecios" in t_name.lower():
                            for param in teaser.get("effects", {}).get("parameters", []):
                                if param.get("name") == "PromotionalPriceTableItemsDiscount":
                                    descuento_tabla = float(param.get("value", 0))
                                    precio_calculado = precio_lista - descuento_tabla
                                    if 0 < precio_calculado < precio_tarjeta:
                                        precio_tarjeta = precio_calculado
                                        medio_pago_especial = "Tarjeta Éxito / Aliados"

            mejor_precio = min(precio_oferta, precio_tarjeta)
            porcentaje_descuento = round((1 - (mejor_precio / precio_lista)) * 100)

            if porcentaje_descuento >= 50:
                ofertas_validas.append({
                    "tienda": "Éxito",
                    "titulo": nombre,
                    "imagen": imagen_url,
                    "url": url_producto,
                    "precio_tachado": int(precio_lista),
                    "precio_general": int(precio_oferta),
                    "precio_tarjeta": int(precio_tarjeta) if medio_pago_especial else None,
                    "medio_pago": medio_pago_especial,
                    "descuento_pct": porcentaje_descuento,
                    "es_marketplace": node.get("productType", {}).get("isMkp", True)
                })

        print(f"Ofertas >= 50% filtradas: {len(ofertas_validas)}")
        return ofertas_validas

    except requests.RequestException as e:
        print(f"Error de red controlado: {e}")
        return []

if __name__ == "__main__":
    resultados = extraer_exito()
    print(json.dumps(resultados, indent=2, ensure_ascii=False))
