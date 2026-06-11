import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px

# 1. Configuración de pantalla completa del monitor estilo Centro de Comando
st.set_page_config(
    layout="wide", 
    page_title="Monitor de Proyecciones - Semana Tipo",
    initial_sidebar_state="expanded"
)

# Estilos CSS para limpiar el entorno visual del dashboard corporativo (ideal para pantallas)
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
    st.caption("Centro de Analítica Geoestadística Sincronizado en Vivo")

    # Método nativo de lectura sincronizada en vivo (GViz)
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
        # Limpieza estándar de nombres de columnas a MAYÚSCULAS
        df_raw.columns = df_raw.columns.str.strip().str.upper()

        # Mapeo exacto de los nombres de tus campos
        col_provincia = "PROVINCIA"
        col_servicio = "SERVICIO"
        col_dia = "DIA NOMBRE"
        col_estado = "ESTADO DE ASISTENCIA"
        col_hora_agrupada = "HORA AGRUPADA"
        col_vehiculo = "TIPO DE VEHÍCULO" if "TIPO DE VEHÍCULO" in df_raw.columns else "TIPO DE VEHICULO"
        col_ciudad = "CIUDAD"

        # Formateamos texto para evitar duplicados por minúsculas o espacios
        df_raw[col_provincia] = df_raw[col_provincia].astype(str).str.strip().str.upper()
        if col_estado in df_raw.columns:
            df_raw[col_estado] = df_raw[col_estado].astype(str).str.strip()

        # ==========================================
        # INTERFAZ DE FILTROS EN LA BARRA LATERAL
        # ==========================================
        st.sidebar.header("🎛️ Filtros del Monitor")
        
        # Filtro 1: Servicio
        lista_servicios = ["Todos"] + list(df_raw[col_servicio].dropna().unique())
        servicio_sel = st.sidebar.selectbox("Seleccionar Servicio:", lista_servicios)
        
        # Filtro 2: Día Nombre
        lista_dias = ["Todos"] + list(df_raw[col_dia].dropna().unique())
        dia_sel = st.sidebar.selectbox("Seleccionar Día Tipo:", lista_dias)

        # Filtro 3: Estado de Asistencia
        if col_estado in df_raw.columns:
            lista_estados = ["Todos"] + list(df_raw[col_estado].dropna().unique())
            estado_sel = st.sidebar.selectbox("Estado de Asistencia:", lista_estados)
        else:
            estado_sel = "Todos"

        # Filtro 4: Tipo de Vehículo
        if col_vehiculo in df_raw.columns:
            lista_vehiculos = ["Todos"] + list(df_raw[col_vehiculo].dropna().unique())
            vehiculo_sel = st.sidebar.selectbox("Tipo de Vehículo:", lista_vehiculos)
        else:
            vehiculo_sel = "Todos"

        # Aplicación estricta de filtros en cascada (RAM)
        df_filtrado = df_raw.copy()
        if servicio_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
        if dia_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_dia] == dia_sel]
        if estado_sel != "Todos" and col_estado in df_raw.columns:
            df_filtrado = df_filtrado[df_filtrado[col_estado] == estado_sel]
        if vehiculo_sel != "Todos" and col_vehiculo in df_raw.columns:
            df_filtrado = df_filtrado[df_filtrado[col_vehiculo] == vehiculo_sel]

        # ==========================================
        # 📊 INDICADORES CLAVE (KPI CARDS)
        # ==========================================
        total_casos = len(df_filtrado)
        
        if total_casos > 0:
            top_servicio = df_filtrado[col_servicio].value_counts().idxmax()
            top_provincia = df_filtrado[col_provincia].value_counts().idxmax()
        else:
            top_servicio = "---"
            top_provincia = "---"

        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric(label="📊 Volumen de Asistencias", value=f"{total_casos} Casos")
        with kpi2:
            st.metric(label="🎯 Servicio Mayoritario", value=str(top_servicio)[:22])
        with kpi3:
            st.metric(label="📍 Provincia Foco", value=str(top_provincia))

        st.markdown("---")

        # ==========================================
        # 🗺️ MAQUETACIÓN: MAPA (50%) | GRÁFICOS (50%)
        # ==========================================
        col_izquierda, col_derecha = st.columns([5, 5])

        # --- SECCIÓN IZQUIERDA: EL MAPA ---
        with col_izquierda:
            st.write("### 🗺️ Distribución Geográfica de Demanda")
            
            resumen_mapa = df_filtrado.groupby(col_provincia).size().reset_index(name='Proyeccion')

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

            m = folium.Map(location=[-1.8312, -78.1834], zoom_start=7, tiles="CartoDB dark_matter")

            for idx, row in resumen_mapa.iterrows():
                prov = str(row[col_provincia]).strip()
                total = int(row['Proyeccion'])
                
                if prov in coordenadas_provincias:
                    # Cálculo logarítmico adaptativo para que las burbujas luzcan equilibradas en pantalla
                    radio = min(max(total * 0.4, 6), 35) 
                    
                    folium.CircleMarker(
                        location=coordenadas_provincias[prov],
                        radius=radio,
                        popup=f"<b>Provincia:</b> {prov}<br><b>Casos:</b> {total}",
                        color="#00FFA6",
                        fill=True,
                        fill_color="#0055FF",
                        fill_opacity=0.65,
                        weight=2
                    ).add_to(m)

            st_folium(m, width="100%", height=530)

        # --- SECCIÓN DERECHA: LOS GRÁFICOS COMPLEMENTARIOS ---
        with col_derecha:
            if total_casos > 0:
                # Gráfico 1: Análisis de Comportamiento Horario (Hora Agrupada)
                if col_hora_agrupada in df_filtrado.columns:
                    st.write("### ⏰ Curva de Carga Horaria")
                    df_horas = df_filtrado[col_hora_agrupada].value_counts().reset_index()
                    df_horas.columns = [col_hora_agrupada, 'Casos']
                    df_horas = df_horas.sort_values(by=col_hora_agrupada) # Orden cronológico de horas
                    
                    fig_horas = px.bar(
                        df_horas, 
                        x=col_hora_agrupada, 
                        y='Casos',
                        text_auto=True,
                        color_discrete_sequence=['#00FFA6']
                    )
                    fig_horas.update_layout(height=240, margin=dict(t=10, b=10, l=10, r=10), xaxis_title=None, yaxis_title=None)
                    st.plotly_chart(fig_horas, use_container_width=True)
                
                # Gráfico 2: Composición por Estado de Asistencia
                if col_estado in df_filtrado.columns:
                    st.write("### 📌 Estatus de Casos")
                    df_status = df_filtrado[col_estado].value_counts().reset_index()
                    df_status.columns = [col_estado, 'Cantidad']
                    
                    fig_status = px.pie(
                        df_status, 
                        names=col_estado, 
                        values='Cantidad',
                        hole=0.4,
                        color_discrete_sequence=px.colors.sequential.YlGnBu_r
                    )
                    fig_status.update_layout(height=230, margin=dict(t=10, b=10, l=10, r=10), showlegend=True)
                    st.plotly_chart(fig_status, use_container_width=True)
            else:
                st.info("Sin registros para desplegar gráficos operacionales con los filtros seleccionados.")
                
    else:
        st.warning("⚠️ Esperando conexión con el archivo de Google Drive. Asegúrate de que el enlace sea de libre acceso.")
