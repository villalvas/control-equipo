import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px

# 1. Configuración del monitor - Forzamos que la barra lateral permanezca visible
st.set_page_config(
    layout="wide", 
    page_title="Monitor de Proyecciones - Semana Tipo",
    initial_sidebar_state="expanded"
)

# Estilos CSS limpios para pantallas de monitoreo corporativo
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDataFrame [data-testid="stDataFrameDownloadButton"] {display: none;}
    button[title="View fullscreen"] {display: none;}
    /* Asegurar estabilidad visual de la barra lateral */
    [data-testid="stSidebar"] { min-width: 300px; max-width: 350px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 🗂️ MENÚ PRINCIPAL FIJO (BARRA LATERAL)
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
    st.write("Bienvenido al sistema de control de equipo. Selecciona un módulo en la barra lateral.")

# ==========================================
# VISTA: MONITOR DE PROYECCIONES (SEMANA TIPO)
# ==========================================
if st.session_state.modulo_activo == "🔮 Proyecciones":
    st.title("🔮 Monitor de Proyección de Asistencias (Semana Tipo)")
    st.caption("Indicadores Promediados por Día y Hora para Planificación de Turnos")

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

        df_raw[col_provincia] = df_raw[col_provincia].astype(str).str.strip().str.upper()

        # ==========================================
        # INTERFAZ DE FILTROS (SIEMPRE EN LA SIDEBAR)
        # ==========================================
        st.sidebar.header("🎛️ Filtros del Monitor")
        
        # Filtro Obligatorio de Día para calcular la Semana Tipo (Por defecto el primer día disponible)
        dias_disponibles = list(df_raw[col_dia].dropna().unique())
        dia_sel = st.sidebar.selectbox("Seleccionar Día Tipo:", dias_disponibles)
        
        # Filtro Opcional de Servicio
        lista_servicios = ["Todos"] + list(df_raw[col_servicio].dropna().unique())
        servicio_sel = st.sidebar.selectbox("Seleccionar Servicio:", lista_servicios)

        # Filtro Opcional de Estado
        if col_estado in df_raw.columns:
            lista_estados = ["Todos"] + list(df_raw[col_estado].dropna().unique())
            estado_sel = st.sidebar.selectbox("Estado de Asistencia:", lista_estados)
        else:
            estado_sel = "Todos"

        # --- PROCESAMIENTO MATEMÁTICO EN RAM ---
        # 1. Filtramos primero por el Día Tipo seleccionado para saber cuántas fechas reales de ese día existen en la historia
        df_dia_especifico = df_raw[df_raw[col_dia] == dia_sel]
        num_fechas_reales = df_dia_especifico[col_fecha].nunique() if col_fecha in df_dia_especifico.columns else 1
        if num_fechas_reales == 0: num_fechas_reales = 1

        # 2. Aplicamos el resto de filtros secundarios elegidos por el usuario
        df_filtrado = df_dia_especifico.copy()
        if servicio_sel != "Todos":
            df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
        if estado_sel != "Todos" and col_estado in df_raw.columns:
            df_filtrado = df_filtrado[df_filtrado[col_estado] == estado_sel]

        # ==========================================
        # 📊 INDICADORES CLAVE (PROMEDIOS REALES)
        # ==========================================
        total_casos_historicos = len(df_filtrado)
        # División matemática: Casos Totales / Cantidad de días evaluados en la historia
        promedio_asistencias_dia = round(total_casos_historicos / num_fechas_reales, 1)
        
        if total_casos_historicos > 0:
            top_servicio = df_filtrado[col_servicio].value_counts().idxmax()
            top_provincia = df_filtrado[col_provincia].value_counts().idxmax()
        else:
            top_servicio = "---"
            top_provincia = "---"

        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric(label=f"📅 Asistencias Promedio para un día {dia_sel}", value=f"{promedio_asistencias_dia} Casos / Día")
        with kpi2:
            st.metric(label="🎯 Servicio Mayoritario", value=str(top_servicio)[:22])
        with kpi3:
            st.metric(label="📍 Provincia Foco", value=str(top_provincia))

        st.markdown("---")

        # ==========================================
        # 🗺️ VISUALIZACIONES: MAPA Y CARGA HORARIA PROMEDIO
        # ==========================================
        col_izquierda, col_derecha = st.columns([5, 5])

        with col_izquierda:
            st.write(f"### 🗺️ Demanda Promedio Regional ({dia_sel})")
            
            # Agrupación por provincia calculando su respectivo promedio diario real
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

            m = folium.Map(location=[-1.8312, -78.1834], zoom_start=7, tiles="CartoDB dark_matter")

            for idx, row in resumen_provincias.iterrows():
                prov = str(row[col_provincia]).strip()
                prom_prov = float(row['Promedio'])
                
                if prov in coordenadas_provincias and prom_prov > 0:
                    # El tamaño de la burbuja ahora responde al promedio diario esperado
                    radio = min(max(prom_prov * 2.5, 6), 35)
                    
                    folium.CircleMarker(
                        location=coordenadas_provincias[prov],
                        radius=radio,
                        popup=f"<b>Provincia:</b> {prov}<br><b>Promedio Esperado:</b> {prom_prov} casos",
                        color="#00FFA6",
                        fill=True,
                        fill_color="#0055FF",
                        fill_opacity=0.65,
                        weight=2
                    ).add_to(m)

            st_folium(m, width="100%", height=530)

        with col_derecha:
            if total_casos_historicos > 0:
                # Gráfico 1: Carga Promedio por Hora Agrupada para la Semana Tipo
                if col_hora_agrupada in df_filtrado.columns:
                    st.write(f"### ⏰ Casos Promedio Esperados por Hora ({dia_sel})")
                    df_horas = df_filtrado[col_hora_agrupada].value_counts().reset_index()
                    df_horas.columns = [col_hora_agrupada, 'Total_Historico']
                    
                    # Dividimos el volumen de cada hora para obtener su promedio real por bloque horario
                    df_horas['Promedio_Casos'] = (df_horas['Total_Historico'] / num_fechas_reales).round(1)
                    df_horas = df_horas.sort_values(by=col_hora_agrupada)
                    
                    fig_horas = px.bar(
                        df_horas, 
                        x=col_hora_agrupada, 
                        y='Promedio_Casos',
                        text_auto=True,
                        labels={'Promedio_Casos': 'Casos Promedio'},
                        color_discrete_sequence=['#00FFA6']
                    )
                    fig_horas.update_layout(height=240, margin=dict(t=10, b=10, l=10, r=10), xaxis_title="Bloque Horario", yaxis_title=None)
                    st.plotly_chart(fig_horas, use_container_width=True)
                
                # Gráfico 2: Composición Porcentual de Estatus
                if col_estado in df_filtrado.columns:
                    st.write("### 📌 Distribución de Estatus Operativo")
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
                st.info("Sin registros suficientes para calcular los promedios con los filtros actuales.")
    else:
        st.warning("⚠️ Esperando conexión con el archivo de Google Drive...")
