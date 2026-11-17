import json
import re
from playwright.sync_api import sync_playwright

def formatear_pesos(valor):
    return f"${int(round(valor)):,}".replace(",", ".")

def limpiar_numero_precio(texto):
    if not texto:
        return 0.0
    digitos = re.sub(r"[^\d]", "", str(texto))
    return float(digitos) if digitos else 0.0

def es_producto_valido_comercialmente(nombre, slug, sellers):
    texto_check = f"{nombre} {slug}".lower()
    palabras_prohibidas = ["reacondicionado", "refurbished", "usado", "exhibicion", "open box", "seminuevo"]
    if any(palabra in texto_check for palabra in palabras_prohibidas):
        return False

    if "-mp-" in slug.lower():
        return False

    vende_exito = any(
        "exito" in str(s.get("sellerName", "")).lower() or str(s.get("sellerId", "")) == "1"
        for s in sellers
    )
    return vende_exito

def leer_precios_reales_ficha(page, url_producto):
    """
    Entra a la ficha real (/p) y extrae los precios exactos publicados en pantalla,
    separando Tarjeta Éxito de Addi y Otros Medios.
    """
    try:
        page.goto(url_producto, wait_until="domcontentloaded", timeout=35000)
        page.wait_for_timeout(2800)

        datos_dom = page.evaluate("""() => {
            const textoCompleto = document.body.innerText || "";
            const lineas = textoCompleto.split('\\n').map(l => l.trim()).filter(Boolean);
            
            // Buscar bloques de precios visibles en la zona principal de compra
            const preciosEncontrados = [];
            for (let i = 0; i < lineas.length; i++) {
                const l = lineas[i];
                if (/^\\$\\s*[\\d\\.]+$/.test(l)) {
                    const contexto = (lineas[i-1] || "") + " | " + l + " | " + (lineas[i+1] || "");
                    preciosEncontrados.push({
                        valor: l,
                        anterior: lineas[i-1] || "",
                        siguiente: lineas[i+1] || "",
                        contexto: contexto.toLowerCase()
                    });
                }
            }

            // Buscar porcentaje explícito tipo "- 61%"
            const matchPorcentaje = textoCompleto.match(/-\\s*(\\d{1,2})\\s*%/);
            return {
                precios: preciosEncontrados.slice(0, 10),
                porcentajeBadge: matchPorcentaje ? parseInt(matchPorcentaje[1], 10) : null,
                vendidoPorExito: /vendido por:\\s*exito/i.test(textoCompleto)
            };
        }""")

        if not datos_dom.get("vendidoPorExito"):
            return None

        precio_normal = 0.0
        precio_otros = 0.0
        precio_tarjeta = None

        for item in datos_dom.get("precios", []):
            val = limpiar_numero_precio(item["valor"])
            if val < 10000:
                continue
            ctx = item["contexto"]
            sig = item["siguiente"].lower()
            ant = item["anterior"].lower()

            # 1. Precio normal tachado (suele ir justo después del badge "- 61%")
            if "%" in ant and precio_normal == 0:
                precio_normal = val
            # 2. Precio explícito de Tarjeta Éxito (ignora Addi)
            elif ("tarjeta" in sig or "tarjeta" in ctx) and "addi" not in ctx:
                if precio_tarjeta is None or val < precio_tarjeta:
                    precio_tarjeta = val
            # 3. Precio Otros medios
            elif "otros" in sig or "otros" in ctx:
                if precio_otros == 0:
                    precio_otros = val

        # Respaldo si "Otros" no tenía la palabra al lado pero es el mayor de los precios de oferta
        candidatos_oferta = [
            limpiar_numero_precio(p["valor"])
            for p in datos_dom.get("precios", [])
            if limpiar_numero_precio(p["valor"]) >= 10000
            and limpiar_numero_precio(p["valor"]) != precio_normal
            and "addi" not in p["siguiente"].lower()
        ]
        if precio_otros == 0 and candidatos_oferta:
            precio_otros = max(candidatos_oferta)

        if precio_normal <= 0 or precio_otros <= 0 or precio_otros >= precio_normal:
            return None

        if precio_tarjeta and (precio_tarjeta >= precio_otros or precio_tarjeta <= 0):
            precio_tarjeta = None

        mejor_precio = precio_tarjeta if precio_tarjeta else precio_otros
        descuento_real = round((1 - (mejor_precio / precio_normal)) * 100)

        return {
            "precio_normal": precio_normal,
            "precio_tarjeta": precio_tarjeta,
            "precio_otros": precio_otros,
            "descuento_real": descuento_real
        }
    except Exception:
        return None

