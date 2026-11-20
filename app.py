import streamlit as st
import pandas as pd
import json
import os
import base64
import urllib.request
import time

from exito import extraer_exito
from alkosto import extraer_alkosto
from ktronix import extraer_ktronix
from falabella import extraer_falabella

# Configuración de página con la marca comercial definitiva
st.set_page_config(
    page_title="Cazador de Ofertas Online | Vitrina Oficial",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- NUEVO: Formato colombiano $ 1.959.900 ---
def formato_pesos(valor):
    if valor is None or valor == "":
        return None
    try:
        n = int(float(valor))
    except:
        return None
    # 1959900 -> $ 1.959.900
    return "$ " + f"{n:,}".replace(",", ".")

# Función para convertir imágenes locales a base64
def obtener_base64_imagen(ruta):
    if os.path.exists(ruta):
        with open(ruta, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode("utf-8")
    return ""

img_exito = obtener_base64_imagen("exito.png")
img_falabella = obtener_base64_imagen("falabella.png")
img_alkosto = obtener_base64_imagen("alkosto.png")
img_ktronix = obtener_base64_imagen("ktronix.png")

# --- ESTILOS CSS: LOGOS GRANDES FIJOS Y BANNER AMARILLO COMPACTO ---
st.markdown("""
    <style>
    .stApp {
        background-color: #F8FAFC;
        margin-top: 15px;
    }

    header[data-testid="stHeader"] {
        background-color: #FFFFFF !important;
        border-bottom: 1px solid #E2E8F0 !important;
        visibility: visible !important;
    }

    .top-fixed-logos-bar {
        position: fixed;
        top: 2px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 999999;
        display: flex;
        align-items: center;
        gap: 35px;
        pointer-events: auto;
        background: #FFFFFF;
        padding: 4px 20px;
        border-radius: 8px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    
    .store-logo-img {
        height: 58px;
        object-fit: contain;
        transition: transform 0.2s ease;
    }
    .store-logo-img:hover {
        transform: scale(1.08);
    }

    .main-header-banner {
        background: #FFD100;
        padding: 12px 20px;
        border-radius: 12px;
        color: #1E293B;
        box-shadow: 0 4px 15px rgba(255, 209, 0, 0.2);
        margin-bottom: 20px;
        margin-top: -10px;
        border: none;
        text-align: center;
    }
    .brand-title {
        font-size: 1.8rem;
        font-weight: 900;
        margin: 0;
        color: #0F172A;
        letter-spacing: 1px;
        text-transform: uppercase;
        display: inline-block;
    }
    .brand-title span {
        color: #DC2626;
    }
    .brand-subtitle {
        font-size: 0.85rem;
        color: #1E293B;
        margin: 2px 0 0 0;
        font-weight: 700;
    }

    div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {
        background-color: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stVerticalBlock"] div[data-testid="stContainer"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }

    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# Inicializar métricas de sesión
if 'vistas' not in st.session_state:
    st.session_state.vistas = 150
if 'clics' not in st.session_state:
    st.session_state.clics = 38

# --- LECTURA EN VIVO DIRECTA DESDE GITHUB (SIN CACHÉ ESTANCADA) ---
@st.cache_data(ttl=30)
def obtener_ofertas_en_vivo():
    timestamp = int(time.time())
    urls_posibles = [
        f"https://raw.githubusercontent.com/ariel8902/cazador-de-ofertas-online/principal/ofertas.json?t={timestamp}",
        f"https://raw.githubusercontent.com/ariel8902/cazador-de-ofertas-online/main/ofertas.json?t={timestamp}"
    ]
    datos_crudos = []
    for url in urls_posibles:
        try:
            req = urllib.request.Request(url, headers={"Cache-Control": "no-cache"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    datos_crudos = json.loads(resp.read().decode("utf-8"))
                    break
        except Exception:
            continue

    if not datos_crudos and os.path.exists("ofertas.json"):
        try:
            with open("ofertas.json", "r", encoding="utf-8") as f:
                datos_crudos = json.load(f)
        except Exception:
            datos_crudos = []

    if isinstance(datos_crudos, list):
        return [
            item for item in datos_crudos
            if isinstance(item, dict) and item.get("Almacen") and item.get("Nombre") and item.get("Precio Oferta")
        ]
    return []

ofertas_actuales = obtener_ofertas_en_vivo()

# --- PANEL DE ADMINISTRACIÓN OCULTO EN LA BARRA LATERAL ---
with st.sidebar:
    st.markdown("### ⚙️ Menú de Navegación")
    almacen = st.selectbox("Filtrar por Almacén:", ["Todos los Almacenes", "Éxito", "Falabella", "Alkosto", "Ktronix"])
    
    st.markdown("---")
    with st.expander("🛠️ Panel Admin (Gestión)"):
        st.metric("👁️ Vistas Totales", st.session_state.vistas)
        st.metric("🖱️ Clics a Ofertas", st.session_state.clics)
        if st.button("🔄 Actualizar Vitrina Ahora"):
            st.cache_data.clear()
            st.rerun()

# --- BARRA SUPERIOR FIJA CON LOS LOGOS AMPLIADOS ---
st.markdown(f"""
    <div class="top-fixed-logos-bar">
        <img class="store-logo-img" src="data:image/png;base64,{img_exito}" alt="Éxito">
        <img class="store-logo-img" src="data:image/png;base64,{img_falabella}" alt="Falabella">
        <img class="store-logo-img" src="data:image/png;base64,{img_alkosto}" alt="Alkosto">
        <img class="store-logo-img" src="data:image/png;base64,{img_ktronix}" alt="Ktronix">
    </div>
""", unsafe_allow_html=True)

# --- BANNER SUPERIOR CON LA NUEVA MARCA ---
st.markdown("""
    <div class="main-header-banner">
        <div class="brand-title">🎯 CAZADOR DE <span>OFERTAS ONLINE</span></div>
        <div class="brand-subtitle">La vitrina inteligente con los descuentos más implacables de Colombia (Descuentos reales ≥ 50%)</div>
    </div>
""", unsafe_allow_html=True)

# Filtrar ofertas por almacén seleccionado
ofertas_para_mostrar = ofertas_actuales
if almacen != "Todos los Almacenes" and ofertas_para_mostrar:
    almacen_limpio = almacen.lower().replace("é", "e")
    ofertas_para_mostrar = [
        o for o in ofertas_para_mostrar 
        if o.get("Almacen", "").lower().replace("é", "e") == almacen_limpio
    ]

# --- VITRINA DE PRODUCTOS ---
if ofertas_para_mostrar:
    st.markdown(f"### 🛒 **Oportunidades Disponibles ({len(ofertas_para_mostrar)} productos)**")
    cols = st.columns(3)
    for idx, item in enumerate(ofertas_para_mostrar):
        with cols[idx % 3]:
            with st.container(border=True):
                tienda = item.get('Almacen', 'Desconocido')
                if tienda == "Éxito":
                    st.markdown("🟡 **[ ÉXITO ]**")
                elif tienda == "Falabella":
                    st.markdown("🟢 **[ FALABELLA ]**")
                elif tienda == "Alkosto":
                    st.markdown("🔵 **[ ALKOSTO ]**")
                elif tienda == "Ktronix":
                    st.markdown("🔴 **[ KTRONIX ]**")
                else:
                    st.markdown(f"⚪ **[ {tienda} ]**")

                st.image(item.get("Imagen", "https://via.placeholder.com/200"), width="stretch")
                st.subheader(item.get("Nombre", "Producto"))
                
                # --- CORREGIDO: 4 precios con $ y puntos ---
                precio_normal = formato_pesos(item.get("Precio Normal"))
                precio_oferta = formato_pesos(item.get("Precio Oferta"))
                precio_addi = formato_pesos(item.get("Precio Addi"))
                precio_tarjeta = formato_pesos(item.get("Precio Tarjeta"))
                precio_otros = formato_pesos(item.get("Precio Otros"))

                if precio_normal:
                    st.markdown(f"❌ **Precio Regular:** ~{precio_normal}~")
                
                # Si ya tiene Addi / Tarjeta / Otros, los muestra. Si no tiene, NO inventa nada.
                if precio_addi:
                    st.markdown(f"⭐ **Addi:** **{precio_addi}**")
                if precio_tarjeta:
                    st.markdown(f"💳 **Precio Tarjeta Éxito:** **{precio_tarjeta}**")
                if precio_otros:
                    st.markdown(f"💵 **Otros Medios:** **{precio_otros}**")
                
                if precio_oferta:
                    st.markdown(f"🔥 **Precio Oferta:** **{precio_oferta}**")
                
                st.markdown(f"📉 **Descuento:** 🔥 **{item.get('Descuento')}**")
                
                if st.link_button(f"🔗 Ver Oferta en {tienda}", item.get("Enlace Directo", "#")):
                    st.session_state.clics += 1
else:
    st.info("ℹ️ No hay ofertas cargadas en este momento. Vuelva a consultar más tarde.")
