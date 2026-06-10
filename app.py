import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. Configuración de pantalla del monitor estilo Centro de Comando
st.set_page_config(
    layout="wide", 
    page_title="Monitor de Proyecciones - Semana Tipo",
    initial_sidebar_state="expanded"
)

# Estilos CSS para limpiar el entorno visual del dashboard
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
# 🎛️ CONTROL DE NAVEGACIÓN (MENÚ IZQUIERDO)
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

    # 2. Tu método nativo de lectura sin contraseñas (GViz)
    @st.cache_data(ttl=60)
    def cargar_datos_vía_gviz():
        try:
            url_base = "https://docs.google.com/spreadsheets/d/1UWQy9XJy8UOdef1IcXWDt2Nmn7hTnsQLHby_3BhpJnc/edit"
            pestana = "Consolidado"
            csv_url = url_base.replace('/edit?usp=sharing', f'/gviz/tq?tqx=out:csv&sheet={pestana}').replace('/edit', f'/gviz/tq?tqx=out:csv&sheet={pestana}')
            df = pd.read_csv(csv_url)
            return df
        except Exception as e:
            st.error(f"❌ Error al conectar con Google Drive: {e}")
            return None

    # Llamado y procesamiento seguro de la información
    df_raw = cargar_datos_vía_gviz()

    if df_raw is not None and not df_raw.empty:
        # Limpieza estricta de nombres de columnas (pasamos todo a mayúsculas para evitar fallas)
        df_raw.columns = df_raw.columns.str.strip().str.upper()

        # Identificamos tus columnas reales basadas en tu captura de pantalla
        col_provincia = "PROVINCIA" if "PROVINCIA" in df_raw.columns else df_raw.columns[6]
        col_servicio = "SERVICIO" if "SERVICIO" in df_raw.columns else df_raw.columns[5]
        col_fecha = "FECHA CREACIÓN DE ASISTENCIA" if "FECHA CREACIÓN DE ASISTENCIA" in df_raw.columns else (df_raw.columns[2])

        # Procesamiento de la fecha para extraer el Día Tipo automáticamente
        try:
            df_raw[col_fecha] = pd.to_datetime(df_raw[col_fecha], errors='coerce', dayfirst=True)
            dias_espanol = {0: 'Lunes', 1: 'Martes', 2: 'Miércoles', 3: 'Jueves', 4: 'Viernes', 5: 'Sábado', 6: 'Domingo'}
            df_raw['DÍA TIPO'] = df_raw[col_fecha].dt.dayofweek.map(dias_espanol)
            col_dia = 'DÍA TIPO'
        except:
            col_dia = None

        # Estandarizamos los nombres de las provincias para el mapa (Pichincha, Guayas, etc.)
        df_raw[col_provincia] = df_raw[col_provincia].astype(str).str.strip().str.upper()

        # ==========================================
        # INTERFAZ DE FILTROS EN LA BARRA LATERAL
        # ==========================================
        st.sidebar.header("🎛️ Filtros del Mapa")
        
        # Filtro de Servicio
        lista_servicios = ["Todos"] + list(df_raw[col_servicio].dropna().unique())
        servicio_sel = st.sidebar.selectbox("Seleccionar Servicio:", lista_servicios)
        
        # Filtro de Día (siempre que se haya podido parsear la fecha)
        if col_dia and col_dia in df_raw.columns:
            lista_dias = ["Todos"] + list(df_raw[col_dia].dropna().unique())
            dia_sel = st.sidebar.selectbox("Seleccionar Día Tipo:", lista_dias)
        else:
            dia_sel = "Todos"

        # Aplicación de los filtros seleccionados en la memoria RAM
        df_filtrado = df_raw.copy()
        if servicio_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
        if dia_sel != "Todos" and col_dia:
            df_filtrado = df_filtrado[df_filtrado[col_dia] == dia_sel]

        # Conteo matemático agrupado por Provincias para pintar el mapa coroplético
        resumen_mapa = df_filtrado.groupby(col_provincia).size().reset_index(name='Proyeccion')

        # ==========================================
        # CONSTRUCCIÓN DEL MAPA GEOESTADÍSTICO DE ECUADOR
        # ==========================================
        geojson_url = "https://raw.githubusercontent.com/andresabalos/Geometrias-Ecuador/master/provincias.geojson"
        
        # Creamos mapa base con estilo de noche (CartoDB dark_matter)
        m = folium.Map(location=[-1.8312, -78.1834], zoom_start=7, tiles="CartoDB dark_matter")
        
        folium.Choropleth(
            geo_data=geojson_url,
            name="choropleth",
            data=resumen_mapa,
            columns=[col_provincia, "Proyeccion"],
            key_on="feature.properties.DPA_DESPRO",
            fill_color="YlGnBu",
            fill_opacity=0.85,
            line_opacity=0.2,
            legend_name="Volumen de Asistencias Proyectadas",
            highlight=True
        ).add_to(m)

        # Despliegue interactivo del mapa a lo ancho del monitor
        st_folium(m, width="100%", height=650)
        
    else:
        st.warning("⚠️ Esperando conexión con el archivo de Google Drive. Asegúrate de que el enlace sea de libre acceso.")
