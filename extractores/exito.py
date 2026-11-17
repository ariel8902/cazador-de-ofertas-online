import json
import os
import re
import shutil
import time

JSON_FILE = "ofertas.json"

def actualizar_base_datos(nuevos_productos, almacen_nombre="Éxito"):
    if not nuevos_productos:
        print(f"[!] ALERTA: 0 hallazgos para {almacen_nombre}. Se aborta.")
        return
    if os.path.exists(JSON_FILE):
        try:
            shutil.copy(JSON_FILE, JSON_FILE + ".bak")
        except Exception as e:
            print(f"[!] No se pudo crear .bak: {e}")
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
        print(f"[+] Base actualizada. Total en vitrina: {len(datos_actualizados)}")
    except Exception as e:
        print(f"[!] Error escribiendo: {e}")
        if os.path.exists(temp_file):
            os.remove(temp_file)

# --- NUEVO: Saca Addi y Tarjeta Éxito de los "teasers" de VTEX ---
# Si el producto NO tiene esa tarjeta, devuelve None. No inventa precios.
def extraer_precios_tarjeta(offer, precio_otros):
    precio_addi = None
    precio_tarjeta_exito = None
    if not offer:
        return precio_addi, precio_tarjeta_exito

    teasers = offer.get("teasers", []) or []
    # A veces vienen también en discountHighlights, los revisamos igual
    for t in teasers:
        nombre = str(t.get("name", "") or "").upper()
        # Efectos: acá VTEX guarda el % o el valor de descuento
        efectos = t.get("effects", {}) or {}
        params = efectos.get("parameters", []) or []
        descuento_pct = None
        precio_fijo = None
        for p in params:
            # Ej: {"name": "discount", "value": "10.0"} o {"name": "price", "value": "1959900"}
            n = str(p.get("name", "") or "").lower()
            v = str(p.get("value", "") or "").replace(",", ".")
            try:
                val = float(v)
            except:
                continue
            if "discount" in n or "percent" in n or "%" in n:
                descuento_pct = val
            if "price" in n or "value" in n:
                # Si el valor parece precio (>1000) es precio fijo, si es <100 es %
                if val > 1000:
                    precio_fijo = int(val)
                elif val > 0 and val <= 100:
                    descuento_pct = val

        precio_calculado = None
        if precio_fijo:
            precio_calculado = precio_fijo
        elif descuento_pct is not None and precio_otros:
            precio_calculado = int(round(precio_otros * (1 - descuento_pct / 100)))

        if precio_calculado is None:
            continue

        # ADDI
        if "ADDI" in nombre:
            if precio_addi is None or precio_calculado < precio_addi:
                precio_addi = precio_calculado
        # TARJETA ÉXITO - puede venir como "TARJETA EXITO", "EXITO", "T. EXITO"
        elif "EXITO" in nombre or "ÉXITO" in nombre:
            if precio_tarjeta_exito is None or precio_calculado < precio_tarjeta_exito:
                precio_tarjeta_exito = precio_calculado

    return precio_addi, precio_tarjeta_exito

def extraer_exito():
    from playwright.sync_api import sync_playwright
    hallazgos_50 = []
    vistos = set()
    print("[*] Éxito - Solo >=50% - Rápido con parada inteligente + antibloqueo")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768}, locale="es-CO"
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        page.goto("https://www.exito.com/tecnologia/televisores", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
        page.evaluate("window.scrollTo(0, 600)")
        page.wait_for_timeout(1500)

        for _from in range(0, 500, 50):
            _to = _from + 49
            url_api = f"https://www.exito.com/api/catalog_system/pub/products/search/tecnologia/televisores?_from={_from}&_to={_to}&O=OrderByBestDiscountDESC"
            print(f"[*] Página {_from}-{_to} -> pidiendo desde navegador...")

            productos = page.evaluate("""async (url) => {
                const r = await fetch(url, {headers: {'Accept': 'application/json'}});
                if (!r.ok) return {error: r.status};
                return await r.json();
            }""", url_api)

            if isinstance(productos, dict) and "error" in productos:
                print(f"[!] Bloqueo: {productos['error']}")
                break
            print(f"[*] Productos: {len(productos)}")
            if not productos:
                break

            max_desc_pagina = 0
            nuevos_en_pagina = 0

            for prod in productos:
                name = prod.get("productName")
                link_text = prod.get("linkText", "")
                if not link_text:
                    continue
                link = f"https://www.exito.com/{link_text}/p"
                if link in vistos:
                    continue
                vistos.add(link)
                items = prod.get("items", [])
                if not items:
                    continue
                sellers = items[0].get("sellers", [])
                seller = next((s for s in sellers if s.get("sellerId") == "1"), None) or (sellers[0] if sellers else {})
                offer = seller.get("commertialOffer", {}) or seller.get("commercialOffer", {})

                # --- CORREGIDO: 4 precios ---
                precio_otros = offer.get("Price")  # Otros medios: $ 2.199.900
                precio_lista = offer.get("ListPrice")  # Tachado: $ 5.999.900
                if not precio_otros or precio_otros <= 0:
                    continue

                precio_addi, precio_tarjeta_exito = extraer_precios_tarjeta(offer, precio_otros)

                # El Precio Oferta es el MÁS BARATO que SÍ exista
                candidatos = [p for p in [precio_addi, precio_tarjeta_exito, precio_otros] if p]
                precio_oferta = min(candidatos) if candidatos else precio_otros

                desc_val = 0
                if precio_lista and precio_lista > precio_oferta:
                    desc_val = int(round((1 - (precio_oferta / precio_lista)) * 100))
                if desc_val > max_desc_pagina:
                    max_desc_pagina = desc_val
                # SOLO GUARDAMOS >=50% - ahora con el precio más barato (Addi si hay)
                if desc_val >= 50:
                    images = items[0].get("images", [])
                    imagen_url = images[0].get("imageUrl") if images else ""
                    hallazgos_50.append({
                        "Almacen": "Éxito",
                        "Nombre": name,
                        "Precio Normal": precio_lista if precio_lista else precio_oferta,
                        "Precio Addi": precio_addi,
                        "Precio Tarjeta": precio_tarjeta_exito,
                        "Precio Otros": precio_otros,
                        "Precio Oferta": precio_oferta,
                        "Descuento": f"{desc_val}%",
                        "Descuento_num": desc_val,
                        "Imagen": imagen_url,
                        "Enlace Directo": link
                    })
                    nuevos_en_pagina += 1

            print(f"[*] En esta página >=50%: {nuevos_en_pagina} | Mayor descuento página: {max_desc_pagina}% | Total acumulado >=50%: {len(hallazgos_50)}")

            if max_desc_pagina < 50:
                print(f"[*] Ya bajamos de 50% en {_from}-{_to}. Paramos aquí - Antibloqueo + Rápido.")
                break

            time.sleep(1.2)
            if len(productos) < 50:
                break
        browser.close()

    print(f"[+] Total FINAL solo >=50% para Éxito: {len(hallazgos_50)}")
    actualizar_base_datos(hallazgos_50, almacen_nombre="Éxito")
    return hallazgos_50

if __name__ == "__main__":
    extraer_exito()