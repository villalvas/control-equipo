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

# Estilos CSS para limpiar el entorno visual del dashboard corporativo
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

    # 2. Método nativo de lectura sincronizada en vivo (GViz)
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

    # Llamado seguro a la base de datos de Serviasistencia
    df_raw = cargar_datos_vía_gviz()

    if df_raw is not None and not df_raw.empty:
        # Limpieza estricta de nombres de columnas (eliminamos espacios y forzamos mayúsculas)
        df_raw.columns = df_raw.columns.str.strip().str.upper()

        # Mapeo idéntico y preciso de tus columnas reales del Drive
        col_provincia = "PROVINCIA"
        col_servicio = "SERVICIO"
        col_dia = "DIA NOMBRE"

        # Formateamos las provincias en mayúsculas limpias para evitar descuadres en el mapa
        df_raw[col_provincia] = df_raw[col_provincia].astype(str).str.strip().str.upper()

        # ==========================================
        # INTERFAZ DE FILTROS EN LA BARRA LATERAL
        # ==========================================
        st.sidebar.header("🎛️ Filtros del Mapa")
        
        # Filtro Dinámico de Servicio
        lista_servicios = ["Todos"] + list(df_raw[col_servicio].dropna().unique())
        servicio_sel = st.sidebar.selectbox("Seleccionar Servicio:", lista_servicios)
        
        # Filtro Dinámico de Día Tipo
        lista_dias = ["Todos"] + list(df_raw[col_dia].dropna().unique())
        dia_sel = st.sidebar.selectbox("Seleccionar Día Tipo:", lista_dias)

        # Aplicación matemática de los filtros en la memoria RAM
        df_filtrado = df_raw.copy()
        if servicio_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
        if dia_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_dia] == dia_sel]

        # Conteo exacto agrupado por Provincias para calcular volúmenes
        resumen_mapa = df_filtrado.groupby(col_provincia).size().reset_index(name='Proyeccion')

        # Diccionario maestro de coordenadas fijas para Ecuador
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

        # ==========================================
        # RENDERIZADO DEL MAPA GEOESTADÍSTICO
        # ==========================================
        m = folium.Map(location=[-1.8312, -78.1834], zoom_start=7, tiles="CartoDB dark_matter")

        # Dibujamos los círculos dinámicos basados en la data real mapeada
        for idx, row in resumen_mapa.iterrows():
            prov = str(row[col_provincia]).strip()
            total = int(row['Proyeccion'])
            
            if prov in coordenadas_provincias:
                # El tamaño del marcador se adapta dinámicamente según la cantidad de casos
                radio = min(max(total * 0.4, 6), 35) 
                
                folium.CircleMarker(
                    location=coordenadas_provincias[prov],
                    radius=radio,
                    popup=f"<b>Provincia:</b> {prov}<br><b>Asistencias Proyectadas:</b> {total}",
                    color="#00FFA6",
                    fill=True,
                    fill_color="#0055FF",
                    fill_opacity=0.7,
                    weight=2
                ).add_to(m)

        # Despliegue interactivo del mapa a lo ancho del monitor
        st_folium(m, width="100%", height=650)
        
    else:
        st.warning("⚠️ Esperando conexión con el archivo de Google Drive. Asegúrate de que el enlace sea de libre acceso.")
