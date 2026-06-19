import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import math
import streamlit.components.v1 as components

# 1. Configuración de pantalla ultra ancha para el monitor de control
st.set_page_config(
    layout="wide", 
    page_title="Monitor de Proyecciones 2026 - Control de Flota",
    initial_sidebar_state="collapsed"
)

# --- RECARGA NATIVA FORZADA DE VENTANA CADA 5 MINUTOS (300 SEGUNDOS) ---
components.html(
    """
    <script>
        setTimeout(function(){
            window.parent.location.reload();
        }, 300000); // 5 minutos exactos
    </script>
    """,
    height=0,
    width=0
)

# Estilos CSS corporativos
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDataFrame [data-testid="stDataFrameDownloadButton"] {display: none;}
    button[title="View fullscreen"] {display: none;}
    
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        margin-top: 0px !important;
    }
    
    [data-testid="stTable"] td, [data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] [role="gridcell"] {
        font-size: 14px !important;
        font-weight: 500 !important;
        padding: 4px 6px !important;
    }
    [data-testid="stTable"] th, [data-testid="stDataFrame"] th, div[data-testid="stDataFrame"] [role="columnheader"] {
        font-size: 14px !important;
        font-weight: bold !important;
        padding: 6px 6px !important;
    }
    
    .alerta-clima-mini {
        padding: 4px 10px !important;
        margin-bottom: 4px !important;
        border-left: 4px solid #ff4b4b;
        background-color: #ffebeb;
        color: #ff4b4b;
        font-size: 13px !important;
        font-weight: bold;
        border-radius: 4px;
    }
    
    .card-saldo {
        background-color: #f0f7f4;
        border: 1px solid #d2e7de;
        padding: 10px;
        border-radius: 6px;
        text-align: center;
        margin-top: 10px;
    }
    .banner-feriado {
        background-color: #fff8e1;
        border-left: 5px solid #ffb300;
        padding: 10px;
        border-radius: 4px;
        margin-bottom: 15px;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)

zona_ecuador = ZoneInfo("America/Guayaquil")
ahora_actual = datetime.now(zona_ecuador)
hora_estatica_str = ahora_actual.strftime('%I:%M:%S %p')

st.title("🔮 Monitor de Proyección Horaria y Alerta Temprana de Flota")
st.markdown(f"**Centro de Control Geoanalítico** | 🔄 Próximo refresco automático en 5 min. **(Última Actualización del Tablero: {hora_estatica_str})**")

# --- MEMORIA SERVIDOR ALTA DISPONIBILIDAD (Inmune a refresh de navegador) ---
@st.cache_resource
def inicializar_memoria_inmune():
    return {
        "creditos": 47,
        "alertas_waze": [],
        "ultima_hora_waze": "Nunca",
        "filtros_persistentes": {
            "dia_sel": "TODOS",
            "servicio_sel": "Todos",
            "provincia_sel": "Todas",
            "ciudad_sel": [],
            "estado_sel": []
        }
    }

estado_global = inicializar_memoria_inmune()

# Precarga de estados persistentes en st.session_state
if "dia_sel_key" not in st.session_state:
    st.session_state["dia_sel_key"] = estado_global["filtros_persistentes"]["dia_sel"]
if "servicio_sel_key" not in st.session_state:
    st.session_state["servicio_sel_key"] = estado_global["filtros_persistentes"]["servicio_sel"]
if "provincia_sel_key" not in st.session_state:
    st.session_state["provincia_sel_key"] = estado_global["filtros_persistentes"]["provincia_sel"]
if "ciudad_sel_key" not in st.session_state:
    st.session_state["ciudad_sel_key"] = estado_global["filtros_persistentes"]["ciudad_sel"]
if "estado_sel_key" not in st.session_state:
    st.session_state["estado_sel_key"] = estado_global["filtros_persistentes"]["estado_sel"]

# Funciones callbacks de resguardo inmediato
def guardar_dia_callback(): estado_global["filtros_persistentes"]["dia_sel"] = st.session_state["dia_sel_key"]
def guardar_servicio_callback(): estado_global["filtros_persistentes"]["servicio_sel"] = st.session_state["servicio_sel_key"]
def guardar_provincia_callback():
    estado_global["filtros_persistentes"]["provincia_sel"] = st.session_state["provincia_sel_key"]
    estado_global["filtros_persistentes"]["ciudad_sel"] = []
    st.session_state["ciudad_sel_key"] = []
