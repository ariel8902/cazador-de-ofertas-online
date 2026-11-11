import os
import json
import re
import requests
from bs4 import BeautifulSoup

API_KEY = "392e8624ae3a6701c44394bc61223b66"
URL_PRUEBA = "https://www.exito.com/tecnologia"

print("--- [PRUEBA DE FUEGO] Iniciando rastreo en Éxito Tecnología ---")

endpoint = "http://api.scraperapi.com"
payload = {
    'api_key': API_KEY,
    'url': URL_PRUEBA,
    'render': 'true',
    'country_code': 'co'
}

try:
    respuesta = requests.get(endpoint, params=payload, timeout=90)
    print(f"Estado HTTP devuelto por ScraperAPI: {respuesta.status_code}")
    
    if respuesta.status_code == 200:
        soup = BeautifulSoup(respuesta.text, "html.parser")
        tarjetas = soup.find_all("article") or soup.find_all("div", class_=lambda x: x and ("product" in str(x).lower() or "item" in str(x).lower()))
        print(f"Tarjetas de producto detectadas: {len(tarjetas)}")
        
        ofertas = []
        for prod in tarjetas[:10]:
            nombre_elem = prod.find(["h3", "h2", "span"], class_=lambda x: x and ("name" in str(x).lower() or "title" in str(x).lower()))
            nombre = nombre_elem.get_text(strip=True) if nombre_elem else "Producto Éxito"
            
            link_elem = prod.find("a", href=True)
            if not link_elem:
                continue
            enlace_raw = link_elem['href']
            enlace = f"https://www.exito.com{enlace_raw}" if enlace_raw.startswith("/") else enlace_raw

            texto = prod.get_text(separator=" ", strip=True)
            precios_raw = re.findall(r'\$\s*[\d\.\,]+', texto)
            precios_num = []
            for pr in precios_raw:
                num = int(re.sub(r'[^\d]', '', pr))
                if num > 10000:
                    precios_num.append(num)
            
            precios_num = sorted(list(set(precios_num)), reverse=True)
            if not precios_num:
                continue
                
            precio_alto = precios_num[0]
            precio_oferta = precios_num[-1] if len(precios_num) >= 2 else precio_alto
            
            ofertas.append({
                "Nombre": nombre,
                "Precio Normal": f"${precio_alto:,.0f}".replace(",", "."),
                "Precio Oferta": f"${precio_oferta:,.0f}".replace(",", "."),
                "Descuento": "Oferta Prueba",
                "Enlace Directo": enlace,
                "Imagen": "https://via.placeholder.com/200?text=Exito",
                "Almacen": "Éxito",
                "Categoria": "Tecnología"
            })
            
        print(f"GANGAS EXTRAÍDAS CON ÉXITO: {len(ofertas)}")
        
        # Guardar directamente en el JSON que alimenta la aplicación web
        with open("ofertas.json", "w", encoding="utf-8") as f:
            json.dump(ofertas, f, ensure_ascii=False, indent=2)
        print("¡Archivo ofertas.json actualizado correctamente!")
    else:
        print(f"Error en ScraperAPI: {respuesta.text}")

except Exception as e:
    print(f"Error crítico en la prueba: {str(e)}")
