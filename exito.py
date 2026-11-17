import json
import os
import time
from playwright.sync_api import sync_playwright

# Archivo de base de datos central multitienda
JSON_FILE = "ofertas.json"

# Categorías clave en Éxito estructuradas para barrido controlado por lotes
CATEGORIAS_OBJETIVO = [
    {
        "nombre": "Tecnología y Pantallas",
        "query_args": "category-2/tecnologia/televisores",
    },
    {
        "nombre": "Línea Blanca",
        "query_args": "category-2/electrodomesticos/linea-blanca",
    },
    {
        "nombre": "Electrodomésticos Menores",
        "query_args": "category-2/electrodomesticos/electrodomesticos-menores",
    },
    {
        "nombre": "Hogar y Muebles",
        "query_args": "category-2/muebles-y-colchones",
    },
]


def consultar_via_navegador(page, categoria_path):
    """Navega directamente a la página de la categoría usando el navegador para que Akamai no bloquee la API."""
    url = f"https://www.exito.com/{categoria_path}?initialMap=c&initialQuery=category-2&map=category-2,category-3&orderBy=discount:desc"
    
    try:
        page.goto(url, timeout=60000)
        page.wait_for_timeout(4000)  # Esperar renderizado y carga de productos de la página
        
        # Extraer los datos directamente del estado de la página o realizar la consulta interna interceptada
        # Alternativa robusta: inyectar el fetch de la API GraphQL usando la sesión viva del navegador
        productos = page.evaluate("""async () => {
            const query = `
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
            `;
            
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
                        selectedFacets: [{key: "c", value: arguments[0]}],
                        orderBy: "discount:desc",
                        from: 0,
                        to: 24
                    },
                    query: query
                })
            });
            
            if (!response.ok) return [];
            const json = await response.json();
            return json.data?.productSearch?.products || [];
        }, categoria_path)
        
        return productos
    except Exception as e:
        print(f"[!] Error al consultar la categoría {categoria_path} vía navegador: {str(e)}")
        return []


def procesar_y_filtrar_productos(productos_brutos):
    """Aplica el filtro estricto de venta directa, precios reales y descuento >= 50%."""
    productos_procesados = []

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
        # Filtrar exclusivamente venta directa de Éxito (sellerId == '1') y descartar Marketplace
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
            productos_procesados.append(
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

    return productos_procesados


def actualizar_base_datos(nuevos_productos):
    """Actualiza de forma abierta y multitienda el archivo ofertas.json sin corromper otras tiendas."""
    datos_existentes = []

    if os.path.exists(JSON_FILE):
        try:
            with open(JSON_FILE, "r", encoding="utf-8") as f:
                datos_existentes = json.load(f)
        except json.JSONDecodeError:
            print("[!] Advertencia: ofertas.json tenía formato corrupto. Se reinicializa.")
            datos_existentes = []

    # Aislar y remover registros previos de Éxito, conservando intactas las demás tiendas (Alkosto, Catronix, etc.)
    datos_filtrados = [item for item in datos_existentes if item.get("Almacen") != "Éxito"]
    datos_actualizados = datos_filtrados + nuevos_productos

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(datos_actualizados, f, ensure_ascii=False, indent=2)

    print(f"[+] Total ofertas guardadas en vitrina (Éxito): {len(nuevos_productos)}")


def extraer_exito():
    """Función principal de extracción que utiliza Playwright para saltar Akamai de forma nativa."""
    print("[*] Iniciando sesión con Playwright para sortear Akamai...")
    todos_los_hallazgos = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale="es-CO",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        
        # Cargar la página principal primero para establecer las cookies del WAF
        page.goto("https://www.exito.com/", timeout=60000)
        page.wait_for_timeout(5000)

        for cat in CATEGORIAS_OBJETIVO:
            print(f"[*] Rastreando categoría: {cat['nombre']} ({cat['query_args']})...")
            productos_brutos = consultar_via_navegador(page, cat['query_args'])
            filtrados = procesar_y_filtrar_productos(productos_brutos)
            print(f"[+] Encontrados {len(filtrados)} productos válidos con >= 50% en {cat['nombre']}")
            todos_los_hallazgos.extend(filtrados)
            time.sleep(2)  # Pausa de cortesía entre categorías

        browser.close()

    if todos_los_hallazgos:
        actualizar_base_datos(todos_los_hallazgos)
    else:
        print("[!] El rastreo finalizó sin arrojar productos bajo el filtro estricto en las categorías consultadas.")
        actualizar_base_datos([])

    return todos_los_hallazgos


if __name__ == "__main__":
    extraer_exito()
