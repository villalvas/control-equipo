import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px

# 1. Configuración de pantalla ultra ancha para el monitor de control
st.set_page_config(
    layout="wide", 
    page_title="Monitor de Proyecciones - Semana Tipo",
    initial_sidebar_state="collapsed" # Mantenemos oculta la barra lateral problemática
)

# Estilos CSS limpios para monitor de oficina
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDataFrame [data-testid="stDataFrameDownloadButton"] {display: none;}
    button[title="View fullscreen"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

# Título del Monitor Principal
st.title("🔮 Monitor de Proyección de Asistencias (Semana Tipo)")
st.caption("Centro de Control Geoanalítico con Enfoque Dinámico de Región")

# Conexión optimizada por GViz
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

df_raw = cargar_datos_vía_gviz()

if df_raw is not None and not df_raw.empty:
    # Limpieza estándar de nombres de columnas
    df_raw.columns = df_raw.columns.str.strip().str.upper()

    # Mapeo de columnas esenciales de tu Drive
    col_provincia = "PROVINCIA"
    col_servicio = "SERVICIO"
    col_dia = "DIA NOMBRE"
    col_estado = "ESTADO DE ASISTENCIA"
    col_hora_agrupada = "HORA AGRUPADA"
    col_fecha = "FECHA CREACIÓN DE ASISTENCIA" if "FECHA CREACIÓN DE ASISTENCIA" in df_raw.columns else "FECHA CREACION DE ASISTENCIA"

    # Estandarizamos texto de provincias
    df_raw[col_provincia] = df_raw[col_provincia].astype(str).str.strip().str.upper()

    # ==========================================
    # 🎛️ PANEL DE FILTROS EN LA PANTALLA PRINCIPAL
    # ==========================================
    st.write("### 🎛️ Panel de Filtros de Operación")
    f1, f2, f3, f4 = st.columns(4)
    
    with f1:
        dias_disponibles = list(df_raw[col_dia].dropna().unique())
        dia_sel = st.selectbox("📅 Seleccionar Día Tipo:", dias_disponibles)
    
    with f2:
        lista_servicios = ["Todos"] + list(df_raw[col_servicio].dropna().unique())
        servicio_sel = st.selectbox("🎯 Seleccionar Servicio:", lista_servicios)

    with f3:
        lista_provincias = ["Todas"] + sorted(list(df_raw[col_provincia].dropna().unique()))
        provincia_sel = st.selectbox("📍 Seleccionar Provincia:", lista_provincias)

    with f4:
        if col_estado in df_raw.columns:
            lista_estados = ["Todos"] + list(df_raw[col_estado].dropna().unique())
            estado_sel = st.selectbox("📌 Filtrar por Estado:", lista_estados)
        else:
            estado_sel = "Todos"

    # --- PROCESAMIENTO MATEMÁTICO EN RAM ---
    df_dia_especifico = df_raw[df_raw[col_dia] == dia_sel]
    num_fechas_reales = df_dia_especifico[col_fecha].nunique() if col_fecha in df_dia_especifico.columns else 1
    if num_fechas_reales == 0: num_fechas_reales = 1

    df_filtrado = df_dia_especifico.copy()
    if servicio_sel != "Todos":
