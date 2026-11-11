import streamlit as st
import pandas as pd
import json
import os

# Importar los extractores actualizados
from exito import extraer_exito
from alkosto import extraer_alkosto
from ktronix import extraer_ktronix
from falabella import extraer_falabella

# Configuración inicial de la página
st.set_page_config(
    page_title="Cazador de Gangas - Panel de Control",
    page_icon="🎯",
    layout="wide"
)

# Estilos CSS
st.markdown("""
    <style>
    .main-title { font-size: 2.2rem; font-weight: 700; color: #FF4B4B; margin-bottom: 5px; }
    .sub-title { font-size: 1rem; color: #FAFAFA; margin-bottom: 25px; }
    .stButton>button { border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

# Inicializar estados de la sesión
if 'vistas' not in st.session_state:
    st.session_state.vistas = 150
if 'clics' not in st.session_state:
    st.session_state.clics = 38
if 'bot_token' not in st.session_state:
    st.session_state.bot_token = ""
if 'chat_id' not in st.session_state:
    st.session_state.chat_id = "@CazadorGangasBot"

# --- CARGA AUTOMÁTICA DESDE OFERTAS.JSON (GITHUB ACTIONS) ---
if 'gangas_guardadas' not in st.session_state:
    st.session_state.gangas_guardadas = []
    if os.path.exists("ofertas.json"):
        try:
            with open("ofertas.json", "r", encoding="utf-8") as f:
                datos_json = json.load(f)
                if isinstance(datos_json, list) and len(datos_json) > 0:
                    st.session_state.gangas_guardadas = datos_json
        except Exception as e:
            pass

# --- BARRA LATERAL ---
st.sidebar.markdown("## ⚙️ **Gestión de Aplicación**")

st.sidebar.markdown("### 📊 **Métricas en Tiempo Real**")
col_m1, col_m2 = st.sidebar.columns(2)
col_m1.metric("👁️ Vistas", st.session_state.vistas, delta="+1")
col_m2.metric("🖱️ Clics", st.session_state.clics, delta="+3")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛠️ **Control de Extractores**")
almacen = st.sidebar.selectbox("Elija el almacén a rastrear:", ["Todos los Almacenes", "Éxito", "Alkosto", "Falabella", "Ktronix"])

limite_ofertas = st.sidebar.slider("Número máximo de ofertas:", min_value=5, max_value=50, value=20)

btn_ejecutar = st.sidebar.button("🚀 Ejecutar Extracción Manual", use_container_width=True)
btn_limpiar = st.sidebar.button("🗑️ Limpiar Historial", use_container_width=True)

if btn_limpiar:
    st.session_state.gangas_guardadas = []
    if os.path.exists("ofertas.json"):
        try:
            with open("ofertas.json", "w", encoding="utf-8") as f:
                json.dump([], f)
        except Exception:
            pass
    st.rerun()

# --- PANEL PRINCIPAL ---
st.markdown("<div class='main-title'>🎯 Panel de Control: Cazador de Gangas (En Vivo)</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Gestiona la plataforma, analiza clics e interacciones y visualiza ofertas con 50%+ de descuento.</div>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🔥 **Ofertas Extraídas (>=50%)**", "📈 **Gestión y Analítica**", "🤖 **Bot de Telegram**"])

with tab1:
    if btn_ejecutar:
        with st.spinner(f"Rastreando gangas en {almacen}... Por favor espere."):
            nuevos_resultados = []
            if almacen == "Alkosto":
                nuevos_resultados = extraer_alkosto()
            elif almacen == "Éxito":
                nuevos_resultados = extraer_exito()
            elif almacen == "Ktronix":
                nuevos_resultados = extraer_ktronix()
            elif almacen == "Falabella":
                nuevos_resultados = extraer_falabella()
            elif almacen == "Todos los Almacenes":
                nuevos_resultados.extend(extraer_exito())
                nuevos_resultados.extend(extraer_alkosto())
                nuevos_resultados.extend(extraer_ktronix())
                nuevos_resultados.extend(extraer_falabella())

            if nuevos_resultados:
                st.session_state.gangas_guardadas = nuevos_resultados
                with open("ofertas.json", "w", encoding="utf-8") as f:
                    json.dump(nuevos_resultados, f, ensure_ascii=False, indent=2)
                st.success(f"¡Se capturaron {len(nuevos_resultados)} gangas con 50%+ de descuento!")
            else:
                st.warning(f"No se obtuvieron resultados para {almacen} en esta ejecución.")

    # Filtrar según selección de la barra lateral
    ofertas_a_mostrar = st.session_state.gangas_guardadas
    if almacen != "Todos los Almacenes" and ofertas_a_mostrar:
        ofertas_a_mostrar = [o for o in ofertas_a_mostrar if o.get("Almacen", "").lower() == almacen.lower()]

    if ofertas_a_mostrar:
        st.markdown(f"### 🛒 **Catálogo de Ofertas Capturadas ({len(ofertas_a_mostrar)} en pantalla)**")
        cols = st.columns(3)
        for idx, item in enumerate(ofertas_a_mostrar[:limite_ofertas]):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.image(item.get("Imagen", "https://via.placeholder.com/200"), use_container_width=True)
                    st.subheader(item.get("Nombre", "Producto"))
                    st.markdown(f"**Almacén:** `{item.get('Almacen', 'Desconocido')}`")
                    st.markdown(f"**Precio Normal:** ~{item.get('Precio Normal')}~")
                    st.markdown(f"**Precio Oferta:** `{item.get('Precio Oferta')}`")
                    st.markdown(f"**Descuento:** 🔥 `{item.get('Descuento')}`")
                    if st.link_button(f"🔗 Ver Oferta #{idx+1}", item.get("Enlace Directo", "#")):
                        st.session_state.clics += 1
    else:
        st.info("ℹ️ No hay ofertas cargadas para la selección actual. Presione 'Ejecutar Extracción Manual' o espere el ciclo nocturno de GitHub Actions.")

with tab2:
    st.markdown("### 📊 **Rendimiento y Métricas de Uso**")
    st.write("Estadísticas consolidadas sobre el comportamiento de los usuarios.")
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total Visitas Registradas", st.session_state.vistas)
    col_b.metric("Total Clics Convertidos", st.session_state.clics)
    
    ctr = (st.session_state.clics / st.session_state.vistas * 100) if st.session_state.vistas > 0 else 0
    col_c.metric("Ratio de Clics (CTR)", f"{ctr:.1f}%")

with tab3:
    st.markdown("### 🤖 **Configuración de Alertas por Telegram**")
    st.write("Ajuste las credenciales del bot encargado de notificar las ofertas capturadas.")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        token_input = st.text_input("Bot Token:", value=st.session_state.bot_token, type="password", placeholder="Ej: 123456789:ABCdef...")
    with col_t2:
        chat_input = st.text_input("Chat ID / Canal:", value=st.session_state.chat_id, placeholder="Ej: @CazadorGangasBot")
        
    if st.button("💾 Guardar Configuración de Telegram", type="primary"):
        st.session_state.bot_token = token_input
        st.session_state.chat_id = chat_input
        st.success("✅ Configuración guardada correctamente.")
