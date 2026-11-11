import json
import re
import requests
from bs4 import BeautifulSoup

API_KEY = "392e8624ae3a6701c44394bc61223b66"
URL_PRUEBA = "https://www.exito.com/tecnologia"

print("--- [PRUEBA RÁPIDA] Probando ScraperAPI en Éxito Tecnología ---")

endpoint = "http://api.scraperapi.com"
payload = {
    'api_key': API_KEY,
    'url': URL_PRUEBA,
    'render': 'true',
    'country_code': 'co'
}

try:
    respuesta = requests.get(endpoint, params=payload, timeout=90)
    print(f"--> Código HTTP devuelto por ScraperAPI: {respuesta.status_code}")
    
    if respuesta.status_code == 200:
        soup = BeautifulSoup(respuesta.text, "html.parser")
        tarjetas = soup.find_all("article") or soup.find_all("div", class_=lambda x: x and ("product" in str(x).lower() or "item" in str(x).lower()))
        print(f"--> Tarjetas de producto encontradas: {len(tarjetas)}")
        
        ofertas = []
        for prod in tarjetas[:5]:
            nombre_elem = prod.find(["h3", "h2", "span"], class_=lambda x: x and ("name" in str(x).lower() or "title" in str(x).lower()))
            nombre = nombre_elem.get_text(strip=True) if nombre_elem else "Producto Éxito"
            
            link_elem = prod.find("a", href=True)
            if not link_elem:
                continue
            enlace_raw = link_elem['href']
            enlace = f"https://www.exito.com{enlace_raw}" if enlace_raw.startswith("/") else enlace_raw

            ofertas.append({
                "Nombre": nombre,
                "Enlace Directo": enlace,
                "Almacen": "Éxito (Prueba)",
                "Estado": "OK - ScraperAPI Funcionando"
            })
            
        print(f"--> Ofertas procesadas: {len(ofertas)}")
        
        with open("ofertas.json", "w", encoding="utf-8") as f:
            json.dump(ofertas, f, ensure_ascii=False, indent=2)
        print("--> ¡RESULTADO: ofertas.json generado exitosamente!")
    else:
        print(f"--> ERROR EN SCRAPERAPI: {respuesta.text}")

except Exception as e:
    print(f"--> Error crítico en la prueba: {str(e)}")
