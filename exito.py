import json
import os
import time
from playwright.sync_api import sync_playwright

# Archivo de base de datos central multitienda
JSON_FILE = "ofertas.json"

# Endpoint base de Éxito con ordenamiento estricto por mayor descuento
URL_LIQUIDACION = "https://www.exito.com/?orderBy=discount:desc"

GRAPHQL_QUERY = """
query SearchQuery($fullText: String, $selectedFacets: [ISelectedFacet], $orderBy: String, $from: Int, $to: Int) {
  productSearch(fullText: $fullText, selectedFacets: $selectedFacets, orderBy: $orderBy, from: $from, to: $to) {
    products {
      productName
      linkText
      items {
        images {
          imageUrl
        }
        sellers {
          sellerId
          commissions
          commercialOffer {
            Price
            ListPrice
            spotPrice
            teaser
          }
        }
      }
    }
  }
}
"""

def extraer_exito():
    """Ejecuta el rastreo profesional en Éxito utilizando la sesión viva de Playwright para extraer liquidaciones reales."""
    print("[*] Iniciando motor de extracción profesional para Éxito...")
    todos_los_hallazgos = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="es-CO",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()

        try:
            print(f"[*] Accediendo al portal principal para inicializar WAF y cookies...")
            page.goto(URL_LIQUIDACION, timeout=60000)
            page.wait_for_timeout(6000)

            print("[*] Consultando API GraphQL de liquidaciones generales...")
            productos_brutos = page.evaluate("""async (queryStr) => {
                const response = await fetch('/api/graphql?operationName=SearchQuery', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({
                        operationName: "SearchQuery",
                        variables: {
                            fullText: "",
                            selectedFacets: [],
                            orderBy: "discount:desc",
                            from: 0,
                            to: 50
                        },
                        query: queryStr
                    })
                });
                
                if (!response.ok) return [];
                const json = await response.json();
                return json.data?.productSearch?.products || [];
            }""", GRAPHQL_QUERY)

            if isinstance(productos_brutos, list) and productos_brutos:
                print(f"[+] Se obtuvieron {len(productos_brutos)} productos crudos de la API.")
                
                for p in productos_brutos:
                    nombre = p.get("productName", "")
                    link_text = p.get("linkText", "")
                    enlace = f"https://www.exito.com/{link_text}/p" if link_text else "https://www.exito.com"

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

                    if precio_normal <= 0 or precio_oferta >= precio_normal:
                        continue

                    porcentaje_desc = int(((precio_normal - precio_oferta) / precio_normal) * 100)

                    # Regla estricta: Descuento real obligatorio >= 50%
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
            else:
                print("[!] La API no retornó productos en la búsqueda general.")

        except Exception as e:
            print(f"[!] Error crítico durante la ejecución del scraper: {str(e)}")
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
