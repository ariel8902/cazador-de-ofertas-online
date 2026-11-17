# actualizar_solo_alkosto.py - VERSION FINAL, entiende Exito y Alkosto
import json
from extractores.alkosto import extraer_alkosto

def descuento_num(o):
    # Exito ya tiene Descuento_num, Alkosto tiene Descuento
    if o.get("Descuento_num") is not None:
        try: return int(o.get("Descuento_num"))
        except: pass
    v = o.get("Descuento", 0)
    try:
        if isinstance(v, str): v = v.replace("%","").strip()
        return int(float(v))
    except: return 0

def clave_unica(o):
    # Busca Enlace Directo (Exito) o Enlace (Alkosto)
    enlace = (o.get("Enlace Directo") or o.get("Enlace") or "").strip()
    if enlace:
        return ("LINK", enlace)
    # Si no hay enlace, usa Almacen + Nombre/Producto
    nombre = o.get("Nombre") or o.get("Producto") or ""
    return ("NOMBRE", o.get("Almacen",""), nombre)

print("=== SOLO ALKOSTO - FINAL ===")

with open("ofertas.json", "r", encoding="utf-8") as f:
    todas = json.load(f)

print(f"Antes: {len(todas)}")
from collections import Counter
print("Antes:", Counter([o.get("Almacen") for o in todas]))

todas_sin_alkosto = [o for o in todas if o.get("Almacen") != "Alkosto"]
print(f"Exito intacto: {len(todas_sin_alkosto)}")

nuevas = extraer_alkosto()
print(f"Alkosto nuevo: {len(nuevas)}")
for o in nuevas:
    o["Almacen"] = "Alkosto"
    o["Tarjeta"] = "Tarjeta Alkosto"
    # Para que Alkosto tambien tenga Descuento_num como Exito
    o["Descuento_num"] = descuento_num(o)

todas_final = todas_sin_alkosto + nuevas

vistos = set()
unicas = []
for o in todas_final:
    k = clave_unica(o)
    if k not in vistos:
        vistos.add(k)
        unicas.append(o)

unicas = sorted(unicas, key=lambda x: descuento_num(x), reverse=True)

with open("ofertas.json", "w", encoding="utf-8") as f:
    json.dump(unicas, f, ensure_ascii=False, indent=2)

print(f"\n=== GUARDADO FINAL ===")
print(f"Total: {len(unicas)}")
print("Ahora:", Counter([o.get("Almacen") for o in unicas]))
print("Debe ser Exito 126 + Alkosto 23 = 149")