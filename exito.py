import json
import os
from playwright.sync_api import sync_playwright

# Archivo de base de datos central multitienda
JSON_FILE = "ofertas.json"

# URL directa de la vitrina en Éxito
URL_VITRINA = "https://www.exito.com/tecnologia/televisores?orderBy=discount:desc"


def extraer_exito():
    """Extrae la información de manera directa y pura desde la vitrina, sin cálculos ni lógica de reevaluación."""
    print("[*] Iniciando extracción directa de datos en Éxito...")
    todos_los_hallazgos = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="es-CO",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()

        try:
            print("[*] Accediendo a la vitrina...")
            page.goto(URL_VITRINA, timeout=60000)
            page.wait_for_selector("article", timeout=30000)

            # Extracción pura de elementos del DOM sin cálculos previos
            productos_extraidos = page.evaluate("""() => {
                const items = [];
                const cards = document.querySelectorAll('article');
                
                cards.forEach(card => {
                    try {
                        const nameEl = card.querySelector('h3, h2, [data-testid*="product-name"]');
                        const linkEl = card.querySelector('a');
                        const imgEl = card.querySelector('img');
                        
                        const nombre = nameEl ? nameEl.innerText.trim() : '';
                        const enlace = linkEl ? linkEl.href : '';
                        const imagen = imgEl ? (imgEl.src || imgEl.getAttribute('data-src') || '') : '';
                        
                        // Extraer todo el texto visible de la tarjeta para capturar precios y etiquetas tal cual
                        const textContent = card.innerText.trim();
                        
                        if (nombre && enlace) {
                            items.push({
                                nombre: nombre,
                                enlace: enlace.startsWith('http') ? enlace : 'https://www.exito.com' + enlace,
                                imagen: imagen,
                                texto_crudo: textContent
                            });
                        }
                    } catch (err) {}
                });
                
                return items;
            }""")

            print(f"[+] Se extrajeron {len(productos_extraidos)} registros de la vitrina.")

            for item in productos_extraidos:
                # Mapeo limpio y directo de la información extraída
                todos_los_hallazgos.append({
                    "Almacen": "Éxito",
                    "Nombre": item["nombre"],
                    "Imagen": item["imagen"],
                    "Precio Normal": None,
                    "Precio Tarjeta": None,
                    "Precio Oferta": item["texto_crudo"],
                    "Descuento": "",
                    "Enlace Directo": item["enlace"]
                })

        except Exception as e:
            print(f"[!] Error durante la extracción: {str(e)}")
        finally:
            browser.close()

    # Volcado directo de la información extraída al archivo central
    actualizar_base_datos(todos_los_hallazgos)
    return todos_los_hallazgos


def actualizar_base_datos(nuevos_productos):
    """Actualiza de forma abierta y multitienda el archivo ofertas.json conservando las demás tiendas."""
    datos_existentes = []

    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                datos_existentes = json.load(f)
        except json.JSONDecodeError:
            print("[!] Advertencia: ofertas.json con formato corrupto. Inicializando esquema.")
            datos_existentes = []

    # Aislar registros anteriores de Éxito y anexar la extracción fresca
    datos_filtrados = [item for item in datos_existentes if item.get("Almacen") != "Éxito"]
    datos_actualizados = datos_filtrados + nuevos_productos

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(datos_actualizados, f, ensure_ascii=False, indent=2)

    print(f"[+] Total registros extraídos y guardados para Éxito: {len(nuevos_productos)}")
    print(f"[+] Total general en base de datos multitienda: {len(datos_actualizados)}")


if __name__ == "__main__":
    extraer_exito()