def extraer_exito():
    print("Iniciando navegador real (Chromium) con base funcional + validación en ficha /p...")
    ofertas_validas = []
    candidatos_por_url = {}
    bloques_capturados = []

    rutas_categorias = [
        "https://www.exito.com/tecnologia/televisores?order=discount_desc",
        "https://www.exito.com/tecnologia/celulares?order=discount_desc",
        "https://www.exito.com/tecnologia/computadores/portatiles?order=discount_desc",
        "https://www.exito.com/electrodomesticos/refrigeracion/neveras?order=discount_desc",
        "https://www.exito.com/electrodomesticos/lavado-y-secado/lavadoras?order=discount_desc",
        "https://www.exito.com/electrodomesticos/pequenos-electrodomesticos/freidoras?order=discount_desc"
    ]

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                locale="es-CO",
                timezone_id="America/Bogota"
            )
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page = context.new_page()

            def interceptar_respuesta(response):
                try:
                    if "/api/graphql" in response.url and "SearchQuery" in response.url and response.status == 200:
                        data = response.json()
                        edges = data.get("data", {}).get("search", {}).get("products", {}).get("edges", [])
                        if edges:
                            bloques_capturados.extend(edges)
                except Exception:
                    pass

            page.on("response", interceptar_respuesta)

            # 1. Misma captura que ya nos funcionó
            for url_cat in rutas_categorias:
                print(f"Explorando categoría: {url_cat}")
                try:
                    page.goto(url_cat, wait_until="domcontentloaded", timeout=40000)
                    page.wait_for_timeout(4500)
                    page.evaluate("window.scrollBy(0, 900)")
                    page.wait_for_timeout(1500)
                except Exception as nav_err:
                    print(f"Aviso navegando {url_cat}: {nav_err}")

            print(f"Total nodos interceptados en categorías: {len(bloques_capturados)}")

            # 2. Pre-filtrar candidatos limpios vendidos directo por Éxito
            for edge in bloques_capturados:
                node = edge.get("node", {})
                nombre = node.get("name", "Sin nombre").strip()
                slug = node.get("slug", "")
                if not slug:
                    continue

                url_producto = f"https://www.exito.com/{slug}/p"
                if url_producto in candidatos_por_url:
                    continue

                sellers = node.get("sellers", [])
                if not es_producto_valido_comercialmente(nombre, slug, sellers):
                    continue

                offers = node.get("offers", {}).get("offers", [])
                oferta_activa = next((o for o in offers if o.get("quantity", 0) > 0), None)
                if not oferta_activa:
                    continue

                p_lista = float(oferta_activa.get("listPrice", 0))
                p_oferta = float(oferta_activa.get("price", 0))
                if p_lista > 0 and p_oferta > 0 and (1 - p_oferta / p_lista) >= 0.40:
                    imagenes = node.get("image", [])
                    imagen_url = imagenes[0].get("url", "https://via.placeholder.com/200") if imagenes else "https://via.placeholder.com/200"
                    candidatos_por_url[url_producto] = {
                        "nombre": nombre,
                        "imagen": imagen_url,
                        "url": url_producto
                    }

            print(f"Candidatos limpios para verificar precio real en ficha /p: {len(candidatos_por_url)}")

            # 3. Validar cada candidato entrando a su ficha real (/p)
            for url_prod, info in candidatos_por_url.items():
                datos_reales = leer_precios_reales_ficha(page, url_prod)
                if not datos_reales:
                    continue

                desc = datos_reales["descuento_real"]
                if 50 <= desc <= 85:
                    ofertas_validas.append({
                        "Almacen": "Éxito",
                        "Nombre": info["nombre"],
                        "Imagen": info["imagen"],
                        "Precio Normal": formatear_pesos(datos_reales["precio_normal"]),
                        "Precio Tarjeta": formatear_pesos(datos_reales["precio_tarjeta"]) if datos_reales["precio_tarjeta"] else None,
                        "Precio Oferta": formatear_pesos(datos_reales["precio_otros"]),
                        "Descuento": f"{desc}% OFF",
                        "Enlace Directo": url_prod
                    })

            browser.close()

        ofertas_validas.sort(key=lambda x: int(x["Descuento"].replace("% OFF", "")), reverse=True)
        print(f"Total ofertas reales verificadas de Éxito (>= 50%): {len(ofertas_validas)}")
        return ofertas_validas

    except Exception as e:
        print(f"Error controlado en Playwright (Éxito): {e}")
        return []

if __name__ == "__main__":
    resultados = extraer_exito()
    print(json.dumps(resultados, indent=2, ensure_ascii=False))
