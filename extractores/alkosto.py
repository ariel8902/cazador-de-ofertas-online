import re
import time
import random
from playwright.sync_api import sync_playwright
from config import MIN_DESCUENTO, MAX_DESCUENTO

def extraer_alkosto():
    print(f"--- [ALKOSTO] Modo Equilibrado (>= {MIN_DESCUENTO}%) ---")
    urls = [
        "https://www.alkosto.com/search?text=celular",
        "https://www.alkosto.com/search?text=televisor",
        "https://www.alkosto.com/search?text=portatil",
        "https://www.alkosto.com/search?text=nevera",
    ]
    ofertas = []
    enlaces_vistos = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--no-sandbox"])
        page = browser.new_page(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        for url in urls:
            try:
                print(f"Abriendo: {url}")
                page.goto(url, timeout=60000, wait_until="domcontentloaded")
                time.sleep(4 + random.uniform(0.5, 1.5))
                for _ in range(3):
                    page.mouse.wheel(0, 1000)
                    time.sleep(1.5 + random.uniform(0.5, 1))

                links = page.query_selector_all("a[href*='/p/']")
                print(f"  Encontrados {len(links)} links - vamos a revisar maximo 40")
                contador = 0
                for link_elem in links:
                    if contador >= 40:
                        break
                    try:
                        enlace_raw = link_elem.get_attribute("href")
                        if not enlace_raw:
                            continue
                        enlace = f"https://www.alkosto.com{enlace_raw}" if enlace_raw.startswith("/") else enlace_raw
                        enlace = enlace.split("?")[0]
                        if enlace in enlaces_vistos:
                            continue
                        if "/p/" not in enlace:
                            continue

                        texto_tarjeta = link_elem.evaluate("""el => {
                            let p = el;
                            for (let i = 0; i < 6; i++) {
                                p = p.parentElement;
                                if (!p) break;
                                if (p.innerText && p.innerText.includes('$')) return p.innerText;
                            }
                            return el.innerText || '';
                        }""")
                        if not texto_tarjeta or "$" not in texto_tarjeta:
                            continue

                        lineas = [l.strip() for l in texto_tarjeta.split("\n") if l.strip()]
                        nombre = lineas[0] if lineas else ""
                        if not nombre or len(nombre) < 6:
                            continue

                        imagen = "https://via.placeholder.com/200?text=Alkosto"
                        try:
                            img_src = link_elem.evaluate("""el => {
                                let p = el;
                                for (let i = 0; i < 6; i++) {
                                    p = p.parentElement;
                                    if (!p) break;
                                    let img = p.querySelector('img');
                                    if (img) return img.getAttribute('data-src') || img.getAttribute('src') || '';
                                }
                                return '';
                            }""")
                            if img_src:
                                if img_src.startswith("//"):
                                    imagen = "https:" + img_src
                                elif img_src.startswith("/"):
                                    imagen = "https://www.alkosto.com" + img_src
                                elif img_src.startswith("http"):
                                    imagen = img_src
                        except Exception:
                            pass

                        # === CORRECCIÓN: PRECIOS POR ETIQUETA, NO POR ORDEN ===
                        texto_low = texto_tarjeta.lower()
                        # Todos los precios
                        precios_raw = re.findall(r'\$\s*[\d\.\,]+', texto_tarjeta)
                        precios_num = sorted(list(set([
                            int(re.sub(r'[^\d]', '', pr)) for pr in precios_raw
                            if int(re.sub(r'[^\d]', '', pr) or 0) > 30000
                        ])), reverse=True)
                        if len(precios_num) < 2:
                            continue

                        precio_normal = precios_num[0]

                        # 1. Buscar precio HOY / OFERTA por texto: "hoy" cerca del precio
                        precio_oferta = None
                        # Recorrer líneas buscando $ + Hoy en la misma línea o la siguiente
                        for i, linea in enumerate(lineas):
                            if "$" in linea:
                                num = int(re.sub(r'[^\d]', '', linea) or 0)
                                if num <= 30000 or num == precio_normal:
                                    continue
                                contexto = " ".join(lineas[max(0,i-1):i+2]).lower()
                                if "hoy" in contexto:
                                    precio_oferta = num
                                    break
                        # Si no hay "Hoy", oferta = el mayor que no es normal y no es tarjeta
                        # (en Alkosto el Hoy siempre es el más alto después del tachado)
                        if precio_oferta is None:
                            # Lo dejamos para después, primero buscamos tarjeta
                            pass

                        # 2. Buscar precio TARJETA ALKOSTO por etiqueta
                        precio_tarjeta = 0
                        for i, linea in enumerate(lineas):
                            if "$" in linea:
                                num = int(re.sub(r'[^\d]', '', linea) or 0)
                                if num <= 30000 or num == precio_normal:
                                    continue
                                contexto = " ".join(lineas[max(0,i-1):i+2]).lower()
                                # Solo la azul de Alkosto, ignorar Addi / otras / casita
                                if "tarjeta" in contexto and "alkosto" in texto_low:
                                    # Verificar que esta línea esté cerca de la palabra tarjeta
                                    if "tarjeta" in contexto:
                                        precio_tarjeta = num
                                        break

                        # 3. Si no encontramos Hoy, oferta = el mayor restante que no sea tarjeta ni normal
                        if precio_oferta is None:
                            restantes = [x for x in precios_num if x != precio_normal and x != precio_tarjeta]
                            precio_oferta = restantes[0] if restantes else 0

                        # 4. Si el precio tarjeta quedó igual a oferta o es 0, no tiene tarjeta
                        if precio_tarjeta == precio_oferta:
                            precio_tarjeta = 0
                        if precio_tarjeta == 0:
                            # No forzar, queda sin tarjeta
                            pass

                        if precio_oferta <= 0 or precio_normal <= precio_oferta:
                            continue

                        # Descuento SIEMPRE con precio Hoy / Oferta, no con tarjeta
                        descuento = int(((precio_normal - precio_oferta) / precio_normal) * 100)

                        if MIN_DESCUENTO <= descuento <= MAX_DESCUENTO:
                            enlaces_vistos.add(enlace)
                            contador += 1
                            ofertas.append({
                                "Nombre": nombre,
                                "Precio Normal": precio_normal,
                                "Precio Oferta": precio_oferta,
                                "Precio Tarjeta": precio_tarjeta if precio_tarjeta > 0 else 0,
                                "Precio Addi": None,
                                "Descuento": descuento,
                                "Enlace": enlace,
                                "Enlace Directo": enlace,
                                "Imagen": imagen,
                                "Almacen": "Alkosto"
                            })
                    except Exception:
                        continue
                print(f"  Categoria lista. Llevamos {len(ofertas)} ofertas en total.")
                print("  Pausa de 6 segundos...")
                time.sleep(6)
            except Exception as e:
                print(f"Error en Alkosto ({url}): {e}")
        browser.close()
    print(f"Alkosto aportó: {len(ofertas)} ofertas reales")
    return ofertas

if __name__ == "__main__":
    resultado = extraer_alkosto()
    print(resultado[:2])