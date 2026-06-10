import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
import io

# 1. Configuración de pantalla del monitor y protección visual
st.set_page_config(layout="wide", page_title="Monitor de Proyecciones")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDataFrame [data-testid="stDataFrameDownloadButton"] {display: none;}
    button[title="View fullscreen"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

# Control del Menú Lateral
if "modulo_activo" not in st.session_state:
    st.session_state.modulo_activo = "🔮 Proyecciones"

st.sidebar.title("🗂️ Menú Principal")
if st.sidebar.button("🏠 Inicio", use_container_width=True):
    st.session_state.modulo_activo = "🏠 Inicio"
if st.sidebar.button("🔮 Monitor de Proyecciones", use_container_width=True):
    st.session_state.modulo_activo = "🔮 Proyecciones"

st.sidebar.markdown("---")

if st.session_state.modulo_activo == "🏠 Inicio":
    st.title("🏠 Panel de Control Principal")
    st.write("Bienvenido al sistema. Selecciona un módulo en la barra lateral.")

if st.session_state.modulo_activo == "🔮 Proyecciones":
    st.title("🔮 Monitor de Proyección de Asistencias (Semana Tipo)")
    
    @st.cache_data(ttl=60)
    def cargar_datos_directo():
        # Tu enlace directo de exportación CSV corregido
        url_csv = "https://docs.google.com/spreadsheets/d/1UWQy9XJy8UOdef1IcXWDt2Nmn7hTnsQLHby_3BhpJnc/export?format=csv"
        response = requests.get(url_csv)
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text))
            df.columns = df.columns.str.strip().str.upper()
            if 'PROVINCIA' in df.columns:
                df['PROVINCIA'] = df['PROVINCIA'].astype(str).str.strip().str.upper()
            return df
        else:
            raise Exception("No se pudo conectar a Google Drive.")

    try:
        df_base = cargar_datos_directo()

        st.sidebar.header("🎛️ Filtros del Mapa")
        col_servicio = 'SERVICIO' if 'SERVICIO' in df_base.columns else df_base.columns[1]
        lista_servicios = ["Todos"] + list(df_base[col_servicio].dropna().unique())
        servicio_sel = st.sidebar.selectbox("Seleccionar Servicio:", lista_servicios)

        col_dia = 'DÍA NOMBRE' if 'DÍA NOMBRE' in df_base.columns else ('DIA NOMBRE' if 'DIA NOMBRE' in df_base.columns else df_base.columns[2])
        lista_dias = ["Todos"] + list(df_base[col_dia].dropna().unique())
        dia_sel = st.sidebar.selectbox("Seleccionar Día Tipo:", lista_dias)

        df_filtrado = df_base.copy()
        if servicio_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
        if dia_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_dia] == dia_sel]

        resumen_mapa = df_filtrado.groupby('PROVINCIA').size().reset_index(name='Proyeccion')

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

        st_folium(m, width="100%", height=650)

    except Exception as e:
        st.error(f"❌ Error de procesamiento: {e}")
