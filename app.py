import streamlit as st
import pandas as pd
import json
import os

from exito import extraer_exito
from alkosto import extraer_alkosto
from ktronix import extraer_ktronix
from falabella import extraer_falabella

# Configuración de página con diseño ancho
st.set_page_config(
    page_title="Cazador de Gangas | Vitrina Oficial",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS: BARRA FIJA SUPERIOR ESTÁTICA EN LA FRANJA BLANCA ---
st.markdown("""
    <style>
    /* Fondo general de la aplicación */
    .stApp {
        background-color: #F1F5F9;
        margin-top: 15px;
    }

    /* Estilizar la barra superior nativa de Streamlit para que sea fija y limpia */
    header[data-testid="stHeader"] {
        background-color: #FFFFFF !important;
        border-bottom: 1px solid #E2E8F0 !important;
        visibility: visible !important;
    }

    /* Contenedor fijo, estático y perfectamente centrado en la franja superior */
    .top-fixed-logos-bar {
        position: fixed;
        top: 8px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 999999;
        display: flex;
        align-items: center;
        gap: 20px;
        pointer-events: auto;
        background: #FFFFFF;
        padding: 2px 15px;
        border-radius: 6px;
    }
    
    .store-badge-pill {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 800;
        font-size: 0.8rem;
        letter-spacing: 0.5px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .badge-exito { background-color: #FACC15; color: #713F12; }
    .badge-falabella { background-color: #84CC16; color: #1A2E05; }
    .badge-alkosto { background-color: #0EA5E9; color: #0C4A6E; }
    .badge-ktronix { background-color: #EF4444; color: #450A0A; }

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

# --- BARRA SUPERIOR FIJA CON IDENTIDAD VISUAL DE LAS TIENDAS ---
st.markdown("""
    <div class="top-fixed-logos-bar">
        <div class="store-badge-pill badge-exito">🟡 ÉXITO</div>
        <div class="store-badge-pill badge-falabella">🟢 FALABELLA</div>
        <div class="store-badge-pill badge-alkosto">🔵 ALKOSTO</div>
        <div class="store-badge-pill badge-ktronix">🔴 KTRONIX</div>
    </div>
""", unsafe_allow_html=True)

# --- TÍTULO PRINCIPAL DE LA MARCA ---
st.markdown("""
    <div style="margin-top: 10px; margin-bottom: 25px; text-align: center;">
        <h1 style="font-size: 2.2rem; font-weight: 900; color: #0F172A; text-transform: uppercase; margin: 0;">🎯 CAZADOR DE <span style="color: #FF4B4B;">GANGAS</span></h1>
        <p style="color: #64748B; font-size: 0.95rem; margin-top: 5px;">La vitrina inteligente con las ofertas más implacables de Colombia (Descuentos reales ≥ 50%)</p>
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
