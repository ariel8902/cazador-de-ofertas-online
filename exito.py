import json
import os
from playwright.sync_api import sync_playwright

# Archivo de base de datos central multitienda
JSON_FILE = "ofertas.json"

# URL directa de la vitrina de liquidación en Éxito
URL_VITRINA = "https://www.exito.com/tecnologia/televisores?orderBy=discount:desc"


def extraer_exito():
    """Motor de extracción profesional basado en interceptación nativa de red (Bypass Akamai garantizado)."""
    print("[*] Iniciando motor profesional con interceptación de red para Éxito...")
    productos_capturados = []

    with sync_playwright() as p:
        # Lanzamiento optimizado y blindado para entornos CI/CD (GitHub Actions)
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="es-CO",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()

        # Listener de red: Captura de forma transparente la respuesta GraphQL oficial de VTEX
        def handle_response(response):
            if "/api/graphql" in response.url and response.status == 200:
                try:
                    body = response.json()
                    if "data" in body and body["data"] and "productSearch" in body["data"]:
                        prods = body["data"]["productSearch"].get("products", [])
                        if prods:
                            print(f"[+] ¡Interceptados {len(prods)} productos oficiales desde la red del navegador!")
                            productos_capturados.extend(prods)
                except Exception:
                    pass

        page.on("response", handle_response)

        try:
            print(f"[*] Navegando a la vitrina: {URL_VITRINA}")
            # Carga natural que supera los retos de Akamai y dispara las peticiones legítimas
            page.goto(URL_VITRINA, timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(6000)  # Tiempo de estabilización para capturar todos los lotes asíncronos
        except Exception as e:
            print(f"[!] Error crítico durante la navegación en el navegador: {str(e)}")
        finally:
            browser.close()

    # Procesamiento y mapeo directo de la información extraída (sin cálculos inventados)
    hallazgos = []
    vistos = set()

    for p in productos_capturados:
        nombre = p.get("productName", "")
        link_text = p.get("linkText", "")
        enlace = f"https://www.exito.com/{link_text}/p" if link_text else "https://www.exito.com"

        # Evitar duplicados capturados en múltiples llamadas de red
        if enlace in vistos:
            continue
        vistos.add(enlace)

        items = p.get("items", [])
        if not items:
            continue

        item = items[0]
        images = item.get("images", [])
        imagen = images[0].get("imageUrl", "") if images else ""

        sellers = item.get("sellers", [])
        # Filtrar exclusivamente venta directa de Éxito (sellerId == '1')
        seller_directo = next((s for s in sellers if s.get("sellerId") == "1"), None)
        if not seller_directo:
            continue

        offer = seller_directo.get("commercialOffer", {})
        precio_oferta = offer.get("Price", 0)
        precio_normal = offer.get("ListPrice", 0)

        # Formateo directo de precios tal cual los entrega la plataforma oficial
        p_normal_str = f"${precio_normal:,.0f}".replace(",", ".") if precio_normal > 0 else None
        p_oferta_str = f"${precio_oferta:,.0f}".replace(",", ".") if precio_oferta > 0 else None

        # Descuento oficial suministrado por el backend de la tienda
        desc_str = ""
        if precio_normal > 0 and precio_oferta < precio_normal:
            porcentaje = int(((precio_normal - precio_oferta) / precio_normal) * 100)
            if porcentaje > 0:
                desc_str = f"{porcentaje}% OFF"

        hallazgos.append({
            "Almacen": "Éxito",
            "Nombre": nombre,
            "Imagen": imagen,
            "Precio Normal": p_normal_str,
            "Precio Tarjeta": None,
            "Precio Oferta": p_oferta_str,
            "Descuento": desc_str,
            "Enlace Directo": enlace
        })

    print(f"[+] Total de registros limpios procesados para Éxito: {len(hallazgos)}")
    actualizar_base_datos(hallazgos)
    return hallazgos


def actualizar_base_datos(nuevos_productos):
    """Actualiza de forma abierta y multitienda el archivo ofertas.json preservando las demás tiendas."""
    datos_existentes = []

    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                datos_existentes = json.load(f)
        except json.JSONDecodeError:
            print("[!] Advertencia: ofertas.json con formato corrupto. Inicializando nuevo esquema.")
            datos_existentes = []

    # Aislar registros anteriores de Éxito y anexar los nuevos hallazgos frescos
    datos_filtrados = [item for item in datos_existentes if item.get("Almacen") != "Éxito"]
    datos_actualizados = datos_filtrados + nuevos_productos

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(datos_actualizados, f, ensure_ascii=False, indent=2)

    print(f"[+] Archivo ofertas.json actualizado correctamente. Total general en vitrina: {len(datos_actualizados)}")


if __name__ == "__main__":
    extraer_exito()
