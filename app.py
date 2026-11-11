import streamlit as st
import pandas as pd
import json
import os

from exito import extraer_exito
from alkosto import extraer_alkosto
from ktronix import extraer_ktronix
from falabella import extraer_falabella

st.set_page_config(
    page_title="Cazador de Gangas - Panel de Control",
    page_icon="🎯",
    layout="wide"
)

st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; font-weight: 700; color: #FF4B4B; margin-bottom: 5px; }
    .sub-title { font-size: 1rem; color: #FAFAFA; margin-bottom: 25px; }
    .stButton>button { border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

if 'vistas' not in st.session_state:
    st.session_state.vistas = 150
if 'clics' not in st.session_state:
    st.session_state.clics = 38

if 'gangas_guardadas' not in st.session_state or len(st.session_state.gangas_guardadas) == 0:
    if os.path.exists("ofertas.json"):
        try:
            with open("ofertas.json", "r", encoding="utf-8") as f:
                datos = json.load(f)
                if isinstance(datos, list):
                    st.session_state.gangas_guardadas = datos
        except Exception:
            st.session_state.gangas_guardadas = []

st.sidebar.markdown("## ⚙️ **Gestión de Aplicación**")
almacen = st.sidebar.selectbox("Elija el almacén a ver:", ["Todos los Almacenes", "Éxito", "Alkosto", "Falabella", "Ktronix"])
limite_ofertas = st.sidebar.slider("Número máximo de ofertas:", min_value=5, max_value=50, value=20)
btn_ejecutar = st.sidebar.button("🚀 Ejecutar Extracción Manual", use_container_width=True)

st.markdown("<div class='main-title'>🎯 Panel de Control: Cazador de Gangas (En Vivo)</div>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["🔥 **Ofertas Extraídas (>=50%)**", "📈 **Gestión y Analítica**"])

with tab1:
    if btn_ejecutar:
        with st.spinner(f"Rastreando en vivo {almacen}..."):
            res = []
            if almacen in ["Éxito", "Exito"]:
                res = extraer_exito()
            elif almacen == "Alkosto":
                res = extraer_alkosto()
            elif almacen == "Ktronix":
                res = extraer_ktronix()
            elif almacen == "Falabella":
                res = extraer_falabella()
            elif almacen == "Todos los Almacenes":
                res.extend(extraer_exito())
                res.extend(extraer_falabella())
                res.extend(extraer_alkosto())
                res.extend(extraer_ktronix())

            if res:
                st.session_state.gangas_guardadas = res

    ofertas_para_mostrar = st.session_state.gangas_guardadas
    if almacen != "Todos los Almacenes" and ofertas_para_mostrar:
        almacen_limpio = almacen.lower().replace("é", "e")
        ofertas_para_mostrar = [
            o for o in ofertas_para_mostrar 
            if o.get("Almacen", "").lower().replace("é", "e") == almacen_limpio
        ]

    if ofertas_para_mostrar:
        st.markdown(f"### 🛒 **Catálogo de Ofertas ({len(ofertas_para_mostrar)} cargadas)**")
        cols = st.columns(3)
        for idx, item in enumerate(ofertas_para_mostrar[:limite_ofertas]):
            with cols[idx % 3]:
                with st.container(border=True):
                    # Insignia de Color por Almacén
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
                    
                    st.markdown(f"❌ **Precio Lista:** ~{item.get('Precio Normal')}~")
                    st.markdown(f"💳 **Precio Tarjeta:** **{item.get('Precio Tarjeta Exito', item.get('Precio Oferta'))}**")
                    st.markdown(f"💵 **Otros Medios:** **{item.get('Precio Oferta')}**")
                    st.markdown(f"📉 **Descuento:** 🔥 **{item.get('Descuento')}**")
                    
                    if st.link_button(f"🔗 Ver Oferta Directa #{idx+1}", item.get("Enlace Directo", "#")):
                        st.session_state.clics += 1
    else:
        st.info("ℹ️ No hay ofertas para mostrar en la selección actual. Ejecute la extracción manual.")

with tab2:
    st.markdown("### 📊 **Rendimiento y Métricas de Uso**")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total Visitas", st.session_state.vistas)
    col_b.metric("Total Clics", st.session_state.clics)
    ctr = (st.session_state.clics / st.session_state.vistas * 100) if st.session_state.vistas > 0 else 0
    col_c.metric("Ratio (CTR)", f"{ctr:.1f}%")
