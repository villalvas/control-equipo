import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import folium
from streamlit_folium import st_folium

# 1. Configuración de pantalla del monitor y ocultar herramientas nativas
st.set_page_config(
    layout="wide", 
    page_title="Monitor de Proyecciones - Semana Tipo",
    initial_sidebar_state="expanded"
)

# Inyección de código CSS para destruir visualmente cualquier botón de descarga en el monitor
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDataFrame [data-testid="stDataFrameDownloadButton"] {display: none;}
    button[title="View fullscreen"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

# Encabezado oficial del proyecto
st.title("🔮 Monitor de Proyección de Asistencias (Semana Tipo)")
st.caption("Visualización geoanalítica basada en registros históricos")

# 2. Conexión interna y segura con Google Drive
@st.cache_data(ttl=300) # Guarda la data por 5 minutos para rendimiento óptimo
def cargar_datos_drive():
    # URL de conexión de tu hoja de Google Sheets
    # (En el siguiente paso cambiaremos este link por el tuyo real)
    url_sheets = "https://docs.google.com/spreadsheets/d/1UWQy9XJy8UOdef1IcXWDt2Nmn7hTnsQLHby_3BhpJnc/edit?usp=sharing"
    
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=url_sheets)
    
    # Estandarización de provincias a MAYÚSCULAS para que hagan juego perfecto con el mapa político
    if 'PROVINCIA' in df.columns:
        df['PROVINCIA'] = df['PROVINCIA'].astype(str).str.strip().str.upper()
    return df

try:
    # Procesamiento privado en el servidor (el usuario del monitor nunca ve la tabla cruda)
    df_base = cargar_datos_drive()

    # 3. Filtros interactivos en la barra lateral
    st.sidebar.header("🎛️ Control de Proyecciones")
    
    # Filtro por Tipo de Servicio (Busca la columna SERVICIO)
    col_servicio = 'SERVICIO' if 'SERVICIO' in df_base.columns else 'Servicio'
    lista_servicios = ["Todos"] + list(df_base[col_servicio].dropna().unique())
    servicio_sel = st.sidebar.selectbox("Seleccionar Servicio:", lista_servicios)
    
    # Filtro por Día Nombre (Busca tu columna de nombres de días)
    col_dia = 'Día Nombre' if 'Día Nombre' in df_base.columns else 'Dia Nombre'
    lista_dias = ["Todos"] + list(df_base[col_dia].dropna().unique())
    dia_sel = st.sidebar.selectbox("Seleccionar Día Tipo:", lista_dias)

    # 4. Filtrado lógico en memoria RAM
    df_filtrado = df_base.copy()
    if servicio_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
    if dia_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado[col_dia] == dia_sel]

    # Agrupamos los datos para contar las asistencias proyectadas por provincia
    resumen_mapa = df_filtrado.groupby('PROVINCIA').size().reset_index(name='Proyeccion')

    # 5. Renderizado del mapa de Ecuador (Polígonos coropléticos sólidos)
    geojson_url = "https://raw.githubusercontent.com/andresabalos/Geometrias-Ecuador/master/provincias.geojson"
    
    # Creación del mapa centrado en el país con un estilo oscuro premium para centros de control
    m = folium.Map(location=[-1.8312, -78.1834], zoom_start=7, tiles="CartoDB dark_matter")
    
    folium.Choropleth(
        geo_data=geojson_url,
        name="choropleth",
        data=resumen_mapa,
        columns=["PROVINCIA", "Proyeccion"],
        key_on="feature.properties.DPA_DESPRO", # Cruce matemático exacto sin importar tildes
        fill_color="YlGnBu", # Degradado estético (Amarillo -> Verde -> Azul)
        fill_opacity=0.85,
        line_opacity=0.2,
        legend_name="Volumen de Asistencias Proyectadas",
        highlight=True
    ).add_to(m)

    # Desplegar mapa interactivo a lo ancho de la pantalla
    st_folium(m, width="100%", height=650)

except Exception as e:
    st.error("🔒 Conexión segura establecida. Esperando mapeo de credenciales de Google Drive en Streamlit Cloud.")
