import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. Configuración estética del Monitor estilo Ejecutivo
st.set_page_config(
    layout="wide", 
    page_title="Monitor de Proyecciones - Semana Tipo",
    initial_sidebar_state="expanded"
)

# Inyección de código CSS para bloquear herramientas de descarga nativas
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDataFrame [data-testid="stDataFrameDownloadButton"] {display: none;}
    button[title="View fullscreen"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 🎛️ CONTROL DE NAVEGACIÓN (BARRA LATERAL IZQUIERDA)
# ==========================================
if "modulo_activo" not in st.session_state:
    st.session_state.modulo_activo = "🔮 Proyecciones"

st.sidebar.title("🗂️ Menú Principal")

if st.sidebar.button("🏠 Inicio", use_container_width=True):
    st.session_state.modulo_activo = "🏠 Inicio"
if st.sidebar.button("🔮 Monitor de Proyecciones", use_container_width=True):
    st.session_state.modulo_activo = "🔮 Proyecciones"

st.sidebar.markdown("---")

# ==========================================
# VISTA: INICIO
# ==========================================
if st.session_state.modulo_activo == "🏠 Inicio":
    st.title("🏠 Panel de Control Principal")
    st.write("Bienvenido al sistema de control de equipo. Selecciona un módulo en la barra lateral para empezar.")

# ==========================================
# VISTA: MONITOR DE PROYECCIONES
# ==========================================
if st.session_state.modulo_activo == "🔮 Proyecciones":
    st.title("🔮 Monitor de Proyección de Asistencias (Semana Tipo)")
    st.caption("Visualización geoanalítica basada en registros históricos sincronizados en vivo")

    # Función de Conexión usando el método nativo GViz
    @st.cache_data(ttl=60)
    def cargar_datos_vía_gviz(url_base, nombre_pestana):
        try:
            csv_url = url_base.replace('/edit?usp=sharing', f'/gviz/tq?tqx=out:csv&sheet={nombre_pestana}').replace('/edit', f'/gviz/tq?tqx=out:csv&sheet={nombre_pestana}')
            df = pd.read_csv(csv_url)
            df.columns = df.columns.str.strip()
            return df
        except Exception as e:
            st.error(f"❌ Error al conectar con la pestaña '{nombre_pestana}'. Verifica que el nombre de la pestaña en Drive sea idéntico.")
            return None

    # URL oficial de tu hoja de cálculo "Consolidado historico asistencias"
    URL_REAL = "https://docs.google.com/spreadsheets/d/1UWQy9XJy8UOdef1IcXWDt2Nmn7hTnsQLHby_3BhpJnc/edit"
    
    # Sincronización corregida con tu pestaña real
    PESTANA_OBJETIVO = "Consolidado" 

    df_raw = cargar_datos_vía_gviz(URL_REAL, PESTANA_OBJETIVO)

    if df_raw is not None and not df_raw.empty:
        try:
            # Estandarización automática de columnas a MAYÚSCULAS
            df_raw.columns = df_raw.columns.str.strip().str.upper()

            # Buscador inteligente mapeando la estructura real de tu hoja
            def buscar_columna_exacta(opciones, df):
                for opcion in opciones:
                    for col in df.columns:
                        if opcion.upper() in col.upper():
                            return col
                return None

            col_provincia = buscar_columna_exacta(['PROVINCIA', 'ZONA'], df_raw) or 'PROVINCIA'
            col_servicio = buscar_columna_exacta(['SERVICIO', 'TIPO SERVICIO'], df_raw) or 'SERVICIO'
            
            # Mapeamos la fecha de creación para extraer los días automáticamente si no viene la columna "Día Nombre"
            col_fecha = buscar_columna_exacta(['FECHA CREACIÓN', 'FECHA CREACION', 'FECHA'], df_raw)

            if col_fecha and col_fecha in df_raw.columns:
                df_raw[col_fecha] = pd.to_datetime(df_raw[col_fecha], errors='coerce', dayfirst=True)
                # Creamos dinámicamente los días de la semana en español para tus filtros
                dias_espanol = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}
                df_raw['DÍA TIPO'] = df_raw[col_fecha].dt.dayofweek.map(dias_espanol)
                col_dia = 'DÍA TIPO'
            else:
                col_dia = buscar_columna_exacta(['DÍA NOMBRE', 'DIA NOMBRE', 'DIA'], df_raw) or df_raw.columns[2]

            # Forzar mayúsculas en provincias para el acople con el mapa geográfico
            df_raw[col_provincia] = df_raw[col_provincia].astype(str).str.strip().str.upper()

            # Filtros Dinámicos colocados debajo del menú
            st.sidebar.header("🎛️ Filtros del Mapa")
            
            lista_servicios = ["Todos"] + list(df_raw[col_servicio].dropna().unique())
            servicio_sel = st.sidebar.selectbox("Seleccionar Servicio:", lista_servicios)
            
            if col_dia in df_raw.columns:
                lista_dias = ["Todos"] + list(df_raw[col_dia].dropna().unique())
                dia_sel = st.sidebar.selectbox("Seleccionar Día Tipo:", lista_dias)
            else:
                dia_sel = "Todos"

            # Filtrado lógico en RAM
            df_filtrado = df_raw.copy()
            if servicio_sel != "Todos":
                df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
            if dia_sel != "Todos" and col_dia in df_raw.columns:
                df