def guardar_ciudad_callback(): estado_global["filtros_persistentes"]["ciudad_sel"] = st.session_state["ciudad_sel_key"]
def guardar_estado_callback(): estado_global["filtros_persistentes"]["estado_sel"] = st.session_state["estado_sel_key"]

# Configuración geográfica macro
bbox_nacional_ecuador = {"bottom_left": "-5.0000,-81.0000", "top_right": "1.5000,-75.0000"}

coordenadas_provincias = {
    'PICHINCHA': [-0.2298, -78.5249], 'GUAYAS': [-2.1894, -79.8890], 'AZUAY': [-2.9001, -79.0059],
    'MANABI': [-1.0543, -80.4544], 'EL ORO': [-3.2581, -79.9553], 'LOJA': [-3.9931, -79.2042], 
    'TUNGURAHUA': [-1.2491, -78.6168], 'CHIMBORAZO': [-1.6743, -78.6483], 'ESMERALDAS': [0.9682, -79.6517], 
    'LOS RIOS': [-1.4558, -79.4622], 'SANTO DOMINGO DE LOS TSACHILAS': [-0.2530, -79.1754], 
    'SANTA ELENA': [-2.2262, -80.8584], 'IMBABURA': [0.3517, -78.1223], 'COTOPAXI': [-0.9352, -78.6155], 
    'CARCHI': [0.7384, -77.7289], 'SUCUMBIOS': [0.0847, -76.8828], 'ORELLANA': [-0.5665, -76.9872], 
    'NAPO': [-0.9902, -77.8129], 'PASTAZA': [-1.4870, -77.9954], 'MORONA SANTIAGO': [-2.3087, -78.1114], 
    'ZAMORA CHINCHIPE': [-4.0692, -78.9566], 'GALAPAGOS': [-0.7402, -90.3119], 'BOLIVAR': [-1.5910, -79.0022], 
    'CANAR': [-2.5518, -78.9392]
}

diccionario_dias = {"LUNES": 0, "MARTES": 1, "MIÉRCOLES": 2, "MIERCOLES": 2, "JUEVES": 3, "VIERNES": 4, "SÁBADO": 5, "SABADO": 5, "DOMINGO": 6}

# Mapeo de Retornos de Feriados Nacionales 2026
calendario_feriados_2026 = {
    "Retorno Año Nuevo (Enero 5)": {"fecha_origen": "2026-01-05", "tipo": "Real (Año Nuevo)"},
    "Retorno Carnaval (Febrero 18)": {"fecha_origen": "2026-02-18", "tipo": "Real (4 Días Largo)"},
    "Retorno Viernes Santo (Abril 6)": {"fecha_origen": "2026-04-06", "tipo": "Real (Fin de semana largo)"},
    "Retorno Día del Trabajo (Mayo 4)": {"fecha_origen": "2026-05-04", "tipo": "Real (Fin de semana largo)"},
    "🔮 [Proyección] Retorno Primer Grito de Independencia (Agosto 11)": {"fecha_origen": "2026-05-04", "tipo": "Simulado (Basado en Feriado de Mayo)"},
    "🔮 [Proyección] Retorno Independencia de Guayaquil (Octubre 12)": {"fecha_origen": "2026-04-06", "tipo": "Simulado (Basado en Feriado de Abril)"},
    "🔮 [Proyección] Retorno Difuntos y Cuenca (Noviembre 5)": {"fecha_origen": "2026-02-18", "tipo": "Simulado (Basado en Feriado de Carnaval)"},
    "🔮 [Proyección] Retorno Navidad (Diciembre 28)": {"fecha_origen": "2026-01-05", "tipo": "Simulado (Basado en Feriado de Año Nuevo)"}
}

# Conectores API de Clima y Waze
def consultar_alertas_waze_real(bbox_dict):
    api_key = "ak_823f13app2zd9qkia4z6vdi27ttb31z9a7v7pvlhnn878w3"
    try:
        url = "https://api.openwebninja.com/waze/alerts-and-jams"
        headers = {"X-API-Key": api_key}
        params = {"bottom_left": bbox_dict["bottom_left"], "top_right": bbox_dict["top_right"]}
        respuesta = requests.get(url, headers=headers, params=params, timeout=10).json()
        alertas = []
        if "alerts" in respuesta and respuesta["alerts"]:
            for item in respuesta["alerts"][:5]:
                tipo = item.get("type", "TRÁFICO").replace("_", " ")
                subtipo = item.get("subtype", "").replace("_", " ")
                calle = item.get("street", "Vía pública")
                ciudad = item.get("city", "")
                ubicacion = f" en {calle} ({ciudad})" if ciudad else f" en {calle}"
                alertas.append(f"⚠️ {tipo} ({subtipo}){ubicacion}")
        return alertas if alertas else ["✅ Sin incidentes críticos reportados en carreteras principales del país."]
    except: return ["⚠️ Error de conexión con los servidores viales."]

