import json
from exito import extraer_exito

print("--- [PRUEBA EXCLUSIVA ÉXITO 50%+] ---")
ofertas = extraer_exito()

print(f"Total ofertas filtradas obtenidas: {len(ofertas)}")

with open("ofertas.json", "w", encoding="utf-8") as f:
    json.dump(ofertas, f, ensure_ascii=False, indent=2)

print("¡Archivo ofertas.json actualizado!")
