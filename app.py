import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. Configuración de pantalla completa del monitor y protección visual
st.set_page_config(
    layout="wide", 
    page_title="Monitor de Proyecciones - Semana Tipo",
    initial_sidebar_state="expanded"
)

# Inyección de código CSS para ocultar barras nativas y botones de descarga de tablas
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
# 🎛️ NAVEGACIÓN IZQUIERDA (MENÚ PRINCIPAL)
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
# MÓDULO 1: INICIO
# ==========================================
if st.session_state.modulo_activo == "🏠 Inicio":
    st.title("🏠 Panel de Control Principal")
    st.write("Bienvenido al sistema de visualización. Por favor selecciona un módulo en la barra lateral izquierda.")

# ==========================================
# MÓDULO 2: MONITOR DE PROYECCIONES
# ==========================================
if st.session_state.modulo_activo == "🔮 Proyecciones":
    st.title("🔮 Monitor de Proyección de Asistencias (Semana Tipo)")
    st.caption("Carga local de base de datos histórica para visualización geoanalítica inmediata")

    # Contenedor principal de carga para el monitor
    st.info("📊 Para activar el mapa interactivo de Ecuador, por favor arrastra o selecciona tu archivo histórico abajo.")
    
    archivo_subido = st.file_uploader(
        "Selecciona tu archivo 'Consolidado historico asistencias' (Formatos aceptados: .xlsx o .csv)", 
        type=["csv", "xlsx"]
    )

    if archivo_subido is not None:
        try:
            # Lectura del archivo según el formato cargado
            if archivo_subido.name.endswith('.csv'):
                df_base = pd.read_csv(archivo_subido)
            else:
                df_base = pd.read_excel(archivo_subido)

            # Estandarizamos todas las columnas a MAYÚSCULAS
            df_base.columns = df_base.columns.str.strip().str.upper()

            # Forzar formato en la columna clave de provincias
            if 'PROVINCIA' in df_base.columns:
                df_base['PROVINCIA'] = df_base['PROVINCIA'].astype(str).str.strip().str.upper()

            # Configuración de los Filtros Dinámicos en la Sidebar debajo del menú
            st.sidebar.header("🎛️ Filtros del Mapa")
            
            col_servicio = 'SERVICIO' if 'SERVICIO' in df_base.columns else df_base.columns[1]
            lista_servicios = ["Todos"] + list(df_base[col_servicio].dropna().unique())
            servicio_sel = st.sidebar.selectbox("Seleccionar Servicio:", lista_servicios)

            col_dia = 'DÍA NOMBRE' if 'DÍA NOMBRE' in df_base.columns else ('DIA NOMBRE' if 'DIA NOMBRE' in df_base.columns else df_base.columns[2])
            lista_dias = ["Todos"] + list(df_base[col_dia].dropna().unique())
            dia_sel = st.sidebar.selectbox("Seleccionar Día Tipo:", lista_dias)

            # Filtrado inteligente en la memoria RAM del servidor
            df_filtrado = df_base.copy()
            if servicio_sel != "Todos":
                df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
            if dia_sel != "Todos":
                df_filtrado = df_filtrado[df_filtrado[col_dia] == dia_sel]

            # Conteo estadístico por provincia
            resumen_mapa = df_filtrado.groupby('PROVINCIA').size().reset_index(name='Proyeccion')

            # Renderizado del mapa coroplético estilo Centro de Comando (Dark Mode)
            geojson_url = "https://raw.githubusercontent.com/andresabalos/Geometrias-Ecuador/master/provincias.geojson"
            m = folium.Map(location=[-1.8312, -78.1834], zoom_start=7, tiles="CartoDB dark_matter")
            
            folium.Choropleth(
                geo_data=geojson_url,
                name="choropleth",
                data=resumen_mapa,
                columns=["PROVINCIA", "Proyeccion"],
                key_on="feature.properties.DPA_DESPRO",
                fill_color="YlGnBu",
                fill_opacity=0.85,
                line_opacity=0.2,
                legend_name="Volumen de Asistencias Proyectadas",
                highlight=True
            ).add_to(m)

            # Despliegue del mapa interactivo a pantalla completa
            st_folium(m, width="100%", height=650)

        except Exception as e:
            st.error(f"❌ Error al procesar las columnas del archivo: {e}")
            st.info("Verifica que tu documento contenga las columnas llamadas 'PROVINCIA', 'SERVICIO' y 'Día Nombre'.")
    else:
        st.write("✨ Esperando archivo de datos...")
