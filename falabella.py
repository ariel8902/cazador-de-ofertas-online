import json
import re
import requests
from bs4 import BeautifulSoup

API_KEY = "392e8624ae3a6701c44394bc61223b66"

def extraer_falabella():
    print("--- [FALABELLA] Rastreando Ofertas Reales (>= 50%) ---")
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
                tarjetas = soup.find_all(["div", "article"], class_=lambda x: x and ("pod" in str(x).lower() or "product" in str(x).lower()))
                
                for prod in tarjetas[:30]:
                    # 1. Enlace y filtro de producto individual
                    link_elem = prod.find("a", href=True)
                    if not link_elem:
                        continue
                    enlace_raw = link_elem['href']
                    if "/product/" not in enlace_raw and "-prod" not in enlace_raw:
                        continue
                    enlace = f"https://www.falabella.com.co{enlace_raw}" if enlace_raw.startswith("/") else enlace_raw

                    # 2. Nombre
                    nombre_elem = prod.find(["b", "h3", "h2", "span"], class_=lambda x: x and ("title" in str(x).lower() or "name" in str(x).lower()))
                    nombre = nombre_elem.get_text(strip=True) if nombre_elem else "Producto Falabella"
                    if len(nombre) < 5:
                        continue

                    # 3. Imagen real
                    img_elem = prod.find("img")
                    imagen = "https://via.placeholder.com/200?text=Falabella"
                    if img_elem:
                        src = img_elem.get("src") or img_elem.get("data-src") or img_elem.get("srcset")
                        if src and "http" in str(src):
                            imagen = src.split()[0]
                        elif src and str(src).startswith("//"):
                            imagen = "https:" + src.split()[0]

                    # 4. Precios (Normal, Tarjeta CMR y Otros Medios)
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
                        
                    precio_normal = precios_num[0]
                    precio_oferta = precios_num[-1]
                    precio_tarjeta = precios_num[-2] if len(precios_num) >= 3 else precio_oferta
                    
                    descuento = int(((precio_normal - precio_oferta) / precio_normal) * 100)
                    
                    if descuento >= 50:
                        ofertas.append({
                            "Nombre": nombre,
                            "Precio Normal": f"${precio_normal:,.0f}".replace(",", "."),
                            "Precio Tarjeta Exito": f"${precio_tarjeta:,.0f}".replace(",", "."), # Usado para Tarjeta CMR
                            "Precio Oferta": f"${precio_oferta:,.0f}".replace(",", "."),
                            "Descuento": f"-{descuento}%",
                            "Enlace Directo": enlace,
                            "Imagen": imagen,
                            "Almacen": "Falabella",
                            "Categoria": cat
                        })
        except Exception as e:
            print(f"Error en Falabella ({cat}): {e}")
            
    print(f"Falabella aportó: {len(ofertas)} ofertas de 50%+")
    return ofertas
