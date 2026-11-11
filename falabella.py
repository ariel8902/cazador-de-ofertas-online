import json
import re
import requests
from bs4 import BeautifulSoup

API_KEY = "392e8624ae3a6701c44394bc61223b66"

def extraer_falabella():
    print("--- [FALABELLA] Rastreando Ofertas (Filtro >= 50%) ---")
    categorias = [
        ("https://www.falabella.com.co/falabella-co/category/cat1361001/Tecnologia", "Tecnología"),
        ("https://www.falabella.com.co/falabella-co/category/cat50611/Electrodomesticos", "Electrodomésticos")
    ]
    
    ofertas = []
    
    for url, cat in categorias:
        payload = {
            'api_key': API_KEY,
            'url': url,
            'render': 'true',
            'country_code': 'co'
        }
        try:
            res = requests.get("http://api.scraperapi.com", params=payload, timeout=90)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                tarjetas = soup.find_all("div", class_=lambda x: x and ("pod" in str(x).lower() or "product" in str(x).lower())) or soup.find_all("article")
                
                for prod in tarjetas[:20]:
                    nombre_elem = prod.find(["b", "h3", "h2", "span"], class_=lambda x: x and ("title" in str(x).lower() or "name" in str(x).lower() or "pod-title" in str(x).lower()))
                    nombre = nombre_elem.get_text(strip=True) if nombre_elem else "Producto Falabella"
                    
                    link_elem = prod.find("a", href=True)
                    if not link_elem:
                        continue
                    enlace_raw = link_elem['href']
                    enlace = f"https://www.falabella.com.co{enlace_raw}" if enlace_raw.startswith("/") else enlace_raw

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
                    
                    descuento = 0
                    if precio_alto > precio_oferta:
                        descuento = int(((precio_alto - precio_oferta) / precio_alto) * 100)
                    
                    # FILTRO 50%+ DE DESCUENTO
                    if descuento >= 50:
                        ofertas.append({
                            "Nombre": nombre,
                            "Precio Normal": f"${precio_alto:,.0f}".replace(",", "."),
                            "Precio Oferta": f"${precio_oferta:,.0f}".replace(",", "."),
                            "Descuento": f"-{descuento}%",
                            "Enlace Directo": enlace,
                            "Imagen": "https://via.placeholder.com/200?text=Falabella",
                            "Almacen": "Falabella",
                            "Categoria": cat
                        })
        except Exception as e:
            print(f"Error en Falabella ({cat}): {e}")
            
    print(f"Falabella aportó: {len(ofertas)} ofertas de 50%+ de descuento")
    return ofertas
