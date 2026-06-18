import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import math
import time

# 1. Configuración de pantalla ultra ancha para el monitor de control
st.set_page_config(
    layout="wide", 
    page_title="Monitor de Proyecciones 2026 - Control de Flota",
    initial_sidebar_state="collapsed"
)

# Estilos CSS corporativos y tamaño de letra optimizado para pantallas de control y móviles
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDataFrame [data-testid="stDataFrameDownloadButton"] {display: none;}
    button[title="View fullscreen"] {display: none;}
    
    /* Margen corregido para optimizar espacio */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
        margin-top: 0px !important;
    }
    
    /* Reducción de márgenes internos de tablas para máxima compactación */
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
    
    /* Alertas de clima ultra compactas para evitar que empujen la tabla */
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
    </style>
    """, unsafe_allow_html=True)

# --- CONTROL DEL TEMPORIZADOR Y HORA ESTÁT ---
zona_ecuador = ZoneInfo("America/Guayaquil")
ahora_actual = datetime.now(zona_ecuador)

if "ultima_actualizacion" not in st.session_state:
    st.session_state.ultima_actualizacion = ahora_actual
if "proxima_actualizacion" not in st.session_state:
    st.session_state.proxima_actualizacion = ahora_actual + timedelta(minutes=5)

if ahora_actual >= st.session_state.proxima_actualizacion:
    st.session_state.ultima_actualizacion = ahora_actual
    st.session_state.proxima_actualizacion = ahora_actual + timedelta(minutes=5)

hora_estatica_str = st.session_state.ultima_actualizacion.strftime('%I:%M:%S %p')

st.title("🔮 Monitor de Proyección Horaria y Alerta Temprana de Flota")
st.caption(f"Centro de Control Geoanalítico | 🔄 Auto-refresco activo cada 5 min (Último: {hora_estatica_str})")

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

# 🚗 CLIMA EN VIVO
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

# 🛰️ WAZE ALERTAS EN VIVO
@st.cache_data(ttl=60)
def obtener_alertas_waze_Ecuador_completo():
    url_waze = "https://www.waze.com/row-rtserver/web/getStreetUniqueAlerts?top=1.45&bottom=-5.01&left=-81.11&right=-75.19"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.waze.com/live-map/"
    }
    incidentes_nacionales = []
    incidentes_provinciales = {
        "PICHINCHA": [], "GUAYAS": [], "AZUAY": [], "MANABI": [], "MANABÍ": [], "LOS RIOS": [], "LOS RÍOS": [],
        "TUNGURAHUA": [], "EL ORO": [], "LOJA": [], "CHIMBORAZO": [], "COTOPAXI": [], "ESMERALDAS": [],
        "SANTO DOMINGO DE LOS TSÁCHILAS": [], "SANTO DOMINGO DE LOS TSACHILAS": [], "SANTA ELENA": [], "IMBABURA": []
    }
    try:
        respuesta = requests.get(url_waze, headers=headers, timeout=10).json()
        alertas = respuesta.get("alerts", [])
        zona_ec = ZoneInfo("America/Guayaquil")
        for al in alertas:
            calle = al.get("street", "Vía no identificada")
            tipo = al.get("type", "TRÁFICO")
            subtipo = al.get("subType", "")
            descripcion = al.get("reportDescription", "")
            millis = al.get("pubMillis", 0)
            if millis > 0:
                dt_ec = datetime.fromtimestamp(millis / 1000.0, tz=ZoneInfo("UTC")).astimezone(zona_ec)
                tiempo_str = dt_ec.strftime("%d/%m %I:%M %p")
            else:
                tiempo_str = "Hora no disp."
            tipo_legible = subtipo.replace("_", " ").title() if subtipo else tipo.title()
            icono = "💥" if "ACCIDENT" in tipo or "COLLISION" in tipo else "⚠️"
            detalles = f" ({descripcion})" if descripcion else ""
            texto_alerta = f"{icono} **[{tiempo_str}]** {calle}: {tipo_legible}{detalles}."
            
            if any(pe in calle.upper() for pe in ["VIA", "VÍA", "PANAMERICANA", "ALOAG", "ALÓAG", "E35", "E25", "E45"]):
                incidentes_nacionales.append(texto_alerta)
            calle_up = calle.upper()
            if any(pq in calle_up for pq in ["QUITO", "SIMON BOLIVAR", "SIMÓN BOLÍVAR", "CUMBAYA"]):
                incidentes_provinciales["PICHINCHA"].append(texto_alerta)
            elif any(pg in calle_up for pg in ["GUAYAQUIL", "JUAN TANCA", "SAMANES", "DAULE", "SAMBORONDON"]):
                incidentes_provinciales["GUAYAS"].append(texto_alerta)
            elif any(pa in calle_up for pa in ["CUENCA", "ORDONEZ LASSO"]):
                incidentes_provinciales["AZUAY"].append(texto_alerta)
            elif any(pm in calle_up for pm in ["MANTA", "PORTOVIEJO"]):
                incidentes_provinciales["MANABI"].append(texto_alerta)
        if not incidentes_nacionales:
            incidentes_nacionales = ["✅ **[WAZE]** Ejes principales estables."]
        return incidentes_nacionales, incidentes_provinciales
    except:
        return ["⚠️ **[WAZE]** Sincronizando flujo..."], incidentes_provinciales

# 📊 FACTOR LLUVIA
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
    f1, f2, f3, f4, f5 = st.columns([2, 2, 2, 3, 2])
    
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
        estado_sel = st.selectbox("📌 Filtrar por Estado:", ["Todos"] + list(df_raw[col_estado].dropna().unique())) if col_estado in df_raw.columns else "Todos"

    if dia_sel.upper() == "TODOS":
        df_dia_especifico = df_raw.copy()
        num_fechas_reales = df_dia_especifico[col_fecha].nunique() if col_fecha in df_dia_especifico.columns else 1
        fecha_target_str = st.session_state.ultima_actualizacion.strftime("%Y-%m-%d")
        dias_diferencia = 0
    else:
        dia_destino_num = diccionario_dias.get(dia_sel.upper(), st.session_state.ultima_actualizacion.weekday())
        dias_diferencia = (dia_destino_num - st.session_state.ultima_actualizacion.weekday()) % 7
        fecha_target_str = (st.session_state.ultima_actualizacion + timedelta(days=dias_diferencia)).strftime("%Y-%m-%d")
        df_dia_especifico = df_raw[df_raw[col_dia].str.upper() == dia_sel.upper()]
        num_fechas_reales = df_dia_especifico[col_fecha].nunique() if col_fecha in df_dia_especifico.columns else 1

    if num_fechas_reales <= 0: num_fechas_reales = 1

    df_filtrado = df_dia_especifico.copy()
    if estado_sel != "Todos" and col_estado in df_raw.columns: df_filtrado = df_filtrado[df_filtrado[col_estado] == estado_sel]
    if servicio_sel != "Todos": df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
    if provincia_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado[col_provincia] == provincia_sel]
        if ciudad_sel: df_filtrado = df_filtrado[df_filtrado[col_ciudad].isin(ciudad_sel)]

    hora_actual = st.session_state.ultima_actualizacion.hour
    if provincia_sel != "Todas":
        lat_c, lon_c = coordenadas_provincias.get(provincia_sel, [-0.2298, -78.5249])
        diccionario_clima = obtener_clima_horario_futuro(lat_c, lon_c, fecha_target_str)
        factor_ajuste = calcular_factor_lluvia_en_vivo(df_filtrado, lat_c, lon_c)
    else:
        diccionario_clima, factor_ajuste = {}, 1.0

    st.markdown("---")
    
    # 🌟 NUEVA ASIGNACIÓN DE COLUMNAS: Izquierda pequeña (2.8), Centro ancha (6.7), Derecha pequeña (2.5)
    col_izq, col_cen, col_der = st.columns([2.8, 6.7, 2.5])
    
    with col_izq:
        promedio_asistencias_dia = int(round(len(df_filtrado) / num_fechas_reales, 0))
        st.metric(label=f"📊 Promedio ({dia_sel.title()})", value=f"{promedio_asistencias_dia} Asist.")
        
        if len(df_filtrado) > 0:
            if provincia_sel == "Todas":
                st.write("##### 📋 Demanda Provincias")
                df_tp = df_filtrado.groupby(col_provincia).size().reset_index(name='Casos')
                df_tp['Prom.'] = (df_tp['Casos'] / num_fechas_reales).round(0).astype(int)
                st.dataframe(df_tp.sort_values(by='Casos', ascending=False), use_container_width=True, hide_index=True)
            else:
                st.write(f"##### 📋 Ciudades: {provincia_sel.title()}")
                df_tc = df_filtrado.groupby(col_ciudad).size().reset_index(name='Casos')
                df_tc['Prom.'] = (df_tc['Casos'] / num_fechas_reales).round(0).astype(int)
                st.dataframe(df_tc.sort_values(by='Casos', ascending=False), use_container_width=True, hide_index=True)

    with col_cen:
        st.write(f"### ⏰ Matriz Horaria y Flota Simplificada: {dia_sel.title()}")
        
        # --- SECCIÓN DE ALERTAS ULTRA COMPACTAS ---
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
                base_total_combinado = int(round(p_local + p_foraneo, 0))
                
                clima_info = diccionario_clima.get(hr, {"Detalle": "☁️ Nublado (N/A)", "Estado": "Normal"})
                detalle_clima = clima_info["Detalle"] if provincia_sel != "Todas" else "🌍 Seleccione Prov."
                es_lluvia = (clima_info["Estado"] == "Lluvia" and provincia_sel != "Todas")

                if es_lluvia:
                    p_local *= factor_ajuste
                    p_foraneo *= factor_ajuste
                    total_ajustado_int = int(round(p_local + p_foraneo, 0))
                    # Guardamos la alerta compacta si es del bloque operativo relevante
                    if hr >= hora_actual and hr <= (hora_actual + 4):
                        alertas_clima_acumuladas.append(f"🚨 [{hr:02d}:00] Lluvia en {provincia_sel}. Sube a {total_ajustado_int} casos.")
                    base_total_combinado = total_ajustado_int

                # FÓRMULA DE OPERACIÓN CON ARRASTRE
                l_ant = p_local if hr == 0 else (casos_locales[hr-1] / num_fechas_reales)
                f_ant1 = p_foraneo if hr == 0 else (casos_foraneos[hr-1] / num_fechas_reales)
                f_ant2 = p_foraneo if hr <= 1 else (casos_foraneos[hr-2] / num_fechas_reales)
                
                gruas_netas = (p_local + (0.5 * l_ant)) + (p_foraneo + f_ant1 + f_ant2)
                gruas_necesarias = math.ceil(gruas_netas)

                es_remolque = any(x in str(servicio_sel).upper() for x in ["REMOLQUE", "GRÚA", "GRUA", "TODOS"])
                
                if es_remolque and (base_total_combinado > 0 or gruas_necesarias > 0):
                    if es_lluvia:
                        motivo_asesor = f"🔥 ALERTA DE LLUVIA: El clima aumentará los servicios."
                    elif base_total_combinado > 0 and gruas_necesarias == base_total_combinado:
                        motivo_asesor = f"🟢 Para los {base_total_combinado} casos nuevos de esta hora."
                    elif base_total_combinado > 0 and gruas_necesarias > base_total_combinado:
                        arrastre = gruas_necesarias - base_total_combinado
                        motivo_asesor = f"⏳ {base_total_combinado} para casos nuevos + {arrastre} de arrastre del viaje anterior."
                    elif base_total_combinado == 0 and gruas_necesarias > 0:
                        motivo_asesor = f"🔄 No hay casos nuevos, pero se siguen terminando viajes anteriores."
                    else:
                        motivo_asesor = "✅ Flota disponible en base."
                        
                    string_gruas = f"🚛 {gruas_necesarias} U."
                else:
                    string_gruas = "-"
                    motivo_asesor = "Normal"

                if base_total_combinado > 0 or string_gruas != "-":
                    registros_tabla.append({
                        "HORA": f"{hr:02d}:00",
                        "🌤️ Clima Online": detalle_clima,
                        "🚗 Casos Nuevos": base_total_combinado,
                        "🚛 Grúas Necesarias": string_gruas,
                        "📋 ¿Por qué se necesitan estas grúas?": motivo_asesor
                    })

            # Render de alertas en formato ultra compacto (HTML nativo liviano)
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
                        "🚗 Casos Nuevos": st.column_config.NumberColumn(alignment="center", width="small"),
                        "🚛 Grúas Necesarias": st.column_config.TextColumn(alignment="center", width="small"),
                        "📋 ¿Por qué se necesitan estas grúas?": st.column_config.TextColumn(alignment="left", width="large")
                    }
                )

    with col_der:
        st.write("##### 🛰️ Tráfico Waze")
        inc_nac, inc_prov = obtener_alertas_waze_Ecuador_completo()
        
        st.markdown("🔗 **Troncales:**")
        for al in inc_nac[:2]: st.warning(al)
            
        prov_up = provincia_sel.upper()
        st.markdown(f"📍 **{provincia_sel.title()}:**")
        alertas_locales = inc_prov.get(prov_up, []) if provincia_sel != "Todas" else [al for l in inc_prov.values() for al in l]
        
        if alertas_locales:
            for al in alertas_locales[:3]: st.error(al) if "💥" in al else st.info(al)
        else:
            st.success("✅ Flujo estable.")

    # AUTOMATIZACIÓN DE AUTO-REFRESCO NATIVO
    time.sleep(1)
    if datetime.now(zona_ecuador) >= st.session_state.proxima_actualizacion:
        st.rerun()
