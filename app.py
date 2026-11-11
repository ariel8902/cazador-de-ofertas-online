import streamlit as st
import pandas as pd
import json
import os
import base64

from exito import extraer_exito
from alkosto import extraer_alkosto
from ktronix import extraer_ktronix
from falabella import extraer_falabella

# Configuración de página con diseño ancho y título técnico
st.set_page_config(
    page_title="Smart Ofertas Colombia | Vitrina Oficial",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Función para convertir imágenes locales a base64 para que carguen perfecto en HTML
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

# --- ESTILOS CSS: LOGOS GRANDES Y BANNER COMPACTO CORPORATIVO ---
st.markdown("""
    <style>
    /* Fondo general de la aplicación */
    .stApp {
        background-color: #F8FAFC;
        margin-top: 15px;
    }

    /* Estilizar la barra superior nativa de Streamlit para que sea fija y limpia */
    header[data-testid="stHeader"] {
        background-color: #FFFFFF !important;
        border-bottom: 1px solid #E2E8F0 !important;
        visibility: visible !important;
    }

    /* Contenedor fijo, estático y perfectamente centrado en la franja blanca */
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
        height: 58px; /* Logotipos imponentes */
        object-fit: contain;
        transition: transform 0.2s ease;
    }
    .store-logo-img:hover {
        transform: scale(1.08);
    }

    /* Banner Principal Compacto y Técnico */
    .main-header-banner {
        background: #FFD100; /* Amarillo puro brillante estilo Éxito */
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

    /* Tarjetas de Producto Modernas */
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

    /* Estilo de Botones */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# Inicializar estados
if 'vistas' not in st.session_state:
    st.session_state.vistas = 150
if 'clics' not in st.session_state:
    st.session_state.clics = 38

# Cargar ofertas guardadas
if 'gangas_guardadas' not in st.session_state or len(st.session_state.gangas_guardadas) == 0:
    if os.path.exists("ofertas.json"):
        try:
            with open("ofertas.json", "r", encoding="utf-8") as f:
                datos = json.load(f)
                if isinstance(datos, list):
                    st.session_state.gangas_guardadas = datos
        except Exception:
            st.session_state.gangas_guardadas = []

# --- PANEL DE ADMINISTRACIÓN OCULTO EN LA BARRA LATERAL ---
with st.sidebar:
    st.markdown("### ⚙️ Menú de Navegación")
    almacen = st.selectbox("Filtrar por Almacén:", ["Todos los Almacenes", "Éxito", "Falabella", "Alkosto", "Ktronix"])
    
    st.markdown("---")
    with st.expander("🛠️ Panel Admin (Gestión)"):
        st.metric("👁️ Vistas Totales", st.session_state.vistas)
        st.metric("🖱️ Clics a Ofertas", st.session_state.clics)
        if st.button("🚀 Forzar Rastreo en Vivo"):
            with st.spinner("Rastreando tiendas aliadas..."):
                res = []
                res.extend(extraer_exito())
                res.extend(extraer_falabella())
                res.extend(extraer_alkosto())
                res.extend(extraer_ktronix())
                if res:
                    st.session_state.gangas_guardadas = res
                    with open("ofertas.json", "w", encoding="utf-8") as f:
                        json.dump(res, f, ensure_ascii=False, indent=2)
                    st.success(f"¡{len(res)} ofertas actualizadas!")
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

# --- BANNER SUPERIOR TÉCNICO Y COMERCIAL ---
st.markdown("""
    <div class="main-header-banner">
        <div class="brand-title">🎯 SMART <span>OFERTAS</span> COLOMBIA</div>
        <div class="brand-subtitle">La vitrina inteligente con las oportunidades más implacables del mercado (Descuentos reales ≥ 50%)</div>
    </div>
""", unsafe_allow_html=True)

# Filtrar ofertas por almacén seleccionado
ofertas_para_mostrar = st.session_state.gangas_guardadas
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

                st.image(item.get("Imagen", "https://via.placeholder.com/200"), use_container_width=True)
                st.subheader(item.get("Nombre", "Producto"))
                
                st.markdown(f"❌ **Precio Regular:** ~{item.get('Precio Normal')}~")
                st.markdown(f"💳 **Precio Tarjeta:** **{item.get('Precio Tarjeta', item.get('Precio Oferta'))}**")
                st.markdown(f"💵 **Otros Medios:** **{item.get('Precio Oferta')}**")
                st.markdown(f"📉 **Descuento:** 🔥 **{item.get('Descuento')}**")
                
                if st.link_button(f"🔗 Ver Oferta en {tienda}", item.get("Enlace Directo", "#")):
                    st.session_state.clics += 1
else:
    st.info("ℹ️ No hay ofertas cargadas en este momento. Vuelva a consultar más tarde o ejecute el rastreo desde el panel de administración.")