@st.cache_data(ttl=300)
def obtener_clima_horario_futuro(lat, lon, fecha_objetivo_str):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,weathercode&timezone=auto&forecast_days=7"
        respuesta = requests.get(url, timeout=5).json()
        horas_raw, temperaturas, codigos_clima = respuesta['hourly']['time'], respuesta['hourly']['temperature_2m'], respuesta['hourly']['weathercode']
        datos_clima = {}
        for h, temp, codigo in zip(horas_raw, temperaturas, codigos_clima):
            fecha_part, hora_part = h.split("T")
            if fecha_part == fecha_objetivo_str:
                hora_int = int(hora_part.split(":")[0])
                estado = "Lluvia" if codigo in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99] else "Normal"
                icono = "🌧️" if estado == "Lluvia" else ("☀️" if codigo == 0 else "☁️")
                datos_clima[hora_int] = {"Detalle": f"{icono} {estado} ({temp}°C)", "Estado": estado}
        return datos_clima
    except: return {}

@st.cache_data(ttl=300)
def obtener_clima_actual_rapido(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
        res = requests.get(url, timeout=3).json()
        code, temp = res['current_weather']['weathercode'], res['current_weather']['temperature']
        return f"🌧️ Lluvia ({temp}°C)" if code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99] else f"☁️ Nublado ({temp}°C)"
    except: return "🌍 N/A"

