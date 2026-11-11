import json
import re
import requests
from bs4 import BeautifulSoup

API_KEY = "392e8624ae3a6701c44394bc61223b66"

def extraer_exito():
    print("--- [ÉXITO] Rastreando Ofertas Reales (>= 50%) ---")
    url = "https://www.exito.com/ofertas"
    payload = {
        'api_key': API_KEY,
        'url': url,
        'render': 'true',
        'country_code': 'co'
    }
    
    ofertas = []
    try:
        res = requests.get("http://api.scraperapi.com", params=payload, timeout=90)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            tarjetas = soup.find_all(["article", "div"], class_=lambda x: x and ("product" in str(x).lower() or "item" in str(x).lower()))
            
            for prod in tarjetas[:40]:
                link_elem = prod.find("a", href=True)
                if not link_elem:
                    continue
                enlace_raw = link_elem['href']
                if "/p" not in enlace_raw and "-p" not in enlace_raw:
                    continue
                
                enlace = f"https://www.exito.com{enlace_raw}" if enlace_raw.startswith("/") else enlace_raw

                nombre_elem = prod.find(["h3", "h2", "span"], class_=lambda x: x and ("name" in str(x).lower() or "title" in str(x).lower()))
                nombre = nombre_elem.get_text(strip=True) if nombre_elem else ""
                if not nombre or len(nombre) < 5:
                    continue

                img_elem = prod.find("img")
                imagen = "https://via.placeholder.com/200?text=Exito"
                if img_elem:
                    src_candidates = [
                        img_elem.get("src"), 
                        img_elem.get("data-src"), 
                        img_elem.get("srcset")
                    ]
                    for cand in src_candidates:
                        if cand and "http" in str(cand):
                            imagen = cand.split()[0]
                            break
                        elif cand and str(cand).startswith("//"):
                            imagen = "https:" + cand.split()[0]
                            break

                texto = prod.get_text(separator=" ", strip=True)
                precios_raw = re.findall(r'\$\s*[\d\,\.]+', texto)
                precios_num = []
                for pr in precios_raw:
                    num = int(re.sub(r'[^\d]', '', pr))
                    if num > 30000:
                        precios_num.append(num)
                
                precios_num = sorted(list(set(precios_num)), reverse=True)
                if len(precios_num) < 2:
                    continue
                
                precio_normal = precios_num[0]
                precio_oferta = precios_num[-1]
                precio_tarjeta = precios_num[-2] if len(precios_num) >= 3 else precio_oferta

                if precio_oferta <= 0 or precio_normal <= precio_oferta:
                    continue

                descuento = int(((precio_normal - precio_oferta) / precio_normal) * 100)

                if 50 <= descuento <= 80:
                    ofertas.append({
                        "Nombre": nombre,
                        "Precio Normal": f"${precio_normal:,.0f}".replace(",", "."),
                        "Precio Tarjeta": f"${precio_tarjeta:,.0f}".replace(",", "."),
                        "Precio Oferta": f"${precio_oferta:,.0f}".replace(",", "."),
                        "Descuento": f"-{descuento}%",
                        "Enlace Directo": enlace,
                        "Imagen": imagen,
                        "Almacen": "Éxito"
                    })
    except Exception as e:
        print(f"Error en Éxito: {e}")
        
    print(f"Éxito aportó: {len(ofertas)} ofertas reales")
    return ofertas
