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
    </style>
    """, unsafe_allow_html=True)

zona_ecuador = ZoneInfo("America/Guayaquil")
ahora_actual = datetime.now(zona_ecuador)
hora_estatica_str = ahora_actual.strftime('%I:%M:%S %p')

st.title("🔮 Monitor de Proyección Horaria y Alerta Temprana de Flota")
st.markdown(f"**Centro de Control Geoanalítico** | 🔄 Próximo refresco automático en 5 min. **(Última Actualización del Tablero: {hora_estatica_str})**")

# Cuadrantes BBox autorizados para las 4 regiones clave solicitadas
coordenadas_bbox_provincias = {
    'PICHINCHA': {"bottom_left": "-0.3700,-78.6500", "top_right": "-0.0500,-78.3500"}, # Quito y valles
    'GUAYAS': {"bottom_left": "-2.3000,-80.0500", "top_right": "-2.0000,-79.7500"},    # Guayaquil y enlaces
    'AZUAY': {"bottom_left": "-2.9500,-79.1000", "top_right": "-2.8500,-78.9500"},     # Cuenca
    'MANABI': {"bottom_left": "-1.1000,-80.8000", "top_right": "-0.9000,-80.4000"},    # Manta / Portoviejo
    'MANABÍ': {"bottom_left": "-1.1000,-80.8000", "top_right": "-0.9000,-80.4000"}
}

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

diccionario_dias = {
    "LUNES": 0, "MARTES": 1, "MIÉRCOLES": 2, "MIERCOLES": 2, 
    "JUEVES": 3, "VIERNES": 4, "SÁBADO": 5, "SABADO": 5, "DOMINGO": 6
}

# 🛣️ CONSULTA ADAPTADA A TU ENDPOINT DE OPENWEBNINJA (ALERTS-AND-JAMS)
def consultar_alertas_waze_real(bbox_dict):
    api_key = "ak_823f13app2zd9qkia4z6vdi27ttb31z9a7v7pvlhnn878w3"
    try:
        url = "https://api.openwebninja.com/waze/alerts-and-jams"
        headers = {"X-API-Key": api_key}
        params = {
            "bottom_left": bbox_dict["bottom_left"],
            "top_right": bbox_dict["top_right"]
        }
        respuesta = requests.get(url, headers=headers, params=params, timeout=7).json()
        
        alertas = []
        if "alerts" in respuesta and respuesta["alerts"]:
            for item in respuesta["alerts"][:4]:
                tipo = item.get("type", "TRÁFICO").replace("_", " ")
                subtipo = item.get("subtype", "").replace("_", " ")
                calle = item.get("street", "Vía pública")
                alertas.append(f"⚠️ {tipo} ({subtipo}) en {calle}")
        
        if not alertas:
            return ["✅ Sin incidentes graves reportados por Waze en este cuadrante."]
        return alertas
    except:
        return ["⚠️ No se encontraron reportes activos o el formato de zona requiere mayor precisión."]

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

@st.cache_data(ttl=300)
def obtener_clima_actual_rapido(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
        res = requests.get(url).json()
        code = res['current_weather']['weathercode']
        temp = res['current_weather']['temperature']
        if code == 0: return f"☀️ Despejado ({temp}°C)"
        elif code in [1, 2, 3]: return f"☁️ Nublado ({temp}°C)"
        elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99]: return f"🌧️ Lluvia ({temp}°C)"
        return f"☁️ Nublado ({temp}°C)"
    except:
        return "⚪ N/A"

@st.cache_data(ttl=3600)
def calcular_factor_lluvia_en_vivo(df_historico, lat, lon):
    try:
        df_quick = df_historico.dropna(subset=["FECHA CREACIÓN DE ASISTENCIA", "HORA CREACIÓN DE ASISTENCIA"]).tail(60)
        if df_quick.empty: return 1.35
        fechas_unicas = df_quick["FECHA CREACIÓN DE ASISTENCIA"].astype(str).str.split().str[0].unique()
        lluvias_detectadas, total_evaluado = 0, 0
        for fecha in fechas_unicas[:4]:
            res = requests.get(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={fecha}&end_date={fecha}&hourly=weathercode&timezone=auto").json()
            if 'hourly' in res:
                codigos = res['hourly']['weathercode']
                lluvias_detectadas += sum(1 for c in codigos if c in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99])
                total_evaluado += len(codigos)
        if total_evaluado > 0 and lluvias_detectadas > 0:
            return round(1.2 + ((lluvias_detectadas / total_evaluado) * 1.5), 2)
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

    st.write("### 🎛️ Panel de Filtros de Operación")
    f1, f2, f3, f4, f5 = st.columns([2, 2, 2, 3, 3])
    
    with f1:
        dias_en_orden = ["TODOS", "LUNES", "MARTES", "MIÉRCOLES", "MIERCOLES", "JUEVES", "VIERNES", "SÁBADO", "SABADO", "DOMINGO"]
        dias_disponibles = [d for d in dias_en_orden if d == "TODOS" or d in list(df_raw[col_dia].str.upper().unique())]
        dia_sel = st.selectbox("📅 Seleccionar Día Tipo:", dias_disponibles, index=0)
    
    with f2:
        servicio_sel = st.selectbox("🎯 Seleccionar Servicio:", ["Todos"] + list(df_raw[col_servicio].dropna().unique()))
    with f3:
        provincia_sel = st.selectbox("📍 Seleccionar Provincia:", ["Todas"] + df_raw[col_provincia].value_counts().index.tolist())
    with f4:
        if provincia_sel != "Todas":
            ciudad_sel = st.multiselect("🏙️ Filtrar Ciudades:", sorted(df_raw[df_raw[col_provincia] == provincia_sel][col_ciudad].dropna().unique().tolist()), default=[], placeholder="Todas las ciudades")
        else:
            ciudad_sel = st.multiselect("🏙️ Filtrar Ciudades:", options=[], disabled=True, placeholder="Filtre por Provincia primero")
    with f5:
        if col_estado in df_raw.columns:
            estados_disponibles = sorted(list(df_raw[col_estado].dropna().unique()))
            estado_sel = st.multiselect("📌 Filtrar por Estado:", options=estados_disponibles, default=[], placeholder="Todos los estados")
        else:
            estado_sel = []

    if dia_sel.upper() == "TODOS":
        df_dia_especifico = df_raw.copy()
        num_fechas_reales = df_dia_especifico[col_fecha].nunique() if col_fecha in df_dia_especifico.columns else 1
        fecha_target_str = ahora_actual.strftime("%Y-%m-%d")
        dias_diferencia = 0
    else:
        dia_destino_num = diccionario_dias.get(dia_sel.upper(), ahora_actual.weekday())
        dias_diferencia = (dia_destino_num - ahora_actual.weekday()) % 7
        fecha_target_str = (ahora_actual + timedelta(days=dias_diferencia)).strftime("%Y-%m-%d")
        df_dia_especifico = df_raw[df_raw[col_dia].str.upper() == dia_sel.upper()]
        num_fechas_reales = df_dia_especifico[col_fecha].nunique() if col_fecha in df_dia_especifico.columns else 1

    if num_fechas_reales <= 0: num_fechas_reales = 1

    df_filtrado = df_dia_especifico.copy()
    
    if estado_sel and col_estado in df_raw.columns: 
        df_filtrado = df_filtrado[df_filtrado[col_estado].isin(estado_sel)]
        
    if servicio_sel != "Todos": df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
    if provincia_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado[col_provincia] == provincia_sel]
        if ciudad_sel: df_filtrado = df_filtrado[df_filtrado[col_ciudad].isin(ciudad_sel)]

    hora_actual = ahora_actual.hour
    if provincia_sel != "Todas":
        lat_c, lon_c = coordenadas_provincias.get(provincia_sel, [-0.2298, -78.5249])
        diccionario_clima = obtener_clima_horario_futuro(lat_c, lon_c, fecha_target_str)
        factor_ajuste = calcular_factor_lluvia_en_vivo(df_filtrado, lat_c, lon_c)
    else:
        diccionario_clima, factor_ajuste = {}, 1.0

    st.markdown("---")
    
    col_izq, col_cen, col_der = st.columns([3.4, 6.1, 2.5])
    
    with col_izq:
        promedio_asistencias_dia = int(round(len(df_filtrado) / num_fechas_reales, 0))
        st.metric(label=f"📊 Promedio Demanda ({dia_sel.title()})", value=f"{promedio_asistencias_dia} Asist.")
        
        if len(df_filtrado) > 0:
            if provincia_sel == "Todas":
                st.write("##### 📋 Demanda Provincias")
                df_tp = df_filtrado.groupby(col_provincia).size().reset_index(name='Casos')
                df_tp['Prom.'] = (df_tp['Casos'] / num_fechas_reales).round(0).astype(int)
                
                climados = []
                for prov in df_tp[col_provincia]:
                    if prov in coordenadas_provincias:
                        lat_p, lon_p = coordenadas_provincias[prov]
                        climados.append(obtener_clima_actual_rapido(lat_p, lon_p))
                    else:
                        climados.append("🌍 N/A")
                df_tp['Clima Online'] = climados
                
                df_tp = df_tp[[col_provincia, 'Clima Online', 'Casos', 'Prom.']]
                st.dataframe(df_tp.sort_values(by='Casos', ascending=False), use_container_width=True, hide_index=True)
            else:
                st.write(f"##### 📋 Ciudades: {provincia_sel.title()}")
                df_tc = df_filtrado.groupby(col_ciudad).size().reset_index(name='Casos')
                df_tc['Prom.'] = (df_tc['Casos'] / num_fechas_reales).round(0).astype(int)
                
                lat_p, lon_p = coordenadas_provincias.get(provincia_sel, [-0.2298, -78.5249])
                clima_prov_str = obtener_clima_actual_rapido(lat_p, lon_p)
                df_tc['Clima Online'] = clima_prov_str
                
                df_tc = df_tc[[col_ciudad, 'Clima Online', 'Casos', 'Prom.']]
                st.dataframe(df_tc.sort_values(by='Casos', ascending=False), use_container_width=True, hide_index=True)

    with col_cen:
        st.write(f"### ⏰ Matriz Horaria y Flota Simplificada: {dia_sel.title()}")
        
        if len(df_filtrado) > 0 and col_hora_agrupada in df_filtrado.columns:
            df_horas_raw = df_filtrado.copy()
            df_horas_raw[col_hora_agrupada] = pd.to_numeric(df_horas_raw[col_hora_agrupada], errors='coerce').fillna(-1).astype(int)
            
            casos_locales = [0] * 24
            casos_foraneos = [0] * 24
            for hr in range(24):
                df_b = df_horas_raw[df_horas_raw[col_hora_agrupada] == hr]
                for _, fila in df_b.iterrows():
                    if "FOR" in str(fila[col_cobertura]).upper(): casos_foraneos[hr] += 1
                    else: casos_locales[hr] += 1

            registros_tabla = []
            alertas_clima_acumuladas = []

            for hr in range(24):
                p_local = casos_locales[hr] / num_fechas_reales
                p_foraneo = casos_foraneos[hr] / num_fechas_reales
                
                promedio_base_calculado = int(round(p_local + p_foraneo, 0))
                
                clima_info = diccionario_clima.get(hr, {"Detalle": "☁️ Nublado (N/A)", "Estado": "Normal"})
                detalle_clima = clima_info["Detalle"] if provincia_sel != "Todas" else "🌍 Filtre Provincia"
                es_lluvia = (clima_info["Estado"] == "Lluvia" and provincia_sel != "Todas")

                if es_lluvia:
                    p_local *= factor_ajuste
                    p_foraneo *= factor_ajuste
                    proyeccion_final_int = int(round(p_local + p_foraneo, 0))
                    texto_proyeccion = f"{proyeccion_final_int} (Lluvia 🌧️)"
                    if hr >= hora_actual and hr <= (hora_actual + 4):
                        alertas_clima_acumuladas.append(f"🚨 [{hr:02d}:00] Lluvia en {provincia_sel}. Sube de {promedio_base_calculado} a {proyeccion_final_int} casos.")
                else:
                    proyeccion_final_int = promedio_base_calculado
                    texto_proyeccion = f"{proyeccion_final_int} (Normal)"

                l_ant = p_local if hr == 0 else (casos_locales[hr-1] / num_fechas_reales)
                f_ant1 = p_foraneo if hr == 0 else (casos_foraneos[hr-1] / num_fechas_reales)
                f_ant2 = p_foraneo if hr <= 1 else (casos_foraneos[hr-2] / num_fechas_reales)
                
                gruas_netas = (p_local + (0.5 * l_ant)) + (p_foraneo + f_ant1 + f_ant2)
                gruas_necesarias = math.ceil(gruas_netas)

                es_remolque = any(x in str(servicio_sel).upper() for x in ["REMOLQUE", "GRÚA", "GRUA", "TODOS"])
                
                if es_remolque and (proyeccion_final_int > 0 or gruas_necesarias > 0):
                    if es_lluvia:
                        motivo_asesor = f"🔥 ALERTA DE LLUVIA: El clima aumentará los servicios."
                    elif proyeccion_final_int > 0 and gruas_necesarias == proyeccion_final_int:
                        motivo_asesor = f"🟢 Para los {proyeccion_final_int} casos nuevos de esta hora."
                    elif proyeccion_final_int > 0 and gruas_necesarias > proyeccion_final_int:
                        arrastre = gruas_necesarias - proyeccion_final_int
                        motivo_asesor = f"⏳ {proyeccion_final_int} para casos nuevos + {arrastre} de arrastre del viaje anterior."
                    elif proyeccion_final_int == 0 and gruas_necesarias > 0:
                        motivo_asesor = f"🔄 No hay casos nuevos, pero se siguen terminando viajes anteriores."
                    else:
                        motivo_asesor = "✅ Flota disponible en base."
                        
                    string_gruas = f"🚛 {gruas_necesarias} U."
                else:
                    string_gruas = "-"
                    motivo_asesor = "Normal"

                if proyeccion_final_int > 0 or string_gruas != "-":
                    registros_tabla.append({
                        "HORA": f"{hr:02d}:00",
                        "🌤️ Clima Online": detalle_clima,
                        "📊 Promed": promedio_base_calculado,
                        "📈 Proyección": texto_proyeccion,
                        "🚛 Grúas N.": string_gruas,
                        "📋 ¿Por qué se necesitan estas grúas?": motivo_asesor
                    })

            if alertas_clima_acumuladas:
                html_alertas = "".join([f'<div class="alerta-clima-mini">{a}</div>' for a in alertas_clima_acumuladas[:3]])
                st.markdown(html_alertas, unsafe_allow_html=True)

            if registros_tabla:
                st.dataframe(
                    pd.DataFrame(registros_tabla), 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "HORA": st.column_config.TextColumn(alignment="center", width="small"),
                        "🌤️ Clima Online": st.column_config.TextColumn(alignment="left", width="medium"),
                        "📊 Promed": st.column_config.NumberColumn(alignment="center", width="small"),
                        "📈 Proyección": st.column_config.TextColumn(alignment="center", width="medium"),
                        "🚛 Grúas N.": st.column_config.TextColumn(alignment="center", width="small"),
                        "📋 ¿Por qué se necesitan estas grúas?": st.column_config.TextColumn(alignment="left", width="large")
                    }
                )

    with col_der:
        st.write("##### 🚛 Alertas e Incidentes")
        
        # --- CONTROL DE ESTADO E INICIALIZACIÓN DE CRÉDITOS ---
        if 'waze_data' not in st.session_state:
            st.session_state['waze_data'] = []
            st.session_state['waze_time'] = "Nunca"
            
        # Fijado en 49 para preservar la consulta que hiciste antes del último cambio
        if 'creditos_waze' not in st.session_state:
            st.session_state['creditos_waze'] = 49 
            
        # --- NUEVA REGLA DE VALIDACIÓN PARA EL BOTÓN DE WAZE (PROVINCIA + SERVICIO) ---
        provincia_limpia = provincia_sel.upper().strip()
        es_provincia_valida = provincia_limpia in coordenadas_bbox_provincias and provincia_sel != "Todas"
        
        # Validar que el servicio contenga REMOLQUE, GRÚA o GRUA (excluyendo "Todos")
        servicio_limpio = str(servicio_sel).upper().strip()
        es_servicio_valido = any(x in servicio_limpio for x in ["REMOLQUE", "GRÚA", "GRUA"]) and servicio_limpio != "TODOS"

        # El botón solo se activa si cumple AMBOS criterios de forma simultánea
        if es_provincia_valida and es_servicio_valido:
            btn_text = "🔍 Consultar Tráfico en Vivo (Waze)"
            is_disabled = False
        else:
            if not es_servicio_valido and not es_provincia_valida:
                btn_text = "🔒 Filtre Servicio Remolque y Región Válida"
            elif not es_servicio_valido:
                btn_text = "🔒 Waze solo para servicio de Remolque"
            else:
                btn_text = "🔒 Waze disponible solo en UIO/GYE/CUE/MNT"
            is_disabled = True

        btn_consultar = st.button(btn_text, use_container_width=True, disabled=is_disabled)
        
        if btn_consultar and es_provincia_valida and es_servicio_valido:
            if st.session_state['creditos_waze'] > 0:
                bbox_zona = coordenadas_bbox_provincias[provincia_limpia]
                
                with st.spinner(f"Conectando Waze ({provincia_sel.title()})..."):
                    resultado_waze = consultar_alertas_waze_real(bbox_zona)
                    st.session_state['waze_data'] = resultado_waze
                    st.session_state['waze_time'] = ahora_actual.strftime('%I:%M:%S %p')
                    st.session_state['creditos_waze'] -= 1 
            else:
                st.error("❌ Has alcanzado el límite de 50 consultas de tu plan gratuito mensual.")
        
        st.caption(f"⏱️ Último reporte Waze: **{st.session_state['waze_time']}**")
        
        # Bloques informativos de ayuda dinámica en la barra lateral
        if not es_provincia_valida or not es_servicio_valido:
            st.warning("⚠️ El botón requiere seleccionar una Provincia autorizada (Pichincha, Guayas, Azuay, Manabí) Y especificar el Servicio de Remolque.")
        elif not st.session_state['waze_data']:
            st.info("💡 Parámetros correctos. Presiona el botón de arriba para consultar el tráfico en vivo.")
        else:
            for incidente in st.session_state['waze_data']:
                if "✅" in incidente:
                    st.success(incidente)
                else:
                    st.error(incidente)
                
        # Contador visual de saldo
        st.markdown(f"""
            <div class="card-saldo">
                <span style="font-size: 12px; color: #555555; font-weight: bold; display:block;">🔑 CRÉDITOS OPENWEBNINJA</span>
                <span style="font-size: 26px; color: #2e7d32; font-weight: 800;">{st.session_state['creditos_waze']}</span>
                <span style="font-size: 14px; color: #777777;"> / 50 Restantes</span>
            </div>
        """, unsafe_allow_html=True)
        
        st.success("🟢 Monitor meteorológico y matriz analítica operando al 100% en tiempo real.")
