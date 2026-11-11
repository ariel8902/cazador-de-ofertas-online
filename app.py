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

# --- ESTILOS CSS: BARRA FIJA SUPERIOR Y DISEÑO PROFESIONAL ---
st.markdown("""
    <style>
    /* Fondo general Gris Perla / Marfil Suave */
    .stApp {
        background-color: #F1F5F9;
        margin-top: 0px;
    }
    
    /* Barra Superior Fija y Estática (Navbar de Marca y Logos Oficiales) */
    .fixed-navbar {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
        color: white;
        padding: 10px 25px;
        z-index: 99999;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        border-bottom: 3px solid #FF4B4B;
    }
    .navbar-brand {
        font-size: 1.4rem;
        font-weight: 900;
        letter-spacing: 0.5px;
        color: #FFFFFF;
        text-transform: uppercase;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .navbar-brand span {
        color: #FF4B4B;
    }
    .navbar-logos {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-right: 40px;
    }
    .store-logo-img {
        height: 28px;
        background: white;
        padding: 3px 8px;
        border-radius: 6px;
        object-fit: contain;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }

    /* Espaciado para compensar la barra fija superior */
    .main-content-wrapper {
        margin-top: 60px;
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

# --- BARRA NAVEGADORA FIJA SUPERIOR (ESTÁTICA CON LOGOS OFICIALES) ---
st.markdown("""
    <div class="fixed-navbar">
        <div class="navbar-brand">
            🎯 CAZADOR DE <span>GANGAS</span>
        </div>
        <div class="navbar-logos">
            <span style="font-size: 0.8rem; color: #94A3B8; font-weight: 600;">ALIADOS:</span>
            <img class="store-logo-img" src="https://upload.wikimedia.org/wikipedia/commons/4/42/Almacenes_%C3%89xito_logo.svg" alt="Éxito">
            <img class="store-logo-img" src="https://upload.wikimedia.org/wikipedia/commons/3/36/Falabella_logo_%282018%29.svg" alt="Falabella">
            <img class="store-logo-img" src="https://upload.wikimedia.org/wikipedia/commons/a/a4/Alkosto_logo.svg" alt="Alkosto">
            <img class="store-logo-img" src="https://upload.wikimedia.org/wikipedia/commons/b/b3/Ktronix_logo.svg" alt="Ktronix">
        </div>
    </div>
""", unsafe_allow_html=True)

# Contenedor principal con margen superior para no solapar la barra fija
st.markdown('<div class="main-content-wrapper"></div>', unsafe_allow_html=True)

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
