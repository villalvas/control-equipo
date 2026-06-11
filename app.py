import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px

# 1. Configuración de pantalla ultra ancha para el monitor de control
st.set_page_config(
    layout="wide", 
    page_title="Monitor de Proyecciones - Semana Tipo",
    initial_sidebar_state="collapsed"
)

# Estilos CSS corporativos limpios
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDataFrame [data-testid="stDataFrameDownloadButton"] {display: none;}
    button[title="View fullscreen"] {display: none;}
    </style>
    """, unsafe_allow_html=True)

# Título Principal
st.title("🔮 Monitor de Proyección de Asistencias (Semana Tipo)")
st.caption("Centro de Control Geoanalítico con Enfoque Automático de Región")

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

    # --- PROCESAMIENTO MATEMÁTICO SIN ERRORES DE SANGRÍA ---
    df_dia_especifico = df_raw[df_raw[col_dia] == dia_sel]
    num_fechas_reales = df_dia_especifico[col_fecha].nunique() if col_fecha in df_dia_especifico.columns else 1
    if num_fechas_reales == 0: 
        num_fechas_reales = 1

    df_filtrado = df_dia_especifico.copy()
    
    if servicio_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
        
    if provincia_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado[col_provincia] == provincia_sel]
        
    if estado_sel != "Todos" and col_estado in df_raw.columns:
        df_filtrado = df_filtrado[df_filtrado[col_estado] == estado_sel]

    st.markdown("---")

    # ==========================================
    # 📊 INDICADORES CLAVE (PROMEDIOS REALES)
    # ==========================================
    total_casos_historicos = len(df_filtrado)
    promedio_asistencias_dia = round(total_casos_historicos / num_fechas_reales, 1)
    
    if total_casos_historicos > 0:
        top_servicio = df_filtrado[col_servicio].value_counts().idxmax()
        top_provincia = df_filtrado[col_provincia].value_counts().idxmax() if provincia_sel == "Todas" else provincia_sel
    else:
        top_servicio = "---"
        top_provincia = "---"

    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.metric(label=f"📊 Casos Promedio Esperados (Día {dia_sel})", value=f"{promedio_asistencias_dia} Asistencias")
    with kpi2:
        st.metric(label="🎯 Servicio Mayoritario", value=str(top_servicio)[:22])
    with kpi3:
        st.metric(label="📍 Provincia en Foco", value=str(top_provincia))

    st.markdown("---")

    # ==========================================
    # 🗺️ VISUALIZACIONES EN PANTALLA PARTIDA (50% | 50%)
    # ==========================================
    col_izquierda, col_derecha = st.columns([5, 5])

    # --- LADO IZQUIERDO: EL MAPA CON ENFOQUE AUTOMÁTICO ---
    with col_izquierda:
        st.write(f"### 🗺️ Distribución Geográfica de Demanda ({dia_sel})")
        
        resumen_provincias = df_filtrado.groupby(col_provincia).size().reset_index(name='Total')
        resumen_provincias['Promedio'] = (resumen_provincias['Total'] / num_fechas_reales).round(1)

        coordenadas_provincias = {
            'PICHINCHA': [-0.2298, -78.5249], 'GUAYAS': [-2.1894, -79.8890], 'AZUAY': [-2.9001, -79.0059],
            'MANABI': [-1.0543, -80.4544], 'MANABÍ': [-1.0543, -80.4544], 'EL ORO': [-3.2581, -79.9553], 
            'LOJA': [-3.9931, -79.2042], 'TUNGURAHUA': [-1.2491, -78.6168], 'CHIMBORAZO': [-1.6743, -78.6483], 
            'ESMERALDAS': [0.9682, -79.6517], 'LOS RIOS': [-1.4558, -79.4622], 'LOS RÍOS': [-1.4558, -79.4622],
            'SANTO DOMINGO DE LOS TSÁCHILAS': [-0.2530, -79.1754], 'SANTO DOMINGO DE LOS TSACHILAS': [-0.2530, -79.1754], 
            'SANTA ELENA': [-2.2262, -80.8584], 'IMBABURA': [0.3517, -78.1223], 'COTOPAXI': [-0.9352, -78.6155], 
            'CARCHI': [0.7384, -77.7289], 'SUCUMBIOS': [0.0847, -76.8828], 'SUCUMBÍOS': [0.0847, -76.8828],
            'ORELLANA': [-0.5665, -76.9872], 'NAPO': [-0.9902, -77.8129], 'PASTAZA': [-1.4870, -77.9954], 
            'MORONA SANTIAGO': [-2.3087, -78.1114], 'ZAMORA CHINCHIPE': [-4.0692, -78.9566],
            'GALAPAGOS': [-0.7402, -90.3119], 'GALÁPAGOS': [-0.7402, -90.3119], 'BOLIVAR': [-1.5910, -79.0022], 
            'BOLÍVAR': [-1.5910, -79.0022], 'CAÑAR': [-2.5518, -78.9392]
        }

        # LÓGICA DE COORDENADAS: Vuela y hace zoom dinámico (9) si eliges provincia, o ve Ecuador entero (7)
        lat_inicial, lon_inicial, zoom_inicial = -1.8312, -78.1834, 7
        if provincia_sel != "Todas" and provincia_sel in coordenadas_provincias:
            lat_inicial, lon_inicial = coordenadas_provincias[provincia_sel]
            zoom_inicial = 9 

        m = folium.Map(location=[lat_inicial, lon_inicial], zoom_start=zoom_inicial, tiles="CartoDB dark_matter")

        for idx, row in resumen_provincias.iterrows():
            prov = str(row[col_provincia]).strip()
            prom_prov = float(row['Promedio'])
            
            if prov in coordenadas_provincias and prom_prov > 0:
                radio = min(max(prom_prov * 2.5, 6), 35)
                
                folium.CircleMarker(
                    location=coordenadas_provincias[prov],
                    radius=radio,
                    popup=f"<b>Provincia:</b> {prov}<br><b>Promedio Proyectado:</b> {prom_prov} casos",
                    color="#00FFA6",
                    fill=True,
                    fill_color="#0055FF",
                    fill_opacity=0.65,
                    weight=2
                ).add_to(m)

        # Usar key dinamizado fuerza al mapa a re-centrar la cámara inmediatamente
        st_folium(m, width="100%", height=550, key=f"mapa_control_{
