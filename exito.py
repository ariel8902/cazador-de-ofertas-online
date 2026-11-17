import json
import os
import time
from playwright.sync_api import sync_playwright

# Archivo de base de datos central multitienda
JSON_FILE = "ofertas.json"

# URL directa de liquidación y tecnología en Éxito
URL_VITRINA = "https://www.exito.com/tecnologia/televisores?initialMap=c&initialQuery=tecnologia&map=c,c&orderBy=discount:desc"


def extraer_exito():
    """Motor de extracción profesional basado en análisis de DOM y estado renderizado para evitar bloqueos de API."""
    print("[*] Iniciando motor de extracción robusto para Éxito...")
    todos_los_hallazgos = []

    with sync_playwright() as p:
        # Lanzamiento optimizado para entornos CI/CD (GitHub Actions)
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

        try:
            print(f"[*] Navegando a la vitrina de ofertas...")
            page.goto(URL_VITRINA, timeout=60000)
            
            # Esperar a que el DOM renderice las tarjetas de productos de VTEX
            print("[*] Esperando renderizado de elementos en el DOM...")
            page.wait_for_selector("article", timeout=30000)
            time.sleep(4)  # Pausa de estabilización para carga de imágenes y precios dinámicos

            # Scroll controlado para forzar la carga de elementos perezosos (lazy loading)
            for _ in range(2):
                page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
                time.sleep(2)

            # Extracción estructurada directamente desde las tarjetas de producto renderizadas
            productos_extraidos = page.evaluate("""() => {
                const items = [];
                // Selector estándar de tarjetas de producto en VTEX / Éxito
                const cards = document.querySelectorAll('article');
                
                cards.forEach(card => {
                    try {
                        // Nombre del producto
                        const nameEl = card.querySelector('h3, h2, [data-testid*="product-name"]');
                        const name = nameEl ? nameEl.innerText.trim() : '';
                        
                        // Enlace directo
                        const linkEl = card.querySelector('a');
                        const href = linkEl ? linkEl.getAttribute('href') : '';
                        
                        // Imagen
                        const imgEl = card.querySelector('img');
                        const imgSrc = imgEl ? (imgEl.getAttribute('src') || imgEl.getAttribute('data-src')) : '';
                        
                        // Precios (Búsqueda de textos con formato de moneda COP)
                        const textContent = card.innerText;
                        
                        if (name && href) {
                            items.push({
                                name: name,
                                link: href.startsWith('http') ? href : 'https://www.exito.com' + href,
                                image: imgSrc,
                                rawText: textContent
                            });
                        }
                    } catch (err) {}
                });
                
                return items;
            }""")

            print(f"[+] Se capturaron {len(productos_extraidos)} elementos del DOM.")

            for item in productos_extraidos:
                nombre = item["name"]
                enlace = item["link"]
                imagen = item["image"]
                raw_text = item["rawText"]

                # Procesamiento analítico de precios desde el texto crudo de la tarjeta
                # Buscamos patrones de precios en el texto extraído
                import re
                # Extraer todos los valores numéricos con formato de precio colombiano ($ X.XXX.XXX)
                precios_encontrados = re.findall(r'\$\s*[\d\.,]+', raw_text)
                
                if len(precios_encontrados) < 2:
                    continue  # Si no hay al menos precio normal y precio oferta, descartamos

                # Limpieza y conversión de precios
                def limpiar_precio(val_str):
                    try:
                        clean = re.sub(r'[^\d]', '', val_str)
                        return int(clean) if clean else 0
                    except:
                        return 0

                valores = [limpiar_precio(p) for p in precios_encontrados if limpiar_precio(p) > 10000]
                
                if len(valores) < 2:
                    continue

                # En VTEX el precio mayor suele ser el ListPrice y el menor el Offer Price
                precio_normal = max(valores)
                precio_oferta = min(valores)

                if precio_normal <= 0 or precio_oferta >= precio_normal:
                    continue

                porcentaje_desc = int(((precio_normal - precio_oferta) / precio_normal) * 100)

                # Regla de oro estricta: Descuento real obligatorio >= 50% y descarte de Marketplace externo si aplica
                if porcentaje_desc >= 50:
                    todos_los_hallazgos.append(
                        {
                            "Almacen": "Éxito",
                            "Nombre": nombre,
                            "Imagen": imagen,
                            "Precio Normal": f"${precio_normal:,.0f}".replace(",", "."),
                            "Precio Tarjeta": None,
                            "Precio Oferta": f"${precio_oferta:,.0f}".replace(",", "."),
                            "Descuento": f"{porcentaje_desc}% OFF",
                            "Enlace Directo": enlace,
                        }
                    )

        except Exception as e:
            print(f"[!] Error crítico en el motor DOM: {str(e)}")
        finally:
            browser.close()

    # Actualización segura de la base de datos central multitienda
    actualizar_base_datos(todos_los_hallazgos)
    return todos_los_hallazgos


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

    print(f"[+] Total ofertas válidas guardadas en vitrina (Éxito): {len(nuevos_productos)}")
    print(f"[+] Total general en base de datos multitienda: {len(datos_actualizados)}")


if __name__ == "__main__":
    extraer_exito()
