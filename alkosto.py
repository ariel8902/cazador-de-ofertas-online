import json
import re
import requests
from bs4 import BeautifulSoup

API_KEY = "392e8624ae3a6701c44394bc61223b66"

def extraer_alkosto():
    print("--- [ALKOSTO] Rastreando Ofertas (Filtro >= 50%) ---")
    urls = [
        "https://www.alkosto.com/ofertas",
        "https://www.alkosto.com/tecnologia/c/BI_100",
        "https://www.alkosto.com/electrodomesticos/c/BI_101"
    ]
    
    ofertas = []
    
    for url in urls:
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
                tarjetas = soup.find_all(["li", "div"], class_=lambda x: x and ("product" in str(x).lower() or "item" in str(x).lower()))
                
                for prod in tarjetas:
                    nombre_elem = prod.find(["h2", "h3", "h4", "a"], class_=lambda x: x and ("name" in str(x).lower() or "title" in str(x).lower()))
                    nombre = nombre_elem.get_text(strip=True) if nombre_elem else ""
                    if not nombre or len(nombre) < 4:
                        continue
                    
                    link_elem = prod.find("a", href=True)
                    if not link_elem:
                        continue
                    enlace_raw = link_elem['href']
                    enlace = f"https://www.alkosto.com{enlace_raw}" if enlace_raw.startswith("/") else enlace_raw

                    # Captura de Imagen Real
                    img_elem = prod.find("img")
                    imagen = "https://via.placeholder.com/200?text=Alkosto"
                    if img_elem:
                        imagen = img_elem.get("data-src") or img_elem.get("src") or img_elem.get("srcset") or imagen
                        if isinstance(imagen, str) and imagen.startswith("//"):
                            imagen = "https:" + imagen

                    # Captura y Procesamiento de Precios
                    texto = prod.get_text(separator=" ", strip=True)
                    precios_raw = re.findall(r'\$\s*[\d\.\,]+', texto)
                    precios_num = []
                    for pr in precios_raw:
                        num = int(re.sub(r'[^\d]', '', pr))
                        if num > 10000:
                            precios_num.append(num)
                    
                    precios_num = sorted(list(set(precios_num)), reverse=True)
                    if len(precios_num) < 2:
                        continue
                        
                    precio_alto = precios_num[0]
                    precio_oferta = precios_num[-1]
                    
                    descuento = int(((precio_alto - precio_oferta) / precio_alto) * 100)
                    
                    if descuento >= 50:
                        # Etiqueta de Medio de Pago
                        medio_pago = "Tarjeta CrediAlkosto / Oferta Especial" if "alkosto" in texto.lower() or "tarjeta" in texto.lower() else "Cualquier Medio de Pago"
                        
                        ofertas.append({
                            "Nombre": nombre,
                            "Precio Normal": f"${precio_alto:,.0f}".replace(",", "."),
                            "Precio Oferta": f"${precio_oferta:,.0f}".replace(",", "."),
                            "Descuento": f"-{descuento}%",
                            "Medio Pago": medio_pago,
                            "Enlace Directo": enlace,
                            "Imagen": imagen,
                            "Almacen": "Alkosto"
                        })
        except Exception as e:
            print(f"Error en Alkosto: {e}")
            
    print(f"Alkosto aportó: {len(ofertas)} ofertas de 50%+")
    return ofertas
