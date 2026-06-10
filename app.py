import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. Configuración de pantalla del monitor y protección visual contra descargas
st.set_page_config(
    layout="wide", 
    page_title="Monitor de Proyecciones - Semana Tipo",
    initial_sidebar_state="expanded"
)

# Inyección de código CSS para bloquear visualmente cualquier botón de descarga o inspección en el monitor
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

# Botones de navegación para cambiar de módulo
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
    st.caption("Visualización geoanalítica basada en registros históricos vinculados directamente a Google Drive")

    # 2. Función interna de conexión directa usando tu enlace real transformado a CSV
    @st.cache_data(ttl=300)
    def cargar_datos_drive():
        # Enlace oficial transformado para descarga directa en la memoria RAM del servidor
        url_csv = "https://docs.google.com/spreadsheets/d/1UWQy9XJy8UOdef1IcXWDt2Nmn7hTnsQLHby_3BhpJnc/export?format=csv"
        
        # Lectura veloz con pandas
        df = pd.read_csv(url_csv)
        
        # Estandarización estricta de provincias a MAYÚSCULAS para evitar fallos de emparejamiento gráfico
        if 'PROVINCIA' in df.columns:
            df['PROVINCIA'] = df['PROVINCIA'].astype(str).str.strip().str.upper()
        return df

    try:
        # Cargando la información en el backend
        df_base = cargar_datos_drive()

        # Filtros dinámicos en la barra lateral debajo del menú
        st.sidebar.header("🎛️ Filtros del Mapa")
        
        # Detector automático de nombre de columna para el Servicio
        col_servicio = 'SERVICIO' if 'SERVICIO' in df_base.columns else 'Servicio'
        lista_servicios = ["Todos"] + list(df_base[col_servicio].dropna().unique())
        servicio_sel = st.sidebar.selectbox("Seleccionar Servicio:", lista_servicios)
        
        # Detector automático de nombre de columna para el Día de la Semana
        col_dia = 'Día Nombre' if 'Día Nombre' in df_base.columns else 'Dia Nombre'
        lista_dias = ["Todos"] + list(df_base[col_dia].dropna().unique())
        dia_sel = st.sidebar.selectbox("Seleccionar Día Tipo:", lista_dias)

        # Filtrado lógico en memoria RAM
        df_filtrado = df_base.copy()
        if servicio_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
        if dia_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_dia] == dia_sel]

        # Conteo matemático de registros por provincia para alimentar la intensidad del mapa
        resumen_mapa = df_filtrado.groupby('PROVINCIA').size().reset_index(name='Proyeccion')

        # 3. Configuración y renderizado del mapa coroplético de Ecuador
        geojson_url = "https://raw.githubusercontent.com/andresabalos/Geometrias-Ecuador/master/provincias.geojson"
        
        # Inicialización del mapa centrado con estilo Oscuro Premium (estilo centro de comando)
        m = folium.Map(location=[-1.8312, -78.1834], zoom_start=7, tiles="CartoDB dark_matter")
        
        folium.Choropleth(
            geo_data=geojson_url,
            name="choropleth",
            data=resumen_mapa,
            columns=["PROVINCIA", "Proyeccion"],
            key_on="feature.properties.D