@st.cache_data(ttl=300)
def cargar_datos_vía_gviz():
    try:
        url_base = "https://docs.google.com/spreadsheets/d/1UWQy9XJy8UOdef1IcXWDt2Nmn7hTnsQLHby_3BhpJnc/edit"
        pestana = "Consolidado"
        csv_url = url_base.replace('/edit', f'/gviz/tq?tqx=out:csv&sheet={pestana}')
        return pd.read_csv(csv_url)
    except: return None

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

    df_raw[col_provincia] = df_raw[col_provincia].astype(str).str.strip().str.upper().str.normalize('NFKD').str.encode('ascii', errors='ignore').str.decode('utf-8')
    if col_ciudad in df_raw.columns: df_raw[col_ciudad] = df_raw[col_ciudad].astype(str).str.strip()
    df_raw[col_cobertura] = df_raw[col_cobertura].astype(str).str.strip().str.upper() if col_cobertura in df_raw.columns else "LOCAL"

    # --- ENRUTAMIENTO POR PESTAÑAS ---
    tab_normal, tab_feriados = st.tabs(["🔮 Operación Diaria (Normal)", "📈 Planificador de Feriados Nacionales"])

    # ==========================================
    # PESTAÑA 1: OPERACIÓN NORMAL
    # ==========================================
    with tab_normal:
        st.write("### 🎛️ Panel de Filtros de Operación")
        f1, f2, f3, f4, f5 = st.columns([2, 2, 2, 3, 3])
        
        with f1:
            dias_en_orden = ["TODOS", "LUNES", "MARTES", "MIÉRCOLES", "MIERCOLES", "JUEVES", "VIERNES", "SÁBADO", "SABADO", "DOMINGO"]
            dias_disponibles = [d for d in dias_en_orden if d == "TODOS" or d in list(df_raw[col_dia].str.upper().unique())]
            dia_sel = st.selectbox("📅 Seleccionar Día Tipo:", dias_disponibles, key="dia_sel_key", on_change=guardar_dia_callback)
        with f2:
            lista_servicios = ["Todos"] + sorted(list(df_raw[col_servicio].dropna().unique()))
            servicio_sel = st.selectbox("🎯 Seleccionar Servicio:", lista_servicios, key="servicio_sel_key", on_change=guardar_servicio_callback)
        with f3:
            lista_provincias = ["Todas"] + df_raw[col_provincia].value_counts().index.tolist()
            provincia_sel = st.selectbox("📍 Seleccionar Provincia:", lista_provincias, key="provincia_sel_key", on_change=guardar_provincia_callback)
        with f4:
            if provincia_sel != "Todas":
                ciudades_disponibles = sorted(df_raw[df_raw[col_provincia] == provincia_sel][col_ciudad].dropna().unique().tolist())
                ciudad_sel = st.multiselect("🏙️ Filtrar Ciudades:", ciudades_disponibles, key="ciudad_sel_key", on_change=guardar_ciudad_callback)
            else:
                ciudad_sel = st.multiselect("🏙️ Filtrar Ciudades:", options=[], disabled=True, placeholder="Filtre por Provincia primero")
        with f5:
            if col_estado in df_raw.columns:
                estados_disponibles = sorted(list(df_raw[col_estado].dropna().unique()))
                estado_sel = st.multiselect("📌 Filtrar por Estado:", options=estados_disponibles, key="estado_sel_key", on_change=guardar_estado_callback)
            else: estado_sel = []

        if dia_sel.upper() == "TODOS":
            df_dia_especifico = df_raw.copy()
            num_fechas_reales = df_dia_especifico[col_fecha].nunique() if col_fecha in df_dia_especifico.columns else 1
            fecha_target_str = ahora_actual.strftime("%Y-%m-%d")
        else:
            dia_destino_num = diccionario_dias.get(dia_sel.upper(), ahora_actual.weekday())
            dias_diferencia = (dia_destino_num - ahora_actual.weekday()) % 7
            fecha_target_str = (ahora_actual + timedelta(days=dias_diferencia)).strftime("%Y-%m-%d")
            df_dia_especifico = df_raw[df_raw[col_dia].str.upper() == dia_sel.upper()]
            num_fechas_reales = df_dia_especifico[col_fecha].nunique() if col_fecha in df_dia_especifico.columns else 1

        if num_fechas_reales <= 0: num_fechas_reales = 1

        df_filtrado = df_dia_especifico.copy()
        if estado_sel and col_estado in df_raw.columns: df_filtrado = df_filtrado[df_filtrado[col_estado].isin(estado_sel)]
        if servicio_sel != "Todos": df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
        if provincia_sel != "Todas":
            df_filtrado = df_filtrado[df_filtrado[col_provincia] == provincia_sel]
            if ciudad_sel: df_filtrado = df_filtrado[df_filtrado[col_ciudad].isin(ciudad_sel)]

        hora_actual_num = ahora_actual.hour
        provincia_key_busqueda = provincia_sel.upper().strip()
        
        if provincia_sel != "Todas" and provincia_key_busqueda in coordenadas_provincias:
            lat_c, lon_c = coordenadas_provincias[provincia_key_busqueda]
            diccionario_clima = obtener_clima_horario_futuro(lat_c, lon_c, fecha_target_str)
        else:
            diccionario_clima = {}
            lat_c, lon_c = -0.2298, -78.5249

        col_izq, col_cen, col_der = st.columns([3.4, 6.1, 2.5])
        
        with col_izq:
            promedio_asistencias_dia = int(round(len(df_filtrado) / num_fechas_reales, 0))
            st.write(f"##### 📋 Promedio Demanda ({dia_sel.title()})")
            st.metric(label="", value=f"{promedio_asistencias_dia} Asist.")
            
            if len(df_filtrado) > 0:
                if provincia_sel == "Todas":
                    st.write("##### 📋 Demanda Provincias")
                    df_tp = df_filtrado.groupby(col_provincia).size().reset_index(name='Casos')
                    df_tp['Prom.'] = (df_tp['Casos'] / num_fechas_reales).round(0).astype(int)
                    df_tp['Clima Online'] = [obtener_clima_actual_rapido(coordenadas_provincias[p][0], coordenadas_provincias[p][1]) if p in coordenadas_provincias else "🌍 N/A" for p in df_tp[col_provincia]]
                    st.dataframe(df_tp.sort_values(by='Casos', ascending=False), use_container_width=True, hide_index=True)
                else:
                    st.write(f"##### 📋 Ciudades: {provincia_sel.title()}")
                    df_tc = df_filtrado.groupby(col_ciudad).size().reset_index(name='Casos')
                    df_tc['Prom.'] = (df_tc['Casos'] / num_fechas_reales).round(0).astype(int)
                    df_tc['Clima Online'] = obtener_clima_actual_rapido(lat_c, lon_c)
                    st.dataframe(df_tc.sort_values(by='Casos', ascending=False), use_container_width=True, hide_index=True)

        with col_cen:
            st.write(f"### ⏰ Matriz Horaria y Flota Simplificada: {dia_sel.title()}")
            if len(df_filtrado) > 0 and col_hora_agrupada in df_filtrado.columns:
                df_horas_raw = df_filtrado.copy()
                df_horas_raw[col_hora_agrupada] = pd.to_numeric(df_horas_raw[col_hora_agrupada], errors='coerce').fillna(-1).astype(int)
                
                casos_locales, casos_foraneos = [0] * 24, [0] * 24
                for hr in range(24):
                    df_b = df_horas_raw[df_horas_raw[col_hora_agrupada] == hr]
                    for _, fila in df_b.iterrows():
                        if "FOR" in str(fila[col_cobertura]).upper(): casos_foraneos[hr] += 1
                        else: casos_locales[hr] += 1

                registros_tabla = []
                for hr in range(24):
                    p_local, p_foraneo = casos_locales[hr] / num_fechas_reales, casos_foraneos[hr] / num_fechas_reales
                    promedio_base_calculado = int(round(p_local + p_foraneo, 0))
                    
                    clima_info = diccionario_clima.get(hr, {"Detalle": "☁️ Nublado (N/A)", "Estado": "Normal"})
                    detalle_clima = clima_info["Detalle"] if provincia_sel != "Todas" else "🌍 Filtre Provincia"

                    l_ant = p_local if hr == 0 else (casos_locales[hr-1] / num_fechas_reales)
                    f_ant1 = p_foraneo if hr == 0 else (casos_foraneos[hr-1] / num_fechas_reales)
                    f_ant2 = p_foraneo if hr <= 1 else (casos_foraneos[hr-2] / num_fechas_reales)
                    
                    gruas_necesarias = math.ceil((p_local + (0.5 * l_ant)) + (p_foraneo + f_ant1 + f_ant2))
                    es_remolque = any(x in str(servicio_sel).upper() for x in ["REMOLQUE", "GRÚA", "GRUA", "TODOS"])
                    
                    string_gruas = f"🚛 {gruas_necesarias} U." if es_remolque and (promedio_base_calculado > 0 or gruas_necesarias > 0) else "-"
                    motivo_asesor = "Normal" if string_gruas == "-" else (f"🟢 Para los {promedio_base_calculado} casos." if gruas_necesarias == promedio_base_calculado else f"⏳ {promedio_base_calculado} nuevos + arrastre.")

                    if promedio_base_calculado > 0 or string_gruas != "-":
                        registros_tabla.append({"HORA": f"{hr:02d}:00", "🌤️ Clima Online": detalle_clima, "📊 Promed": promedio_base_calculado, "📈 Proyección": f"{promedio_base_calculado} (Normal)", "🚛 Grúas N.": string_gruas, "📋 ¿Por qué?": motivo_asesor})

                if registros_tabla: st.dataframe(pd.DataFrame(registros_tabla), use_container_width=True, hide_index=True)

        with col_der:
            st.write("##### 🚛 Alertas Nacionales Waze")
            ejecutar_consulta = st.button("🔍 Consultar Tráfico en Vivo (Ecuador)", use_container_width=True)
            if ejecutar_consulta and estado_global["creditos"] > 0:
                with st.spinner("Escaneando Ecuador..."):
                    estado_global["alertas_waze"] = consultar_alertas_waze_real(bbox_nacional_ecuador)
                    estado_global["ultima_hora_waze"] = ahora_actual.strftime('%I:%M:%S %p')
                    estado_global["creditos"] -= 1 
            st.caption(f"⏱️ Último reporte Waze: **{estado_global['ultima_hora_waze']}**")
            
            if not estado_global["alertas_waze"]: st.info("💡 Consulta manual activa para cuidar créditos.")
            else:
                for incidente in estado_global["alertas_waze"]:
                    if "✅" in incidente: st.success(incidente)
                    else: st.error(incidente)
                    
            st.markdown(f'<div class="card-saldo"><span style="font-size:11px;color:#555;font-weight:bold;display:block;">🔑 CRÉDITOS DISPONIBLES</span><span style="font-size:24px;color:#2e7d32;font-weight:800;">{estado_global["creditos"]}</span><span style="font-size:13px;color:#777;"> / 50 Restantes</span></div>', unsafe_allow_html=True)


    # ==========================================
    # PESTAÑA 2: PLANIFICADOR DE FERIADOS
    # ==========================================
    with tab_feriados:
        st.write("### 🏖️ Analizador de Tendencias y Retornos de Feriados Nacionales")
        
        c_fer1, c_fer2 = st.columns([4, 4])
        with c_fer1:
            feriado_seleccionado = st.selectbox("📅 Seleccione el Feriado a Analizar (Calendario 2026):", list(calendario_feriados_2026.keys()))
        with c_fer2:
            servicio_feriado = st.selectbox("🎯 Filtrar Servicio para Feriado:", sorted(list(df_raw[col_servicio].dropna().unique())), index=0)

        meta_feriado = calendario_feriados_2026[feriado_seleccionado]
        fecha_analisis = meta_feriado["fecha_origen"]
        
        # --- NUEVA LÓGICA DE DETECCIÓN INTELEGENTE DE FORMATOS DE FECHA ---
        # Convertimos la columna de texto a un objeto datetime puro para evitar colisiones de strings (DD/MM/AAAA vs AAAA-MM-DD)
        df_raw["FECHA_DATETIME"] = pd.to_datetime(df_raw[col_fecha], errors='coerce')
        fecha_analisis_dt = pd.to_datetime(fecha_analisis).date()
        
        # Filtrado optimizado por fecha absoluta y servicio
        df_data_feriado = df_raw[(df_raw["FECHA_DATETIME"].dt.date == fecha_analisis_dt) & (df_raw[col_servicio] == servicio_feriado)]
        
        st.markdown(f"""
            <div class="banner-feriado">
                ℹ️ <b>Métrica de Origen:</b> Analizando el día de retorno real <b>{fecha_analisis}</b> | 
                <b>Estructura de Simulación:</b> {meta_feriado['tipo']}.
            </div>
        """, unsafe_allow_html=True)

        if df_data_feriado.empty:
            st.warning(f"⚠️ No se encontraron registros de asistencias para el servicio '{servicio_feriado}' en la fecha histórica {fecha_analisis} (Enero-Mayo 2026). Pruebe cambiando de servicio.")
        else:
            col_f_izq, col_f_der = st.columns([4, 8])
            
            with col_f_izq:
                total_casos_feriado = len(df_data_feriado)
                st.metric(label="📊 Volumen Total de Asistencias en Retorno", value=f"{total_casos_feriado} Casos")
                
                st.write("##### 📍 Provincias con Mayor Carga de Retorno")
                df_prov_feriado = df_data_feriado.groupby(col_provincia).size().reset_index(name='Casos').sort_values(by='Casos', ascending=False)
                st.dataframe(df_prov_feriado, use_container_width=True, hide_index=True)
                
            with col_f_der:
                st.write(f"### ⏰ Matriz Horaria y Flota Crítica de Retorno")
                
                df_data_feriado[col_hora_agrupada] = pd.to_numeric(df_data_feriado[col_hora_agrupada], errors='coerce').fillna(-1).astype(int)
                casos_loc_f, casos_for_f = [0] * 24, [0] * 24
                
                for _, fila in df_data_feriado.iterrows():
                    hr = int(fila[col_hora_agrupada])
                    if 0 <= hr < 24:
                        if "FOR" in str(fila[col_cobertura]).upper(): casos_for_f[hr] += 1
                        else: casos_loc_f[hr] += 1
                
                tabla_feriado_reporte = []
                for hr in range(24):
                    c_loc, c_for = casos_loc_f[hr], casos_for_f[hr]
                    total_hora = c_loc + c_for
                    
                    l_ant = casos_loc_f[hr-1] if hr > 0 else c_loc
                    f_ant1 = casos_for_f[hr-1] if hr > 0 else c_for
                    f_ant2 = casos_for_f[hr-2] if hr > 1 else c_for
                    
                    gruas_feriado = math.ceil((c_loc + (0.5 * l_ant)) + (c_for + f_ant1 + f_ant2))
                    
                    if total_hora > 0 or gruas_feriado > 0:
                        alerta_pico = "🔥 PICO CRÍTICO" if total_hora >= 4 else "Normal"
                        tabla_feriado_reporte.append({
                            "HORA": f"{hr:02d}:00",
                            "📉 Volumen Histórico": total_hora,
                            "🚛 Grúas Críticas Requeridas": f"🚛 {gruas_feriado} U.",
                            "🚨 Estado Operativo": alerta_pico
                        })
                
                if tabla_feriado_reporte:
                    st.dataframe(pd.DataFrame(tabla_feriado_reporte), use_container_width=True, hide_index=True)
                else:
                    st.info("Sin registros horarios estructurados.")
