import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import requests
from datetime import datetime

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

st.title("🔮 Monitor de Proyección y Alerta Temprana Operativa")
st.caption("Centro de Control Geoanalítico con Monitoreo de Clima Online en Tiempo Real")

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

# 🚀 CONSULTA DE CLIMA EN VIVO DESDE LA API ONLINE
@st.cache_data(ttl=300)
def obtener_clima_horario(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,weathercode&timezone=auto&forecast_days=1"
        respuesta = requests.get(url).json()
        horas_raw = respuesta['hourly']['time']
        temperaturas = respuesta['hourly']['temperature_2m']
        codigos_clima = respuesta['hourly']['weathercode']
        
        datos_clima = {}
        for h, temp, codigo in zip(horas_raw, temperaturas, codigos_clima):
            hora_int = int(h.split("T")[1].split(":")[0])
            if codigo == 0: estado, icono = "Despejado", "☀️"
            elif codigo in [1, 2, 3]: estado, icono = "Nublado", "☁️"
            elif codigo in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99]: estado, icono = "Lluvia", "🌧️"
            else: estado, icono = "Nublado", "☁️"
            datos_clima[hora_int] = {"Detalle": f"{icono} {estado} ({temp}°C)", "Icono": icono, "Estado": estado}
        return datos_clima
    except:
        return {i: {"Detalle": "⚪ Sin Conexión", "Icono": "⚪", "Estado": "Normal"} for i in range(24)}

# 🚀 CÁLCULO CIENTÍFICO DEL MULTIPLICADOR HISTÓRICO
@st.cache_data(ttl=3600)
def calcular_factor_lluvia_en_vivo(df_historico, lat, lon):
    try:
        df_quick = df_historico.dropna(subset=["FECHA CREACIÓN DE ASISTENCIA", "HORA CREACIÓN DE ASISTENCIA"]).tail(60)
        if df_quick.empty:
            return 1.35
        
        fechas_unicas = df_quick["FECHA CREACIÓN DE ASISTENCIA"].astype(str).str.split().str[0].unique()
        lluvias_detectadas = 0
        total_evaluado = 0
        
        for fecha in fechas_unicas[:4]:
            url_historial = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={fecha}&end_date={fecha}&hourly=weathercode&timezone=auto"
            res = requests.get(url_historial).json()
            if 'hourly' in res:
                codigos = res['hourly']['weathercode']
                lluvias_detectadas += sum(1 for c in codigos if c in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99])
                total_evaluado += len(codigos)
        
        if total_evaluado > 0 and lluvias_detectadas > 0:
            ratio = lluvias_detectadas / total_evaluado
            return round(1.2 + (ratio * 1.5), 2)
        return 1.35
    except:
        return 1.35

@st.cache_data(ttl=60)
def cargar_datos_vía_gviz():
    try:
        url_base = "https://docs.google.com/spreadsheets/d/1UWQy9XJy8UOdef1IcXWDt2Nmn7hTnsQLHby_3BhpJnc/edit"
        pestana = "Consolidado"
        csv_url = url_base.replace('/edit', f'/gviz/tq?tqx=out:csv&sheet={pestana}')
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        st.error(f"❌ Error al conectar con Google Drive: {e}")
        return None

df_raw = cargar_datos_vía_gviz()

