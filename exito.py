import json
import os
import shutil
from playwright.sync_api import sync_playwright

JSON_FILE = "ofertas.json"

def actualizar_base_datos(nuevos_productos, almacen_nombre="Éxito"):
    """
    Actualiza la base de datos central en ofertas.json de forma segura,
    aplicando escritura atómica (.tmp + os.replace), respaldo .bak,
    y preservando los registros de las demás tiendas.
    """
    if not nuevos_productos:
        print(f"[!] ALERTA: 0 hallazgos para {almacen_nombre}. Se aborta la actualización para no corromper la base de datos.")
        return

    # 1. Crear backup preventivo antes de tocar el archivo
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
            print("[!] El archivo ofertas.json está corrupto o vacío. Se inicializará uno nuevo.")
            datos_existentes = []

    # Filtrar removiendo únicamente la tienda que se va a actualizar
    datos_filtrados = [item for item in datos_existentes if item.get("Almacen") != almacen_nombre]
    
    # Combinar los datos limpios anteriores con los nuevos hallazgos
    datos_actualizados = datos_filtrados + nuevos_productos

    # 2. Escritura atómica para evitar corrupción si el runner se cae a mitad de escritura
    temp_file = JSON_FILE + ".tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(datos_actualizados, f, ensure_ascii=False, indent=4)
        os.replace(temp_file, JSON_FILE)
        print(f"[+] Base de datos actualizada de forma atómica. Total registros en vitrina: {len(datos_actualizados)}")
    except Exception as e:
        print(f"[!] Error crítico escribiendo la base de datos atómica: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)

def extraer_exito():
    hallazgos = []
    vistos = set()
    url = "https://www.exito.com/tecnologia/televisores?orderBy=discount:desc"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled", 
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="es-CO",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()

        def interceptar_respuesta(response):
            try:
                if "/api/graphql" in response.url and response.status == 200:
                    data = response.json()
                    data_prod = data.get("data", {}).get("productSearch", {}).get("products", [])
                    
                    if not data_prod:
                        return

                    for prod in data_prod:
                        link_text = prod.get("linkText", "")
                        if not link_text:
                            continue
                        link = f"https://www.exito.com/{link_text}/p"
                        
                        if link in vistos:
                            continue
                        vistos.add(link)

                        name = prod.get("productName")
                        items = prod.get("items", [])
                        if not items:
                            continue
                        
                        # 3. Selección de seller en 2 pasos estrictos (Prioridad Seller ID 1 = Éxito directo)
                        sellers = items[0].get("sellers", [])
                        seller_encontrado = next((s for s in sellers if s.get("sellerId") == "1"), None)
                        
                        if not seller_encontrado and sellers:
                            seller_encontrado = sellers[0]
                            # Log opcional para auditoría de marketplace
                            # print(f"[!] Sin seller principal para {name}, usando: {seller_encontrado.get('sellerName')}")
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

                            # 4. Esquema unificado 10/10 (incluyendo Precio Tarjeta y formato numérico consistente)
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
            except Exception as e:
                print(f"[!] Error parseando GraphQL: {e} - URL: {response.url[:100]}")

        page.on("response", interceptar_respuesta)

        print("[*] Iniciando motor definitivo 10/10 blindado con interceptación de red para Éxito...")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            
            try:
                page.wait_for_selector("article", timeout=20000)
            except Exception:
                print("[!] Advertencia: Selector 'article' tardó en aparecer, procediendo con la data interceptada...")

            # Scroll dinámico inteligente hasta el fondo
            last_height = page.evaluate("document.body.scrollHeight")
            for _ in range(6):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                page.wait_for_timeout(3000)
                new_height = page.evaluate("document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height

            # 5. Espera de seguridad post-scroll para capturar ráfagas lentas de GraphQL
            print("[*] Finalizado el scroll, esperando ráfagas pendientes de GraphQL...")
            page.wait_for_timeout(5000)

        except Exception as e:
            print(f"[!] Error crítico durante la navegación en el navegador: {e}")
        finally:
            browser.close()

    print(f"[+] Total de registros limpios procesados para Éxito: {len(hallazgos)}")
    actualizar_base_datos(hallazgos, almacen_nombre="Éxito")
    return hallazgos

if __name__ == "__main__":
    extraer_exito()
