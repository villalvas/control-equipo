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
st.caption("Centro de Control Geoanalítico con Desglose Dinámico de Demanda")

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
    col_ciudad = "CIUDAD" if "CIUDAD" in df_raw.columns else ("CANTON" if "CANTON" in df_raw.columns else "CANTÓN")
    col_servicio = "SERVICIO"
    col_dia = "DIA NOMBRE"
    col_estado = "ESTADO DE ASISTENCIA"
    col_hora_agrupada = "HORA AGRUPADA"
    col_fecha = "FECHA CREACIÓN DE ASISTENCIA" if "FECHA CREACIÓN DE ASISTENCIA" in df_raw.columns else "FECHA CREACION DE ASISTENCIA"

    # Estandarizamos texto de provincias y ciudades
    df_raw[col_provincia] = df_raw[col_provincia].astype(str).str.strip().str.upper()
    if col_ciudad in df_raw.columns:
        df_raw[col_ciudad] = df_raw[col_ciudad].astype(str).str.strip().str.upper()

    # ==========================================
    # 🎛️ PANEL DE FILTROS EN LA PANTALLA PRINCIPAL
    # ==========================================
    st.write("### 🎛️ Panel de Filtros de Operación")
    f1, f2, f3, f4 = st.columns(4)
    
    with f1:
        dias_en_orden = ["LUNES", "MARTES", "MIÉRCOLES", "MIERCOLES", "JUEVES", "VIERNES", "SÁBADO", "SABADO", "DOMINGO"]
        dias_existentes = df_raw[col_dia].dropna().unique()
        dias_disponibles = [d for d in dias_en_orden if d in list(df_raw[col_dia].str.upper().unique())]
        extras = [d for d in dias_existentes if d.upper() not in dias_en_orden]
        dias_finales = dias_disponibles + extras
        
        dia_sel = st.selectbox("📅 Seleccionar Día Tipo:", dias_finales)
    
    with f2:
        lista_servicios = ["Todos"] + list(df_raw[col_servicio].dropna().unique())
        servicio_sel = st.selectbox("🎯 Seleccionar Servicio:", lista_servicios)

    with f3:
        ranking_provincias = df_raw[col_provincia].value_counts().index.tolist()
        lista_provincias = ["Todas"] + ranking_provincias
        provincia_sel = st.selectbox("📍 Seleccionar Provincia:", lista_provincias)

    with f4:
        if col_estado in df_raw.columns:
            lista_estados = ["Todos"] + list(df_raw[col_estado].dropna().unique())
            estado_sel = st.selectbox("📌 Filtrar por Estado:", lista_estados)
        else:
            estado_sel = "Todos"

    # --- PROCESAMIENTO MATEMÁTICO ---
    df_dia_especifico = df_raw[df_raw[col_dia].str.upper() == dia_sel.upper()]
    num_fechas_reales = df_dia_especifico[col_fecha].nunique() if col_fecha in df_dia_especifico.columns else 1
    if num_fechas_reales == 0: 
        num_fechas_reales = 1

    df_base_filtros = df_dia_especifico.copy()
    if servicio_sel != "Todos":
        df_base_filtros = df_base_filtros[df_base_filtros[col_servicio] == servicio_sel]
    if estado_sel != "Todos" and col_estado in df_raw.columns:
        df_base_filtros = df_base_filtros[df_base_filtros[col_estado] == estado_sel]

    df_filtrado = df_base_filtros.copy()
    if provincia_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado[col_provincia] == provincia_sel]

    st.markdown("---")

    # ==========================================
    # 📊 INDICADOR ÚNICO (PROMEDIO)
    # ==========================================
    total_casos_historicos = len(df_filtrado)
    promedio_asistencias_dia = round(total_casos_historicos / num_fechas_reales, 1)
    
    st.metric(label=f"📊 Casos Promedio Esperados (Día {dia_sel})", value=f"{promedio_asistencias_dia} Asistencias")

    # ==========================================
    # 📋 SECCIÓN DE TABLAS EN PARALELO (50% | 50%)
    # ==========================================
    st.markdown("---")
    col_tabla_izq, col_tabla_der = st.columns([5, 5])

    with col_tabla_izq:
        if total_casos_historicos > 0:
            if provincia_sel == "Todas":
                st.write("### 📋 Demanda General por Provincias")
                df_tabla = df_base_filtros.groupby(col_provincia).size().reset_index(name='Casos Históricos')
                df_tabla['Promedio Diario Proyectado'] = (df_tabla['Casos Históricos'] / num_fechas_reales).round(1)
                df_tabla = df_tabla.sort_values(by='Casos Históricos', ascending=False)
                st.dataframe(df_tabla, use_container_width=True, hide_index=True)
            else:
                st.write(f"### 📋 Demanda: Ciudades de {provincia_sel}")
                if col_ciudad in df_filtrado.columns:
                    df_tabla = df_filtrado.groupby(col_ciudad).size().reset_index(name='Casos Históricos')
                    df_tabla['Promedio Diario Proyectado'] = (df_tabla['Casos Históricos'] / num_fechas_reales).round(1)
                    df_tabla = df_tabla.sort_values(by='Casos Históricos', ascending=False)
                    st.dataframe(df_tabla, use_container_width=True, hide_index=True)
                else:
                    st.info("No se encontró la columna de Ciudades en la base de datos.")
        else:
            st.info("Sin registros para estructurar la tabla.")

    with col_tabla_der:
        st.write("### 📋 Próxima Tabla Adicional (Espacio Libre)")
        # Dejamos este contenedor al 50% listo para el siguiente requerimiento que necesites agregar al lado
        st.info("Espacio reservado al 50% para la nueva tabla de control.")

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

        st_folium(m, width="100%", height=550, key=f"mapa_control_{provincia_sel}")

    # --- LADO DERECHO: CURVA HORARIA TIPO ---
    with col_derecha:
        if total_casos_historicos > 0:
            if col_hora_agrupada in df_filtrado.columns:
                st.write(f"### ⏰ Casos Promedio Esperados por Hora ({dia_sel})")
                df_horas = df_filtrado[col_hora_agrupada].value_counts().reset_index()
                df_horas.columns = [col_hora_agrupada, 'Total_Historico']
                
                df_horas['Promedio_Casos'] = (df_horas['Total_Historico'] / num_fechas_reales).round(1)
                df_horas = df_horas.sort_values(by=col_hora_agrupada)
                
                fig_horas = px.bar(
                    df_horas, 
                    x=col_hora_agrupada, 
                    y='Promedio_Casos',
                    text_auto=True,
                    labels={'Promedio_Casos': 'Asistencias Promedio'},
                    color_discrete_sequence=['#00FFA6']
                )
                
                # 🚀 FORZAR PLOTLY A MOSTRAR ABSOLUTAMENTE TODAS LAS HORAS (dtick=1 y type="category")
                fig_horas.update_xaxes(type="category", tickmode="linear")
                
                fig_horas.update_layout(
                    height=550, 
                    margin=dict(t=10, b=10, l=10, r=10), 
                    xaxis_title="Bloque Horario", 
                    yaxis_title=None
                )
                st.plotly_chart(fig_horas, use_container_width=True)
        else:
            st.info("Sin registros suficientes para calcular la curva horaria con la combinación de filtros actual.")
else:
    st.warning("⚠️ Esperando conexión con el archivo de Google Drive...")
