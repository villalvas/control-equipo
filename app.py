import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time
import math

# 1. Configuración de pantalla ultra ancha para el monitor de control
st.set_page_config(
    layout="wide", 
    page_title="Monitor de Proyecciones 2026 - Control de Flota",
    initial_sidebar_state="collapsed"
)

# Estilos CSS corporativos y tamaño de letra optimizado para pantallas de control
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDataFrame [data-testid="stDataFrameDownloadButton"] {display: none;}
    button[title="View fullscreen"] {display: none;}
    
    /* 🚀 Tamaño de texto optimizado en celdas y encabezados */
    [data-testid="stTable"] td, [data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] [role="gridcell"] {
        font-size: 16px !important;
        font-weight: 500 !important;
    }
    [data-testid="stTable"] th, [data-testid="stDataFrame"] th, div[data-testid="stDataFrame"] [role="columnheader"] {
        font-size: 17px !important;
        font-weight: bold !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Definimos la zona horaria de Ecuador de forma explícita
zona_ecuador = ZoneInfo("America/Guayaquil")
hora_ecuador_actual = datetime.now(zona_ecuador)
fecha_hoy_str = hora_ecuador_actual.strftime("%Y-%m-%d")

# Coordenadas maestras para el radar nacional de Waze
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

# 🧠 CONTROL DE ESTADOS DE MEMORIA CON RESET DIARIO AUTOMÁTICO
if "fecha_ultimo_control" not in st.session_state:
    st.session_state.fecha_ultimo_control = fecha_hoy_str

if "historial_alertas" not in st.session_state:
    st.session_state.historial_alertas = []

# 🚨 PURGA AL CAMBIO DE DÍA: Si cambió la fecha del servidor, reseteamos el historial a cero
if st.session_state.fecha_ultimo_control != fecha_hoy_str:
    st.session_state.historial_alertas = []
    st.session_state.fecha_ultimo_control = fecha_hoy_str

# 🚀 LECTOR DE WAZE MEJORADO PARA ESCANEO PROVINCIAL O COMPLETO
def obtener_alertas_waze_real(lat, lon, prov_nombre=""):
    delta_lat = 0.18
    delta_lon = 0.18
    
    params = {
        "top": str(lat + delta_lat),
        "bottom": str(lat - delta_lat),
        "left": str(lon - delta_lon),
        "right": str(lon + delta_lon),
        "env": "row",
        "types": "alerts,traffic"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://www.waze.com/live-map/"
    }
    url = "https://www.waze.com/live-map/api/georss"
    
    try:
        respuesta = requests.get(url, params=params, headers=headers, timeout=5)
        if respuesta.status_code == 200:
            datos = respuesta.json()
            alertas_raw = datos.get("alerts", [])
            
            if not alertas_raw:
                return [True, []]
            
            alertas_procesadas = []
            for alert in alertas_raw:
                tipo = alert.get("type", "HAZARD")
                subtipo = alert.get("subtype", "")
                calle = alert.get("street", "Vía no identificada")
                ciudad = alert.get("city", prov_nombre.title())
                uuid = alert.get("uuid", "")
                
                if tipo == "ACCIDENT":
                    icono, titulo, es_critico = "🚨", f"Accidente Vial ({subtipo.replace('_', ' ').title()})", True
                elif tipo == "ROAD_CLOSED":
                    icono, titulo, es_critico = "🚧", "Vía Cerrada / Bloqueo", True
                elif tipo == "JAM":
                    icono, titulo, es_critico = "🚗", "Tráfico Pesado / Congestión", False
                else:
                    icono, titulo, es_critico = "⚠️", "Peligro en Calzada", False
                
                ubicacion_str = f"{calle} ({ciudad if ciudad else prov_nombre.title()})"
                msg_completo = f"{icono} **[{prov_nombre.upper()}] {titulo}:** En {ubicacion_str}."
                
                alertas_procesadas.append({
                    "mensaje": msg_completo,
                    "critico": es_critico,
                    "provincia": prov_nombre.upper(),
                    "uuid": uuid
                })
            return [False, alertas_procesadas]
        return [True, []]
    except:
        return [True, []]

# 🚀 ESCANEO RADAR MULTI-PROVINCIA (Alimenta el Banner + Historial con límite de 6 horas)
def ejecutar_radar_nacional():
    provincias_clave = ['PICHINCHA', 'GUAYAS', 'AZUAY', 'MANABI', 'TUNGURAHUA', 'LOS RIOS', 'SANTO DOMINGO DE LOS TSACHILAS']
    alertas_totales_criticas = []
    ahora_dt = datetime.now(zona_ecuador)
    
    for prov in provincias_clave:
        if prov in coordenadas_provincias:
            lat, lon = coordenadas_provincias[prov]
            _, alertas = obtener_alertas_waze_real(lat, lon, prov)
            
            for a in alertas:
                if a["critico"]:
                    alertas_totales_criticas.append(a)
                    # Insertar en el historial global si no existe previamente por su UUID
                    existe = any(h["uuid"] == a["uuid"] for h in st.session_state.historial_alertas)
                    if not existe:
                        st.session_state.historial_alertas.insert(0, {
                            "timestamp_captura": ahora_dt,
                            "hora_str": ahora_dt.strftime("%I:%M:%S %p"),
                            "mensaje": a["mensaje"],
                            "uuid": a["uuid"]
                        })
    
    # ⏱️ FILTRO DE SEGURIDAD MÓVIL: Remover registros cuya captura exceda las 6 horas de antigüedad
    limite_tiempo = ahora_dt - timedelta(hours=6)
    st.session_state.historial_alertas = [
        h for h in st.session_state.historial_alertas 
        if h["timestamp_captura"] >= limite_tiempo
    ]
        
    return alertas_totales_criticas

# --- EJECUCIÓN DEL RADAR GENERAL ---
alertas_nacionales_activas = ejecutar_radar_nacional()

st.title("🔮 Monitor de Proyección Horaria y Alerta Temprana de Flota")

# 📰 BANNER TOP DE NOTICIAS LOGÍSTICAS (ALERTAS CRÍTICAS DE TODO EL PAÍS)
if alertas_nacionales_activas:
    texto_banner = "  •  ".join([a["mensaje"] for a in alertas_nacionales_activas[:4]])
    st.markdown(f"""
        <div style="background-color: #ffebe6; padding: 12px; border-left: 6px solid #ff4d4d; border-radius: 4px; margin-bottom: 15px;">
            <span style="color: #cc0000; font-weight: bold; font-size: 15px;">📢 RADAR CRÍTICO NACIONAL EN VIVO:</span> 
            <marquee style="color: #330000; font-size: 15px; font-weight: 500;" scrollamount="4">{texto_banner}</marquee>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
        <div style="background-color: #e6f9ff; padding: 10px; border-left: 6px solid #00a3cc; border-radius: 4px; margin-bottom: 15px; color: #004d61; font-weight: 500; font-size: 14px;">
            ✅ <b>Estatus Nacional Despejado:</b> No se registran cierres de vías de gran magnitud ni colisiones críticas en los ejes principales del país.
        </div>
    """, unsafe_allow_html=True)

# Indicador de sincronización en vivo
st.caption(f"Centro de Control Geoanalítico con Monitoreo de Clima y Waze Online | 🔄 Auto-refresco activo cada 5 min (Último: {hora_ecuador_actual.strftime('%I:%M:%S %p')})")

diccionario_dias = {
    "LUNES": 0, "MARTES": 1, "MIÉRCOLES": 2, "MIERCOLES": 2, 
    "JUEVES": 3, "VIERNES": 4, "SÁBADO": 5, "SABADO": 5, "DOMINGO": 6
}

@st.cache_data(ttl=300)
def obtener_clima_horario_futuro(lat, lon, fecha_objetivo_str):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,weathercode&timezone=auto&forecast_days=7"
        respuesta = requests.get(url).json()
        horas_raw = respuesta['hourly']['time']
        temperaturas = respuesta['hourly']['temperature_2m']
        codigos_clima = respuesta['hourly']['weathercode']
        
        datos_clima = {}
        for h, temp, codigo in zip(horas_raw, temperaturas, codigos_clima):
            fecha_part, hora_part = h.split("T")
            if fecha_part == fecha_objetivo_str:
                hora_int = int(hora_part.split(":")[0])
                if codigo == 0: estado, icono = "Despejado", "☀️"
                elif codigo in [1, 2, 3]: estado, icono = "Nublado", "☁️"
                elif codigo in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99]: estado, icono = "Lluvia", "🌧️"
                else: estado, icono = "Nublado", "☁️"
                datos_clima[hora_int] = {"Detalle": f"{icono} {estado} ({temp}°C)", "Icono": icono, "Estado": estado}
        return datos_clima if datos_clima else {i: {"Detalle": "⚪ Sin Predicción", "Icono": "⚪", "Estado": "Normal"} for i in range(24)}
    except:
        return {i: {"Detalle": "⚪ Sin Conexión", "Icono": "⚪", "Estado": "Normal"} for i in range(24)}

