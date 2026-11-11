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

# --- ESTILOS CSS DE MARKETING Y DISEÑO VISUAL ---
st.markdown("""
    <style>
    /* Fondo general Gris Perla / Marfil Suave */
    .stApp {
        background-color: #F1F5F9;
    }
    
    /* Barra superior de Marketing (Ticker de Avisos) */
    .marketing-ticker {
        background: linear-gradient(90deg, #1E293B 0%, #0F172A 100%);
        color: #F8FAFC;
        padding: 8px 15px;
        text-align: center;
        font-size: 0.9rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        border-radius: 8px;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    /* Franja de Aliados Comerciales (Logos de Tiendas) */
    .brand-logos-bar {
        background-color: #FFFFFF;
        padding: 12px 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    .store-badge {
        display: inline-block;
        padding: 6px 16px;
        margin: 0 8px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.85rem;
        letter-spacing: 0.5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .badge-exito { background-color: #FEF08A; color: #854D0E; border: 1px solid #FACC15; }
    .badge-falabella { background-color: #DCFCE7; color: #166534; border: 1px solid #4ADE80; }
    .badge-alkosto { background-color: #E0F2FE; color: #0369A1; border: 1px solid #38BDF8; }
    .badge-ktronix { background-color: #FEE2E2; color: #991B1B; border: 1px solid #F87171; }

    /* Banner de Marca Fijo Superior (Firma Comercial) */
    .brand-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
        padding: 25px 20px;
        border-radius: 12px;
        text-align: center;
        color: white;
        box-shadow: 0 4px 20px rgba(15, 23, 42, 0.15);
        margin-bottom: 25px;
        border-bottom: 4px solid #FF4B4B;
    }
    .brand-title {
        font-size: 2.5rem;
        font-weight: 900;
        letter-spacing: 1px;
        margin: 0;
        color: #FFFFFF;
        text-transform: uppercase;
    }
    .brand-title span {
        color: #FF4B4B;
    }
    .brand-subtitle {
        font-size: 1rem;
        color: #94A3B8;
        margin-top: 6px;
        font-weight: 400;
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

# --- TICKER DE MARKETING SUPERIOR ---
st.markdown("""
    <div class="marketing-ticker">
        🔥 ¡ALERTA DE PRECIOS BAJOS! • Descuentos reales del 50% al 80% verificados • Actualización automática 24/7 🚀
    </div>
""", unsafe_allow_html=True)

# --- FRANJA DE LOGOTIPOS DE ALIADOS COMERCIALES ---
st.markdown("""
    <div class="brand-logos-bar">
        <span style="font-weight: 700; color: #475569; margin-right: 15px; font-size: 0.9rem;">ALIADOS OFICIALES:</span>
        <span class="store-badge badge-exito">🟡 ÉXITO</span>
        <span class="store-badge badge-falabella">🟢 FALABELLA</span>
        <span class="store-badge badge-alkosto">🔵 ALKOSTO</span>
        <span class="store-badge badge-ktronix">🔴 KTRONIX</span>
    </div>
""", unsafe_allow_html=True)

# --- BANNER DE MARCA FIJO (FIRMA COMERCIAL) ---
st.markdown("""
    <div class="brand-header">
        <div class="brand-title">🎯 CAZADOR DE <span>GANGAS</span></div>
        <div class="brand-subtitle">La vitrina inteligente con las ofertas más implacables del mercado colombiano. ¡Págalo al mejor precio!</div>
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
