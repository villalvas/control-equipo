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

# Inyección de código CSS para bloquear visualmente herramientas de descarga e inspección
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

# Botones oficiales del Menú Principal
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
# VISTA: MONITOR DE PROYECCIONES (CON TU MÉTODO ANTERIOR)
# ==========================================
if st.session_state.modulo_activo == "🔮 Proyecciones":
    st.title("🔮 Monitor de Proyección de Asistencias (Semana Tipo)")
    st.caption("Visualización geoanalítica basada en registros históricos sincronizados en vivo")

    # 2. Función de Conexión en Vivo usando tu método nativo de Google GViz
    @st.cache_data(ttl=60)  # Sincroniza automáticamente los datos de Drive cada 60 segundos
    def cargar_datos_vía_gviz(url_base, nombre_pestana):
        try:
            # Tu fórmula matemática exacta de reemplazo de URL para saltar bloqueos
            csv_url = url_base.replace('/edit?usp=sharing', f'/gviz/tq?tqx=out:csv&sheet={nombre_pestana}').replace('/edit', f'/gviz/tq?tqx=out:csv&sheet={nombre_pestana}')
            df = pd.read_csv(csv_url)
            df.columns = df.columns.str.strip() # Limpieza estricta de espacios en encabezados
            return df
        except Exception as e:
            st.error(f"❌ Error al conectar con la pestaña '{nombre_pestana}'. Verifica que el nombre de la pestaña en Drive sea idéntico.")
            return None

    # URL oficial de tu hoja de cálculo "Consolidado historico asistencias"
    URL_REAL = "https://docs.google.com/spreadsheets/d/1UWQy9XJy8UOdef1IcXWDt2Nmn7hTnsQLHby_3BhpJnc/edit"
    
    # ⚠️ REEMPLAZA "Hoja 1" POR EL NOMBRE EXACTO DE TU PESTAÑA CON LAS PROVINCIAS
    PESTANA_OBJETIVO = "Hoja 1" 

    df_raw = cargar_datos_vía_gviz(URL_REAL, PESTANA_OBJETIVO)

    if df_raw is not None and not df_raw.empty:
        
        # Estandarización automática de columnas a MAYÚSCULAS
        df_raw.columns = df_raw.columns.str.strip().str.upper()

        # Buscador inteligente de columnas adaptado de tu código anterior
        def buscar_columna_exacta(opciones, df):
            for opcion in opciones:
                for col in df.columns:
                    if opcion.upper() in col.upper():
                        return col
            return None

        col_provincia = buscar_columna_exacta(['PROVINCIA', 'ZONA', 'REGION', 'UBICACION'], df_raw) or df_raw.columns[0]
        col_servicio = buscar_columna_exacta(['SERVICIO', 'TIPO SERVICIO', 'MODALIDAD'], df_raw) or df_raw.columns[1]
        col_dia = buscar_columna_exacta(['DÍA NOMBRE', 'DIA NOMBRE', 'DIA', 'FECHA'], df_raw) or df_raw.columns[2]

        # Forzar mayúsculas en la columna de provincias para el acople geográfico del mapa
        df_raw[col_provincia] = df_raw[col_provincia].astype(str).str.strip().str.upper()

        # Filtros Dinámicos en la Sidebar Izquierda colocados debajo del menú
        st.sidebar.header("🎛️ Filtros del Mapa")
        
        lista_servicios = ["Todos"] + list(df_raw[col_servicio].dropna().unique())
        servicio_sel = st.sidebar.selectbox("Seleccionar Servicio:", lista_servicios)
        
        lista_dias = ["Todos"] + list(df_raw[col_dia].dropna().unique())
        dia_sel = st.sidebar.selectbox("Seleccionar Día Tipo:", lista_dias)

        # Filtrado en caliente (RAM del Servidor)
        df_filtrado = df_raw.copy()
        if servicio_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
        if dia_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_dia] == dia_sel]

        # Agrupación matemática para contabilizar volúmenes de proyección
        resumen_mapa = df_filtrado.groupby(col_provincia).size().reset_index(name='Proyeccion')

        # 3. Construcción del Mapa de Ecuador Premium (Dark Mode)
        geojson_url = "https://raw.githubusercontent.com/andresabalos/Geometrias-Ecuador/master/provincias.geojson"
        m = folium.Map(location=[-1.8312, -78.1834], zoom_start=7, tiles="CartoDB dark_matter")
        
        folium.Choropleth(
            geo_data=geojson_url,
            name="choropleth",
            data=resumen_mapa,
            columns=[col_provincia, "Proyeccion"],
            key_on="feature.properties.DPA_DESPRO", # Enlace matemático con el mapa oficial sin importar tildes
            fill_color="YlGnBu",
            fill_opacity=0.85,
            line_opacity=0.2,
            legend_name="Volumen de Asistencias Proyectadas",
            highlight=True
        ).add_to(m)

        # Desplegar mapa interactivo a lo ancho del Monitor
        st_folium(m, width="100%", height=650)
        
    else:
        st.warning("⚠️ Esperando datos... Revisa que el nombre de la pestaña en la línea 56 sea el correcto.")
