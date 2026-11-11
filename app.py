import streamlit as st
import pandas as pd
import json
import os

from exito import extraer_exito
from alkosto import extraer_alkosto
from ktronix import extraer_ktronix
from falabella import extraer_falabella

st.set_page_config(
    page_title="Cazador de Gangas - Vitrina Oficial",
    page_icon="🎯",
    layout="wide"
)

# Estilos CSS Profesionales y Limpios
st.markdown("""
    <style>
    .main-title { font-size: 2.5rem; font-weight: 800; color: #FF4B4B; margin-bottom: 0px; text-align: center; }
    .sub-title { font-size: 1.1rem; color: #B0B0B0; margin-bottom: 30px; text-align: center; }
    .stButton>button { border-radius: 8px; width: 100%; }
    </style>
""", unsafe_allow_html=True)

# Inicializar estados de sesión para métricas internas
if 'vistas' not in st.session_state:
    st.session_state.vistas = 150
if 'clics' not in st.session_state:
    st.session_state.clics = 38

# Cargar ofertas desde el JSON
if 'gangas_guardadas' not in st.session_state or len(st.session_state.gangas_guardadas) == 0:
    if os.path.exists("ofertas.json"):
        try:
            with open("ofertas.json", "r", encoding="utf-8") as f:
                datos = json.load(f)
                if isinstance(datos, list):
                    st.session_state.gangas_guardadas = datos
        except Exception:
            st.session_state.gangas_guardadas = []

# --- BARRA LATERAL (FILTROS PARA EL USUARIO) ---
st.sidebar.markdown("## 🔍 **Filtrar Ofertas**")
almacen = st.sidebar.selectbox("Seleccione Almacén:", ["Todos los Almacenes", "Éxito", "Falabella", "Alkosto", "Ktronix"])

st.sidebar.markdown("---")
# ACCESO RESTRINGIDO / PANEL DE ADMINISTRACIÓN (Oculto a la vista principal)
with st.sidebar.expander("🛠️ Panel de Administración (Desarrollador)"):
    st.markdown("### 📊 Métricas Internas")
    st.metric("👁️ Vistas Totales", st.session_state.vistas)
    st.metric("🖱️ Clics Totales", st.session_state.clics)
    
    btn_ejecutar = st.button("🚀 Forzar Extracción Manual")
    if btn_ejecutar:
        with st.spinner("Actualizando ofertas en vivo..."):
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

# --- CABECERA PRINCIPAL DE LA VITRINA ---
st.markdown("<div class='main-title'>🎯 CAZADOR DE GANGAS</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Las mejores ofertas exclusivas de Colombia con 50% o más de descuento en tiempo real.</div>", unsafe_allow_html=True)

# Filtrar ofertas por almacén seleccionado
ofertas_para_mostrar = st.session_state.gangas_guardadas
if almacen != "Todos los Almacenes" and ofertas_para_mostrar:
    almacen_limpio = almacen.lower().replace("é", "e")
    ofertas_para_mostrar = [
        o for o in ofertas_para_mostrar 
        if o.get("Almacen", "").lower().replace("é", "e") == almacen_limpio
    ]

# --- RENDERIZADO DE LA VITRINA (TODAS LAS OFERTAS SIN LÍMITES) ---
if ofertas_para_mostrar:
    st.markdown(f"### 🔥 **Oportunidades Encontradas ({len(ofertas_para_mostrar)} productos disponibles)**")
    cols = st.columns(3)
    for idx, item in enumerate(ofertas_para_mostrar):
        with cols[idx % 3]:
            with st.container(border=True):
                # Insignia de Color Institucional por Almacén
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
    st.info("ℹ️ No hay ofertas disponibles en este momento para la selección actual. Vuelva a consultar más tarde o ejecute una actualización desde el panel de administración.")
