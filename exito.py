import json
import os
import shutil
import requests

JSON_FILE = "ofertas.json"

def actualizar_base_datos(nuevos_productos, almacen_nombre="Éxito"):
    if not nuevos_productos:
        print(f"[!] ALERTA: 0 hallazgos para {almacen_nombre}. Se aborta la actualización.")
        return

    if os.path.exists(JSON_FILE):
        try:
            shutil.copy(JSON_FILE, JSON_FILE + ".bak")
        except Exception as e:
            print(f"[!] No se pudo crear el respaldo .bak: {e}")

    datos_existentes = []
    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                datos_existentes = json.load(f)
        except json.JSONDecodeError:
            datos_existentes = []

    datos_filtrados = [item for item in datos_existentes if item.get("Almacen") != almacen_nombre]
    datos_actualizados = datos_filtrados + nuevos_productos

    temp_file = JSON_FILE + ".tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(datos_actualizados, f, ensure_ascii=False, indent=4)
        os.replace(temp_file, JSON_FILE)
        print(f"[+] Base de datos actualizada con éxito. Total registros: {len(datos_actualizados)}")
    except Exception as e:
        print(f"[!] Error escribiendo la base de datos: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)

def extraer_exito_api():
    hallazgos = []
    # Endpoint directo de la API de catálogo de VTEX para televisores en Éxito
    url = "https://www.exito.com/api/catalog_system/pub/products/search/tecnologia/televisores?_from=0&_to=49&O=OrderByTopSaleDESC"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Referer": "https://www.exito.com/tecnologia/televisores",
        "Accept-Language": "es-CO,es;q=0.9"
    }

    print("[*] Consultando la API directa de VTEX para Éxito...")
    try:
        response = requests.get(url, headers=headers, timeout=25)
        print(f"[*] Status HTTP recibido: {response.status_code}")

        if response.status_code == 200:
            productos = response.json()
            print(f"[*] Productos obtenidos de la API: {len(productos)}")

            for prod in productos:
                name = prod.get("productName")
                link_text = prod.get("linkText", "")
                if not link_text:
                    continue
                link = f"https://www.exito.com/{link_text}/p"

                items = prod.get("items", [])
                if not items:
                    continue

                sellers = items[0].get("sellers", [])
                seller_encontrado = next((s for s in sellers if s.get("sellerId") == "1"), None)
                if not seller_encontrado and sellers:
                    seller_encontrado = sellers[0]
                elif not seller_encontrado:
                    seller_encontrado = {}

                offer = seller_encontrado.get("commercialOffer", {})
                precio = offer.get("Price")
                precio_lista = offer.get("ListPrice")

                images = items[0].get("images", [])
                imagen_url = images[0].get("imageUrl") if images else ""

                if precio and precio > 0:
                    descuento = ""
                    if precio_lista and precio_lista > precio:
                        desc_val = int(round((1 - (precio / precio_lista)) * 100))
                        descuento = f"{desc_val}%"

                    hallazgos.append({
                        "Almacen": "Éxito",
                        "Nombre": name,
                        "Precio Normal": precio_lista if precio_lista else precio,
                        "Precio Oferta": precio,
                        "Precio Tarjeta": None,
                        "Descuento": descuento,
                        "Imagen": imagen_url,
                        "Enlace Directo": link
                    })
        else:
            print(f"[!] La API directa devolvió un código de bloqueo o error: {response.status_code}")

    except Exception as e:
        print(f"[!] Error ejecutando la petición HTTP a la API: {e}")

    print(f"[+] Total de registros limpios procesados por API: {len(hallazgos)}")
    actualizar_base_datos(hallazgos, almacen_nombre="Éxito")
    return hallazgos

if __name__ == "__main__":
    extraer_exito_api()