@st.cache_data(ttl=3600)
def calcular_factor_lluvia_en_vivo(df_historico, lat, lon):
    try:
        df_quick = df_historico.dropna(subset=["FECHA CREACIÓN DE ASISTENCIA", "HORA CREACIÓN DE ASISTENCIA"]).tail(60)
        if df_quick.empty: return 1.35
        fechas_unicas = df_quick["FECHA CREACIÓN DE ASISTENCIA"].astype(str).str.split().str[0].unique()
        lluvias_detectadas, total_evaluado = 0, 0
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
        return pd.read_csv(csv_url)
    except:
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
    col_cobertura = "TIPO COBERTURA"

    df_raw[col_provincia] = df_raw[col_provincia].astype(str).str.strip().str.upper()
    if col_ciudad in df_raw.columns: df_raw[col_ciudad] = df_raw[col_ciudad].astype(str).str.strip()
    df_raw[col_cobertura] = df_raw[col_cobertura].astype(str).str.strip().str.upper() if col_cobertura in df_raw.columns else "LOCAL"

    # 🎛️ PANEL ESTRUCTURADO CON HISTORIAL INTEGRADO EN LA FILA DE FILTROS
    st.write("### 🎛️ Panel de Filtros de Operación e Historial de Incidentes")
    
    col_filtros, col_historial = st.columns([7, 3])
    
    with col_filtros:
        f1, f2, f3 = st.columns(3)
        with f1:
            dia_sel = st.selectbox("📅 Seleccionar Día Tipo:", ["Todos", "LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"], index=0)
        with f2:
            lista_servicios = ["Todos"] + list(df_raw[col_servicio].dropna().unique())
            servicio_sel = st.selectbox("🎯 Seleccionar Servicio:", lista_servicios)
        with f3:
            lista_provincias = ["Todas"] + df_raw[col_provincia].value_counts().index.tolist()
            provincia_sel = st.selectbox("📍 Seleccionar Provincia:", lista_provincias)
            
        f4, f5 = st.columns([2, 1])
        with f4:
            if provincia_sel != "Todas":
                ciudades_disponibles = sorted(df_raw[df_raw[col_provincia] == provincia_sel][col_ciudad].dropna().unique().tolist())
                ciudad_sel = st.multiselect("🏙️ Filtrar Ciudades:", options=ciudades_disponibles, default=[], placeholder="Todas las ciudades")
            else:
                ciudad_sel = st.multiselect("🏙️ Filtrar Ciudades:", options=[], disabled=True, placeholder="Filtre por Provincia primero")
        with f5:
            estado_sel = st.selectbox("📌 Filtrar por Estado:", ["Todos"] + list(df_raw[col_estado].dropna().unique())) if col_estado in df_raw.columns else "Todos"

    with col_historial:
        # 📜 CAJA EXPANDIBLE DE HISTORIAL CON LÍMITE TEMPORAL DE TURNO (6 HORAS MÁX)
        with st.expander("📜 Bitácora de Alertas Nacionales (Últimas 6h)", expanded=True):
            if st.session_state.historial_alertas:
                for hist in st.session_state.historial_alertas[:6]:  
                    st.markdown(f"<small style='color:#666;'>⏱️ {hist['hora_str']} (Hoy)</small><br/><span style='font-size:13px; font-weight:500;'>{hist['mensaje']}</span><hr style='margin:4px 0;'/>", unsafe_allow_html=True)
            else:
                st.write("<span style='color:gray; font-size:13px;'>Sin incidencias críticas en las últimas 6 horas. Monitoreo limpio.</span>", unsafe_allow_html=True)

    # Lógica de Fechas y Filtros
    if dia_sel != "Todos":
        dia_actual_num = hora_ecuador_actual.weekday() 
        dia_destino_num = diccionario_dias.get(dia_sel.upper(), dia_actual_num)
        dias_diferencia = (dia_destino_num - dia_actual_num) % 7
        fecha_target_str = (hora_ecuador_actual + timedelta(days=dias_diferencia)).strftime("%Y-%m-%d")
        df_dia_especifico = df_raw[df_raw[col_dia].str.upper() == dia_sel.upper()]
    else:
        dias_diferencia, fecha_target_str = 0, hora_ecuador_actual.strftime("%Y-%m-%d")
        df_dia_especifico = df_raw.copy()

    num_fechas_reales = max(df_dia_especifico[col_fecha].nunique() if col_fecha in df_dia_especifico.columns else 1, 1)

    df_filtrado = df_dia_especifico.copy()
    if estado_sel != "Todos" and col_estado in df_raw.columns: df_filtrado = df_filtrado[df_filtrado[col_estado] == estado_sel]
    if servicio_sel != "Todos": df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
    if provincia_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado[col_provincia] == provincia_sel]
        if ciudad_sel: df_filtrado = df_filtrado[df_filtrado[col_ciudad].isin(ciudad_sel)]

    st.markdown("---")
    total_casos_historicos = len(df_filtrado)
    promedio_asistencias_dia = int(round(total_casos_historicos / num_fechas_reales, 0))
    st.metric(label="📊 Casos Promedio Esperados (Filtro Actual)", value=f"{promedio_asistencias_dia} Asistencias")
    st.markdown("---")

    col_tabla_izq, col_tabla_der = st.columns([4, 6])

    with col_tabla_izq:
        if total_casos_historicos > 0:
            if provincia_sel == "Todas":
                st.write("### 📋 Demanda General por Provincias")
                df_tabla_prov = df_filtrado.groupby(col_provincia).size().reset_index(name='Casos Históricos')
                df_tabla_prov['Promedio Diario Proyectado'] = (df_tabla_prov['Casos Históricos'] / num_fechas_reales).round(0).astype(int)
                st.dataframe(df_tabla_prov.sort_values(by='Casos Históricos', ascending=False), use_container_width=True, hide_index=True)
            else:
                st.write(f"### 📋 Demanda: Ciudades de {provincia_sel}")
                df_tabla_ciud = df_filtrado.groupby(col_ciudad).size().reset_index(name='Casos Históricos')
                df_tabla_ciud['Promedio Diario Proyectado'] = (df_tabla_ciud['Casos Históricos'] / num_fechas_reales).round(0).astype(int)
                st.dataframe(df_tabla_ciud.sort_values(by='Casos Históricos', ascending=False), use_container_width=True, hide_index=True)

    with col_tabla_der:
        if total_casos_historicos > 0:
            if servicio_sel == "Todos":
                st.write("### 📋 Ranking de Servicios")
                df_tabla_serv = df_filtrado.groupby(col_servicio).size().reset_index(name='Casos Históricos')
                df_tabla_serv['Promedio Diario Proyectado'] = (df_tabla_serv['Casos Históricos'] / num_fechas_reales).round(0).astype(int)
                st.dataframe(df_tabla_serv.sort_values(by='Casos Históricos', ascending=False), use_container_width=True, hide_index=True)
            else:
                st.write(f"### ⏰ Matriz Horaria Avanzada y Necesidad de Flota")
                
                # Radar de tráfico local en la sección derecha
                if provincia_sel != "Todas":
                    st.write("#### 📡 Reportes de Tráfico Waze Local (Live Online)")
                    lat_p, lon_p = coordenadas_provincias.get(provincia_sel, [-0.2298, -78.5249])
                    es_limpio, alertas_locales = obtener_alertas_waze_real(lat_p, lon_p, provincia_sel)
                    
                    if es_limpio:
                        st.success("✅ **Waze Live:** Flujo vial local estable y monitoreado sin novedades en este cuadrante.")
                    else:
                        for al in alertas_locales:
                            if al["critico"]: st.error(al["mensaje"])
                            else: st.warning(al["mensaje"])

                # Render de la Tabla Horaria Integrada
                if col_hora_agrupada in df_filtrado.columns:
                    df_horas_raw = df_filtrado.copy()
                    df_horas_raw[col_hora_agrupada] = pd.to_numeric(df_horas_raw[col_hora_agrupada], errors='coerce').fillna(-1).astype(int)
                    
                    registros_tabla = []
                    lat_c, lon_c = coordenadas_provincias.get(provincia_sel if provincia_sel != "Todas" else 'PICHINCHA', [-0.2298, -78.5249])
                    factor_ajuste = calcular_factor_lluvia_en_vivo(df_filtrado, lat_c, lon_c) if provincia_sel != "Todas" else 1.0
                    diccionario_clima = obtener_clima_horario_futuro(lat_c, lon_c, fecha_target_str) if provincia_sel != "Todas" else {}

                    for hr in range(24):
                        df_bloque = df_horas_raw[df_horas_raw[col_hora_agrupada] == hr]
                        base_total = int(round(len(df_bloque) / num_fechas_reales, 0))
                        
                        clima_info = diccionario_clima.get(hr, {"Detalle": "🌍 Nacional (Filtre Prov.)", "Estado": "Normal"})
                        
                        string_proyeccion = f"{base_total} (Normal)"
                        if clima_info["Estado"] == "Lluvia":
                            string_proyeccion = f"🔥 {int(round(base_total * factor_ajuste, 0))} (Alerta)"
                        
                        gruas_necesarias = math.ceil(base_total * 1.2)
                        string_gruas = f"🚛 {gruas_necesarias} Unidades" if "REMOLQUE" in str(servicio_sel).upper() else "-"
                        
                        if base_total > 0 or "REMOLQUE" in str(servicio_sel).upper():
                            registros_tabla.append({
                                "BLOQUE HORARIO": hr,
                                "🌤️ Clima Online": clima_info["Detalle"],
                                "Promedio Base": base_total,
                                "Proyección Ajustada": string_proyeccion,
                                "Grúas Necesarias (Arrastre)": string_gruas
                            })
                            
                    st.dataframe(pd.DataFrame(registros_tabla), use_container_width=True, hide_index=True)

    st.markdown("---")
    @st.fragment(run_every=300)
    def ejecutar_autorefresh(): pass
    ejecutar_autorefresh()
else:
    st.warning("⚠️ Esperando conexión con el archivo de Google Drive...")