if df_raw is not None and not df_raw.empty:
    df_raw.columns = df_raw.columns.str.strip().str.upper()

    col_provincia = "PROVINCIA"
    col_ciudad = "CIUDAD" if "CIUDAD" in df_raw.columns else ("CANTON" if "CANTON" in df_raw.columns else "CANTÓN")
    col_servicio = "SERVICIO"
    col_dia = "DIA NOMBRE"
    col_estado = "ESTADO DE ASISTENCIA"
    col_hora_agrupada = "HORA AGRUPADA"
    col_fecha = "FECHA CREACIÓN DE ASISTENCIA" if "FECHA CREACIÓN DE ASISTENCIA" in df_raw.columns else "FECHA CREACION DE ASISTENCIA"

    df_raw[col_provincia] = df_raw[col_provincia].astype(str).str.strip().str.upper()

    # Panel de Filtros
    st.write("### 🎛️ Panel de Filtros de Operación")
    f1, f2, f3, f4 = st.columns(4)
    
    with f1:
        dias_en_orden = ["LUNES", "MARTES", "MIÉRCOLES", "MIERCOLES", "JUEVES", "VIERNES", "SÁBADO", "SABADO", "DOMINGO"]
        dias_existentes = df_raw[col_dia].dropna().unique()
        dias_disponibles = [d for d in dias_en_orden if d in list(df_raw[col_dia].str.upper().unique())]
        extras = [d for d in dias_existentes if d.upper() not in dias_en_orden]
        dia_sel = st.selectbox("📅 Seleccionar Día Tipo:", dias_disponibles + extras)
    
    with f2:
        lista_servicios = ["Todos"] + list(df_raw[col_servicio].dropna().unique())
        servicio_sel = st.selectbox("🎯 Seleccionar Servicio:", lista_servicios)

    with f3:
        lista_provincias = ["Todas"] + df_raw[col_provincia].value_counts().index.tolist()
        provincia_sel = st.selectbox("📍 Seleccionar Provincia:", lista_provincias)

    with f4:
        estado_sel = st.selectbox("📌 Filtrar por Estado:", ["Todos"] + list(df_raw[col_estado].dropna().unique())) if col_estado in df_raw.columns else "Todos"

    # Procesamiento
    df_dia_especifico = df_raw[df_raw[col_dia].str.upper() == dia_sel.upper()]
    num_fechas_reales = df_dia_especifico[col_fecha].nunique() if col_fecha in df_dia_especifico.columns else 1
    if num_fechas_reales == 0: num_fechas_reales = 1

    df_base_dia_estado = df_dia_especifico.copy()
    if estado_sel != "Todos" and col_estado in df_raw.columns:
        df_base_dia_estado = df_base_dia_estado[df_base_dia_estado[col_estado] == estado_sel]

    df_base_filtros = df_base_dia_estado.copy()
    if servicio_sel != "Todos":
        df_base_filtros = df_base_filtros[df_base_filtros[col_servicio] == servicio_sel]

    df_filtrado = df_base_filtros.copy()
    if provincia_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado[col_provincia] == provincia_sel]

    # Lógica de Clima condicionada al Filtro de Provincia
    if provincia_sel != "Todas":
        lat_c, lon_c = coordenadas_provincias.get(provincia_sel, [-0.2298, -78.5249])
        diccionario_clima = obtener_clima_horario(lat_c, lon_c)
        factor_ajuste = calcular_factor_lluvia_en_vivo(df_filtrado, lat_c, lon_c)
    else:
        diccionario_clima = {}
        factor_ajuste = 1.0

    st.markdown("---")

    total_casos_historicos = len(df_filtrado)
    promedio_asistencias_dia = round(total_casos_historicos / num_fechas_reales, 1)
    st.metric(label=f"📊 Casos Promedio Esperados (Día {dia_sel})", value=f"{promedio_asistencias_dia} Asistencias")

    st.markdown("---")
    col_tabla_izq, col_tabla_der = st.columns([5, 5])

    with col_tabla_izq:
        if total_casos_historicos > 0:
            if provincia_sel == "Todas":
                st.write("### 📋 Demanda General por Provincias")
                df_tabla_prov = df_base_filtros.groupby(col_provincia).size().reset_index(name='Casos Históricos')
                df_tabla_prov['Promedio Diario Proyectado'] = (df_tabla_prov['Casos Históricos'] / num_fechas_reales).round(1)
                st.dataframe(df_tabla_prov.sort_values(by='Casos Históricos', ascending=False), use_container_width=True, hide_index=True)
            else:
                st.write(f"### 📋 Demanda: Ciudades de {provincia_sel}")
                if col_ciudad in df_filtrado.columns:
                    df_tabla_ciud = df_filtrado.groupby(col_ciudad).size().reset_index(name='Casos Históricos')
                    df_tabla_ciud['Promedio Diario Proyectado'] = (df_tabla_ciud['Casos Históricos'] / num_fechas_reales).round(1)
                    st.dataframe(df_tabla_ciud.sort_values(by='Casos Históricos', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("Sin registros para estructurar la tabla geográfica.")

    with col_tabla_der:
        if total_casos_historicos > 0:
            if servicio_sel == "Todos":
                st.write("### 📋 Ranking de Servicios con Mayor Demanda")
                df_origen_servicios = df_base_dia_estado[df_base_dia_estado[col_provincia] == provincia_sel] if provincia_sel != "Todas" else df_base_dia_estado
                df_tabla_serv = df_origen_servicios.groupby(col_servicio).size().reset_index(name='Casos Históricos')
                df_tabla_serv['Promedio Diario Proyectado'] = (df_tabla_serv['Casos Históricos'] / num_fechas_reales).round(1)
                st.dataframe(df_tabla_serv.sort_values(by='Casos Históricos', ascending=False), use_container_width=True, hide_index=True)
            else:
                st.write("### ⏰ Casos Promedio vs. Estado del Clima Online")
                if col_hora_agrupada in df_filtrado.columns:
                    df_tabla_horas = df_filtrado.groupby(col_hora_agrupada).size().reset_index(name='Casos Históricos')
                    df_tabla_horas['Promedio Base'] = (df_tabla_horas['Casos Históricos'] / num_fechas_reales).round(1)
                    
                    df_tabla_horas[col_hora_agrupada] = pd.to_numeric(df_tabla_horas[col_hora_agrupada], errors='coerce')
                    df_tabla_horas = df_tabla_horas.dropna(subset=[col_hora_agrupada]).sort_values(by=col_hora_agrupada, ascending=True)
                    df_tabla_horas[col_hora_agrupada] = df_tabla_horas[col_hora_agrupada].astype(int)
                    
                    # 🚀 ASIGNACIÓN DE CLIMA CONDICIONADA
                    if provincia_sel != "Todas":
                        df_tabla_horas['🌤️ Clima Online'] = df_tabla_horas[col_hora_agrupada].map(lambda x: diccionario_clima.get(x, {"Detalle": "⚪ N/A"})["Detalle"])
                    else:
                        df_tabla_horas['🌤️ Clima Online'] = "🌍 Nacional (Filtre Provincia)"
                    
                    valores_corregidos = []
                    hora_actual = datetime.now().hour
                    alertas_activas = []
                    
                    for idx, row in df_tabla_horas.iterrows():
                        hr = row[col_hora_agrupada]
                        base = row['Promedio Base']
                        
                        # Si hay provincia seleccionada, evaluamos alertas climáticas
                        if provincia_sel != "Todas":
                            estado_c = diccionario_clima.get(hr, {"Estado": "Normal"})["Estado"]
                            if estado_c == "Lluvia":
                                nuevo_promedio = round(base * factor_ajuste, 1)
                                valores_corregidos.append(f"🔥 {nuevo_promedio} (Alerta)")
                                if hr > hora_actual and hr <= (hora_actual + 3):
                                    alertas_activas.append(f"🚨 **Alerta de Impacto por Clima Actual [{hr}:00]:** El reporte online detecta Lluvia entrante en {provincia_sel}. Históricamente la demanda sube a **{nuevo_promedio} casos** ($\times{factor_ajuste}$).")
                            else:
                                valores_corregidos.append(f"{base} (Normal)")
                        else:
                            # Si está en "Todas", la proyección ajustada es simplemente la base normal
                            valores_corregidos.append(f"{base} (Normal)")
                    
                    df_tabla_horas['Proyección Ajustada'] = valores_corregidos
                    
                    if provincia_sel != "Todas":
                        if alertas_activas:
                            for alerta in alertas_activas: st.error(alerta)
                        else:
                            st.success(f"✅ Reporte Online: Clima estable para las próximas horas en {provincia_sel}. Sin alertas meteorológicas.")
                    else:
                        st.info("ℹ️ Para activar el análisis de impacto meteorológico en vivo y alertas tempranas, por favor selecciona una Provincia en el panel superior.")
                    
                    df_tabla_horas.rename(columns={col_hora_agrupada: "BLOQUE HORARIO"}, inplace=True)
                    st.dataframe(df_tabla_horas[['BLOQUE HORARIO', '🌤️ Clima Online', 'Promedio Base', 'Proyección Ajustada']], use_container_width=True, hide_index=True)
                else:
                    st.info("No se localizó la columna de Bloques Horarios en la fuente de datos.")
        else:
            st.info("Sin registros para estructurar el análisis analítico derecho.")

    st.markdown("---")

    # ==========================================
    # 🗺️ SECCIÓN INFERIOR: MAPA DE CONTROL
    # ==========================================
    st.write(f"### 🗺️ Distribución Geográfica de Demanda ({dia_sel})")
    resumen_provincias = df_filtrado.groupby(col_provincia).size().reset_index(name='Total')
    resumen_provincias['Promedio'] = (resumen_provincias['Total'] / num_fechas_reales).round(1)

    lat_inicial, lon_inicial, zoom_inicial = -1.8312, -78.1834, 7
    if provincia_sel != "Todas" and provincia_sel in coordenadas_provincias:
        lat_inicial, lon_inicial = coordenadas_provincias[provincia_sel]
        zoom_inicial = 9 

    m = folium.Map(location=[lat_inicial, lon_inicial], zoom_start=zoom_inicial, tiles="CartoDB dark_matter")

    for idx, row in resumen_provincias.iterrows():
        prov = str(row[col_provincia]).strip()
        prom_prov = float(row['Promedio'])
        if prov in coordenadas_provincias and prom_prov > 0:
            folium.CircleMarker(
                location=coordenadas_provincias[prov],
                radius=min(max(prom_prov * 2.5, 6), 35),
                popup=f"<b>Provincia:</b> {prov}<br><b>Promedio Proyectado:</b> {prom_prov} casos",
                color="#00FFA6", fill=True, fill_color="#0055FF", fill_opacity=0.65, weight=2
            ).add_to(m)

    st_folium(m, width="100%", height=500, key=f"mapa_control_{provincia_sel}")
else:
    st.warning("⚠️ Esperando conexión con el archivo de Google Drive...")
