import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. Configuración del monitor (Pantalla completa y ocultar herramientas de descarga)
st.set_page_config(
    layout="wide", 
    page_title="Monitor de Proyecciones - Asistencias",
    initial_sidebar_state="expanded"
)

# Inyección de CSS para que el usuario en el monitor NO pueda descargar datos crudos
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDataFrame [data-testid="stDataFrameDownloadButton"] {display: none;}
    button[title="View fullscreen"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

# Título Principal del Monitor Analítico
st.title("🔮 Monitor de Proyección de Asistencias (Semana Tipo)")
st.caption("Visualización de datos históricos integrada directamente con Google Drive")

# 2. Función interna para conectar y limpiar la data de Drive de forma segura
@st.cache_data(ttl=300) # Guarda en caché por 5 minutos para evitar saturar la API
def cargar_datos_drive():
    # PEGA AQUÍ LA URL COMPLETA DE TU GOOGLE SHEETS
    url_sheets = "https://docs.google.com/spreadsheets/d/TU_ID_DE_SHEETS_AQUI/edit#gid=0"
    
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=url_sheets)
    
    # Estandarizamos los nombres de la columna PROVINCIA a Mayúsculas Sostenidas
    # Esto soluciona que Cotopaxi o Chimborazo se queden en blanco en el mapa
    if 'PROVINCIA' in df.columns:
        df['PROVINCIA'] = df['PROVINCIA'].astype(str).str.strip().str.upper()
    return df

try:
    # Carga privada de la data en el backend (El usuario no ve la tabla base)
    df_base = cargar_datos_drive()

    # 3. Filtros en la barra lateral (Estructura de Semana Tipo)
    st.sidebar.header("🎛️ Control de Proyecciones")
    
    # Filtro por Servicio (Usa la columna SERVICIO de tu Sheets)
    col_servicio = 'SERVICIO' if 'SERVICIO' in df_base.columns else 'Servicio'
    lista_servicios = ["Todos"] + list(df_base[col_servicio].dropna().unique())
    servicio_sel = st.sidebar.selectbox("Seleccionar Servicio:", lista_servicios)
    
    # Filtro por Día Nombre (Usa la columna Dia Nombre de tu Sheets)
    col_dia = 'Día Nombre' if 'Día Nombre' in df_base.columns else 'Dia Nombre'
    lista_dias = ["Todos"] + list(df_base[col_dia].dropna().unique())
    dia_sel = st.sidebar.selectbox("Seleccionar Día Tipo:", lista_dias)

    # 4. Procesamiento de los filtros en la memoria del servidor
    df_filtrado = df_base.copy()
    if servicio_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
    if dia_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado[col_dia] == dia_sel]

    # Agrupamos por provincia sumando los registros
    resumen_mapa = df_filtrado.groupby('PROVINCIA').size().reset_index(name='Proyeccion')

    # 5. Configuración del mapa coroplético (Polígonos sólidos de Ecuador)
    # GeoJSON oficial con las coordenadas exactas de las provincias en mayúsculas
    geojson_url = "https://raw.githubusercontent.com/andresabalos/Geometrias-Ecuador/master/provincias.geojson"
    
    # Mapa centrado en Ecuador con estilo Oscuro Premium ("CartoDB dark_matter")
    m = folium.Map(location=[-1.8312, -78.1834], zoom_start=7, tiles="CartoDB dark_matter")
    
    folium.Choropleth(
        geo_data=geojson_url,
        name="choropleth",
        data=resumen_mapa,
        columns=["PROVINCIA", "Proyeccion"],
        key_on="feature.properties.DPA_DESPRO", # Clave estricta de cruce matemático
        fill_color="YlGnBu", # Escala de color limpia (Amarillo -> Verde -> Azul)
        fill_opacity=0.85,
        line_opacity=0.2,
        legend_name="Volumen de Asistencias Proyectadas",
        highlight=True # Efecto visual al pasar el mouse por una provincia
    ).add_to(m)

    # Renderizar el mapa en pantalla completa
    st_folium(m, width="100%", height=650)

except Exception as e:
    st.error("🔒 Conexión segura establecida. Esperando configuración de llaves de Google en Streamlit Cloud.")
    st.info("Paso pendiente: Ingresar las credenciales en la pestaña Secrets de Streamlit.")
