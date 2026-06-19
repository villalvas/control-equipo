import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import math
import streamlit.components.v1 as components
import plotly.graph_objects as go

# 1. Configuración de pantalla completa y compacta para salas de control
st.set_page_config(
    layout="wide", 
    page_title="Monitor de Proyecciones 2026 - Control de Flota",
    initial_sidebar_state="expanded"
)

# --- RECARGA NATIVA FORZADA DE VENTANA CADA 15 MINUTOS ---
components.html(
    """
    <script>
        setTimeout(function(){
            window.parent.location.reload();
        }, 900000);
    </script>
    """,
    height=0,
    width=0
)

# Estilos CSS radicales para compactar todo el Dashboard en 1 sola pantalla sin scroll
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDataFrame [data-testid="stDataFrameDownloadButton"] {display: none;}
    button[title="View fullscreen"] {display: none;}
    
    /* Forzado de márgenes cero para evitar scroll general */
    .block-container {
        padding-top: 0.2rem !important;
        padding-bottom: 0.1rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        margin-top: 0px !important;
    }
    
    /* Celdas de tablas ultra compactas */
    [data-testid="stTable"] td, [data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] [role="gridcell"] {
        font-size: 11px !important;
        font-weight: 500 !important;
        padding: 1px 3px !important;
    }
    [data-testid="stTable"] th, [data-testid="stDataFrame"] th, div[data-testid="stDataFrame"] [role="columnheader"] {
        font-size: 11px !important;
        font-weight: bold !important;
        padding: 2px 3px !important;
    }
    
    .card-saldo {
        background-color: #f0f7f4;
        border: 1px solid #d2e7de;
        padding: 2px 4px;
        border-radius: 4px;
        text-align: center;
        margin-top: 1px;
    }
    .banner-feriado {
        background-color: #fff8e1;
        border-left: 5px solid #ffb300;
        padding: 4px;
        border-radius: 4px;
        margin-bottom: 4px;
        font-weight: 500;
        font-size: 11px;
    }
    .banner-similitud {
        background-color: #e3f2fd;
        border-left: 5px solid #2196f3;
        padding: 4px;
        border-radius: 4px;
        margin-bottom: 4px;
        font-weight: 500;
        font-size: 11px;
        color: #0d47a1;
    }
    div[data-testid="stVerticalBlock"] > div {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
        gap: 0px !important;
    }
    div[data-testid="stSelectbox"] label, div[data-testid="stMultiSelect"] label {
        font-size: 11px !important;
        margin-bottom: 2px !important;
        padding-bottom: 0px !important;
    }
    div[data-testid="stSelectbox"] > div, div[data-testid="stMultiSelect"] > div {
        padding: 0px !important;
        min-height: 26px !important;
    }
    </style>
    """, unsafe_allow_html=True)

zona_ecuador = ZoneInfo("America/Guayaquil")
ahora_actual = datetime.now(zona_ecuador)
hora_estatica_str = ahora_actual.strftime('%I:%M:%S %p')

# --- MEMORIA SERVIDOR ALTA DISPONIBILIDAD ---
@st.cache_resource
def inicializar_memoria_inmune():
    return {
        "historico_alertas": [], 
        "ultima_consulta_tomtom": "Nunca",
        "filtros_normal": {
            "dia_sel": "TODOS",
            "servicio_sel": "Todos",
            "provincia_sel": "Todas",
            "ciudad_sel": [],
            "estado_sel": []
        },
        "filtros_feriados": {
            "feriado_sel": "Carnaval",
            "servicio_sel": "REMOLQUE DE AUTOMOVIL ( GRUA )",
            "provincia_sel": "Todas",
            "ciudad_sel": []
        }
    }

estado_global = inicializar_memoria_inmune()

# --- FUNCIÓN DE CONSULTA REAL (TOMTOM) ---
def ejecutar_consulta_tomtom():
    # AGREGA TU KEY GRATUITA DE TOMTOM DEVELOPER AQUÍ
    TOMTOM_API_KEY = "TU_API_KEY_DE_TOMTOM"
    
    if TOMTOM_API_KEY == "TU_API_KEY_DE_TOMTOM":
        estado_global["ultima_consulta_tomtom"] = datetime.now(zona_ecuador).strftime('%I:%M:%S %p')
        return
        
    bbox_ecuador = "-81.0000,-5.0000,-75.0000,1.5000"
    try:
        url = f"https://api.tomtom.com/traffic/services/4/incidentDetails/s3/{bbox_ecuador}/11/-1/json"
        params = {"key": TOMTOM_API_KEY, "geometries": "false", "language": "es-ES"}
        respuesta = requests.get(url, params=params, timeout=8).json()
        
        if "tm" in respuesta and "poi" in respuesta["tm"]:
            # Limpiar historial previo para la consulta manual fresca
            estado_global["historico_alertas"] = []
            
            for incidente in respuesta["tm"]["poi"]:
                descripcion = incidente.get("d", "Incidente")
                calle = incidente.get("f", "Vía")
                magnitud = incidente.get("ic", 1)
                
                prov_detectada = "TODAS"
                listado_provincias = ['PICHINCHA', 'GUAYAS', 'AZUAY', 'MANABI', 'EL ORO', 'LOJA', 'LOS RIOS', 'SANTA ELENA', 'TUNGURAHUA']
                for p in listado_provincias:
                    if p in descripcion.upper() or p in calle.upper():
                        prov_detectada = p
                        break
                
                iconos = {1: "⚠️", 2: "🚗 Tráfico", 3: "💥 Choque", 4: "🚫 Vía Cerrada"}
                txt_final = f"{iconos.get(magnitud, '⚠️')} | {calle}: {descripcion}"
                h_reporte = datetime.now(zona_ecuador).strftime('%I:%M %p')
                
                estado_global["historico_alertas"].append({
                    "hora": h_reporte,
                    "provincia": prov_detectada,
                    "texto": txt_final
                })
            
            estado_global["historico_alertas"] = estado_global["historico_alertas"][:30]
        estado_global["ultima_consulta_tomtom"] = datetime.now(zona_ecuador).strftime('%I:%M:%S %p')
    except:
        pass

st.markdown(f"<h2 style='margin:0px; padding:0px; font-size:26px;'>🔮 Proyección Horaria y Alerta de Flota</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='margin:0px 0px 6px 0px; font-size:11px; color:#555;'><b>Control Geoanalítico</b> | 🔄 Memoria Inmune Activa (Última Actualización: {hora_estatica_str})</p>", unsafe_allow_html=True)

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

@st.cache_data(ttl=900)
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
                datos_clima[hora_int] = {"Detalle": f"{icono} {temp}°C", "Estado": estado}
        return datos_clima
    except: return {}

@st.cache_data(ttl=900)
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
    df_raw[col_fecha] = df_raw[col_fecha].astype(str).str.strip().str.split().str[0]

    if col_hora_agrupada in df_raw.columns:
        df_raw[col_hora_agrupada] = df_raw[col_hora_agrupada].apply(lambda val: int(str(val).strip().split(':')[0]) if ":" in str(val) else (int(str(val).split('.')[0]) if str(val).split('.')[0].isdigit() else -1))

    tab_normal, tab_feriados = st.tabs(["🔮 Operación Diaria (Normal)", "📈 Planificador de Feriados"])

    with tab_normal:
        col_sidebar, col_main_content = st.columns([1.6, 8.4])
        
        if "dia_sel_key" not in st.session_state: st.session_state["dia_sel_key"] = estado_global["filtros_normal"]["dia_sel"]
        if "servicio_sel_key" not in st.session_state: st.session_state["servicio_sel_key"] = estado_global["filtros_normal"]["servicio_sel"]
        if "provincia_sel_key" not in st.session_state: st.session_state["provincia_sel_key"] = estado_global["filtros_normal"]["provincia_sel"]
        if "ciudad_sel_key" not in st.session_state: st.session_state["ciudad_sel_key"] = estado_global["filtros_normal"]["ciudad_sel"]
        if "estado_sel_key" not in st.session_state: st.session_state["estado_sel_key"] = estado_global["filtros_normal"]["estado_sel"]

        def guardar_dia_callback(): estado_global["filtros_normal"]["dia_sel"] = st.session_state["dia_sel_key"]
        def guardar_servicio_callback(): estado_global["filtros_normal"]["servicio_sel"] = st.session_state["servicio_sel_key"]
        def guardar_provincia_callback():
            estado_global["filtros_normal"]["provincia_sel"] = st.session_state["provincia_sel_key"]
            estado_global["filtros_normal"]["ciudad_sel"] = []
            st.session_state["ciudad_sel_key"] = []
        def guardar_ciudad_callback(): estado_global["filtros_normal"]["ciudad_sel"] = st.session_state["ciudad_sel_key"]
        def guardar_estado_callback(): estado_global["filtros_normal"]["estado_sel"] = st.session_state["estado_sel_key"]

        with col_sidebar:
            st.markdown("<h4 style='margin:0px; font-size:14px; color:#111;'>⚙️ Filtros</h4>", unsafe_allow_html=True)
            dias_en_orden = ["TODOS", "LUNES", "MARTES", "MIÉRCOLES", "MIERCOLES", "JUEVES", "VIERNES", "SÁBADO", "SABADO", "DOMINGO"]
            dias_disponibles = [d for d in dias_en_orden if d == "TODOS" or d in list(df_raw[col_dia].str.upper().unique())]
            dia_sel = st.selectbox("📅 Día Tipo:", dias_disponibles, key="dia_sel_key", on_change=guardar_dia_callback)
            
            lista_servicios = ["Todos"] + sorted(list(df_raw[col_servicio].dropna().unique()))
            servicio_sel = st.selectbox("🎯 Servicio:", lista_servicios, key="servicio_sel_key", on_change=guardar_servicio_callback)
            
            provincia_sel = st.selectbox("📍 Provincia:", ["Todas"] + df_raw[col_provincia].value_counts().index.tolist(), key="provincia_sel_key", on_change=guardar_provincia_callback)
            
            if provincia_sel != "Todas":
                ciudades_disponibles = sorted(df_raw[df_raw[col_provincia] == provincia_sel][col_ciudad].dropna().unique().tolist())
                ciudad_sel = st.multiselect("🏙️ Ciudades:", ciudades_disponibles, key="ciudad_sel_key", on_change=guardar_ciudad_callback)
            else:
                ciudad_sel = st.multiselect("🏙️ Ciudades:", options=[], disabled=True, placeholder="Filtre Provincia")
                
            if col_estado in df_raw.columns:
                estados_disponibles = sorted(list(df_raw[col_estado].dropna().unique()))
                estado_sel = st.multiselect("📌 Estado:", options=estados_disponibles, key="estado_sel_key", on_change=guardar_estado_callback)
            else: estado_sel = []

            st.markdown("<div style='margin-top: 15px; border-top: 1px dashed #ccc; padding-top: 10px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 REBOOT APP", use_container_width=True, key="btn_reboot_sidebar"):
                st.cache_data.clear()
                st.cache_resource.clear()
                st.rerun()

        if dia_sel.upper() == "TODOS":
            df_filtrado_dia = df_raw.copy()
            num_fechas_reales = df_raw[col_fecha].nunique() if col_fecha in df_raw.columns else 1
            fecha_target_str = ahora_actual.strftime("%Y-%m-%d")
        else:
            dia_destino_num = diccionario_dias.get(dia_sel.upper(), ahora_actual.weekday())
            dias_diferencia = (dia_destino_num - ahora_actual.weekday()) % 7
            fecha_target_str = (ahora_actual + timedelta(days=dias_diferencia)).strftime("%Y-%m-%d")
            df_filtrado_dia = df_raw[df_raw[col_dia].str.upper() == dia_sel.upper()]
            num_fechas_reales = df_filtrado_dia[col_fecha].nunique() if col_fecha in df_filtrado_dia.columns else 1

        if num_fechas_reales <= 0: num_fechas_reales = 1

        df_filtrado = df_filtrado_dia.copy()
        if estado_sel and col_estado in df_raw.columns: df_filtrado = df_filtrado[df_filtrado[col_estado].isin(estado_sel)]
        if servicio_sel != "Todos": df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
        if provincia_sel != "Todas":
            df_filtrado = df_filtrado[df_filtrado[col_provincia] == provincia_sel]
            if ciudad_sel: df_filtrado = df_filtrado[df_filtrado[col_ciudad].isin(ciudad_sel)]

        provincia_key_busqueda = provincia_sel.upper().strip()
        if provincia_sel != "Todas" and provincia_key_busqueda in coordenadas_provincias:
            lat_c, lon_c = coordenadas_provincias[provincia_key_busqueda]
            diccionario_clima = obtener_clima_horario_futuro(lat_c, lon_c, fecha_target_str)
        else:
            diccionario_clima = {}

        registros_tabla = []
        data_grafico_lineas = []

        if len(df_filtrado) > 0 and col_hora_agrupada in df_filtrado.columns:
            df_horas_raw = df_filtrado.copy()
            
            casos_locales, casos_foraneos = [0] * 24, [0] * 24
            for hr in range(24):
                df_b = df_horas_raw[df_horas_raw[col_hora_agrupada] == hr]
                for _, fila in df_b.iterrows():
                    cobertura_str = str(fila[col_cobertura]).upper().strip() if col_cobertura in fila else "LOCAL"
                    if "FOR" in cobertura_str: casos_foraneos[hr] += 1
                    else: casos_locales[hr] += 1

            for hr in range(24):
                p_local, p_foraneo = casos_locales[hr] / num_fechas_reales, casos_foraneos[hr] / num_fechas_reales
                promedio_base_calculado = round(p_local + p_foraneo, 1)
                
                clima_info = diccionario_clima.get(hr, {"Detalle": "☁️ Nublado", "Estado": "Normal"})
                detalle_clima = clima_info["Detalle"] if provincia_sel != "Todas" else "🌍 Filtre Prov."
                es_lluvia = clima_info["Estado"] == "Lluvia"

                if es_lluvia and promedio_base_calculado > 0:
                    promedio_proyectado = math.ceil(promedio_base_calculado * 1.20)
                    etiqueta_proyeccion = f"{promedio_proyectado} (+20%)"
                    p_local_calc = p_local * 1.20
                    p_foraneo_calc = p_foraneo * 1.20
                else:
                    promedio_proyectado = int(round(promedio_base_calculado, 0))
                    etiqueta_proyeccion = f"{promedio_proyectado} (Norm)"
                    p_local_calc = p_local
                    p_foraneo_calc = p_foraneo

                l_ant = p_local_calc if hr == 0 else (casos_locales[hr-1] / num_fechas_reales * (1.20 if es_lluvia else 1.0))
                f_ant1 = p_foraneo_calc if hr == 0 else (casos_foraneos[hr-1] / num_fechas_reales * (1.20 if es_lluvia else 1.0))
                f_ant2 = p_foraneo_calc if hr <= 1 else (casos_foraneos[hr-2] / num_fechas_reales * (1.20 if es_lluvia else 1.0))
                
                if promedio_proyectado == 0:
                    gruas_necesarias = math.ceil((0.1 * l_ant) + (0.2 * f_ant1) + (0.1 * f_ant2))
                else:
                    gruas_necesarias = math.ceil((p_local_calc + (0.5 * l_ant)) + (p_foraneo_calc + f_ant1 + f_ant2))
                    
                es_remolque = any(x in str(servicio_sel).upper() for x in ["REMOLQUE", "GRÚA", "GRUA", "TODOS"])
                string_gruas = f"🚛 {gruas_necesarias} U." if es_remolque and (promedio_proyectado > 0 or gruas_necesarias > 0) else "-"

                if promedio_base_calculado == 0 and gruas_necesarias == 0: motivo_asesor = "Sin demanda"
                else:
                    explicaciones = []
                    if promedio_proyectado > 0:
                        if es_lluvia: explicaciones.append(f"{promedio_proyectado} por lluvia")
                        else: explicaciones.append(f"{promedio_proyectado} nuevos")
                    if gruas_necesarias > promedio_proyectado: explicaciones.append("arrastre ant.")
                    motivo_asesor = " + ".join(explicaciones) if explicaciones else "Ok"

                registros_tabla.append({
                    "HORA": f"{hr:02d}:00", "🌤️ Clima": detalle_clima, "📊 Prom": promedio_base_calculado, 
                    "📈 Proy": etiqueta_proyeccion, "🚛 Grúas N.": string_gruas, "📋 Diagnóstico": motivo_asesor
                })
                
                data_grafico_lineas.append({
                    "Hora": hr, "Promedio Base": promedio_base_calculado, "Proyección Ajustada": promedio_proyectado
                })

        with col_main_content:
            col_mando_izq, col_mando_der = st.columns([4.2, 5.8])
            with col_mando_izq:
                st.markdown("<span style='font-size:12px; font-weight:bold; color:#111;'>📍 Top Localidades Afectadas</span>", unsafe_allow_html=True)
                if len(df_filtrado) > 0:
                    col_agrupar = col_provincia if provincia_sel == "Todas" else col_ciudad
                    df_top = df_filtrado.groupby(col_agrupar).agg(Total_Casos=('SERVICIO', 'count')).reset_index()
                    df_top['📊 Prom/Día'] = (df_top['Total_Casos'] / num_fechas_reales).round(0).astype(int)
                    df_top = df_top.rename(columns={col_agrupar: '📍 UBICACIÓN', 'Total_Casos': 'Casos'})
                    df_top = df_top.sort_values(by='Casos', ascending=False).head(5)
                    total_general_casos = df_filtrado.shape[0]
                    df_top['%'] = (df_top['Casos'] / total_general_casos * 100).round(1).astype(str) + '%' if total_general_casos > 0 else '0%'
                    df_top = df_top[['📍 UBICACIÓN', 'Casos', '📊 Prom/Día', '%']]
                    st.dataframe(df_top, use_container_width=True, height=140, hide_index=True)
                else: st.info("Sin datos.")

            with col_mando_der:
                st.markdown(f"<span style='font-size:12px; font-weight:bold; color:#111;'>⏰ Matriz Horaria Detallada: {dia_sel.title()}</span>", unsafe_allow_html=True)
                if registros_tabla: st.dataframe(pd.DataFrame(registros_tabla), use_container_width=True, height=140, hide_index=True)
                else: st.info("Sin asistencias.")

            st.markdown("<div style='margin-top: 4px; border-top: 1px solid #ddd; padding-top: 2px;'></div>", unsafe_allow_html=True)
            col_grafico_full, col_resumen_waze = st.columns([6.8, 3.2])
            
            with col_grafico_full:
                st.markdown("<span style='font-size:13px; font-weight:bold; display:block;'>📈 Curva de Carga Operativa (24 Horas)</span>", unsafe_allow_html=True)
                if data_grafico_lineas:
                    df_gl = pd.DataFrame(data_grafico_lineas)
                    fig_lineas = go.Figure()
                    fig_lineas.add_trace(go.Scatter(x=df_gl["Hora"], y=df_gl["Promedio Base"], name="📊 Promedio Base", mode="lines+markers", line=dict(color="#1f77b4", width=2)))
                    fig_lineas.add_trace(go.Scatter(x=df_gl["Hora"], y=df_gl["Proyección Ajustada"], name="📈 Proyección por Clima", mode="lines+markers", line=dict(color="#ff7f0e", width=2, dash="dash")))
                    fig_lineas.update_layout(
                        xaxis=dict(tickmode="linear", tick0=0, dtick=1, title=dict(text="Hora del Día", font=dict(size=10))),
                        yaxis=dict(title=dict(text="Incidentes / Asistencias", font=dict(size=10))),
                        margin=dict(l=5, r=5, t=5, b=5), height=150, showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9))
                    )
                    st.plotly_chart(fig_lineas, use_container_width=True, config={'displayModeBar': False})

            # =========================================================================
            # CAJA INFERIOR DERECHA: BOTÓN MANUAL PARA ADQUIRIR ALERTAS REALTIME 
            # =========================================================================
            with col_resumen_waze:
                promedio_asistencias_dia = int(round(len(df_filtrado) / num_fechas_reales, 0))
                st.markdown(f"<span style='font-size:11px; color:#555;'>Promedio ({dia_sel.title()})</span>", unsafe_allow_html=True)
                st.markdown(f"<h3 style='margin:0px; padding:0px; font-size:28px; line-height:1;'>{promedio_asistencias_dia} Asist.</h3>", unsafe_allow_html=True)
                
                st.markdown("<span style='font-size:11px; font-weight:bold; color:#1e88e5; display:block; margin-top:4px;'>🚛 Alertas Nacionales Realtime</span>", unsafe_allow_html=True)
                
                c_w1, c_w2 = st.columns([4.5, 5.5])
                with c_w1:
                    if provincia_sel == "Todas":
                        alertas_filtradas = estado_global["historico_alertas"]
                        etiqueta_cobertura = "Global"
                    else:
                        alertas_filtradas = [x for x in estado_global["historico_alertas"] if x["provincia"] == provincia_sel.upper().strip()]
                        etiqueta_cobertura = provincia_sel[:10]

                    st.markdown(f'<div class="card-saldo"><span style="font-size:9px;color:#444;">Filtro: <b>{etiqueta_cobertura}</b></span></div>', unsafe_allow_html=True)
                with c_w2:
                    st.markdown(f"<span style='font-size:9px; color:#777; display:block;'>Último: {estado_global['ultima_consulta_tomtom']}</span>", unsafe_allow_html=True)
                
                # Despliegue de los incidentes si existen
                if not alertas_filtradas:
                    st.markdown("<span style='font-size:9px; color:#999; display:block; margin-bottom:2px;'>• Rutas estables en la red nacional.</span>", unsafe_allow_html=True)
                else:
                    for incidente in alertas_filtradas[:2]:
                        st.markdown(f"<span style='font-size:9px; color:#d32f2f; font-weight:500; display:block; line-height:1.2;'>• {incidente['texto'][:35]}...</span>", unsafe_allow_html=True)
                
                # BOTÓN MANUAL EXACTAMENTE ABAJO DE LA CAJA ORIGINAL
                if st.button("🔄 CONSULTAR ALERTAS MANUALMENTE", use_container_width=True, key="btn_manual_tomtom"):
                    ejecutar_consulta_tomtom()
                    st.rerun()

    # Planificador de feriados (Sin cambios en su estructura)
    with tab_feriados:
        col_f_fer, col_c_fer = st.columns([1.6, 8.4])
        
        if "feriado_sel_key" not in st.session_state: st.session_state["feriado_sel_key"] = estado_global["filtros_feriados"]["feriado_sel"]
        if "servicio_fer_key" not in st.session_state: st.session_state["servicio_fer_key"] = estado_global["filtros_feriados"]["servicio_sel"]
        if "provincia_fer_key" not in st.session_state: st.session_state["provincia_fer_key"] = estado_global["filtros_feriados"]["provincia_sel"]
        if "ciudad_fer_key" not in st.session_state: st.session_state["ciudad_fer_key"] = estado_global["filtros_feriados"]["ciudad_sel"]

        def guardar_feriado_callback(): estado_global["filtros_feriados"]["feriado_sel"] = st.session_state["feriado_sel_key"]
        def guardar_servicio_fer_callback(): estado_global["filtros_feriados"]["servicio_sel"] = st.session_state["servicio_fer_key"]
        def guardar_provincia_fer_callback():
            estado_global["filtros_feriados"]["provincia_sel"] = st.session_state["provincia_fer_key"]
            estado_global["filtros_feriados"]["ciudad_sel"] = []
            st.session_state["ciudad_fer_key"] = []
        def guardar_ciudad_fer_callback(): estado_global["filtros_feriados"]["ciudad_sel"] = st.session_state["ciudad_fer_key"]

        with col_f_fer:
            st.markdown("<h4 style='margin:0px; font-size:14px; color:#111;'>⚙️ Planificador</h4>", unsafe_allow_html=True)
            config_maestra_feriados = {
                "Carnaval": {"fecha": "18/2/2026", "dias": 4, "espejo": None},
                "Año Nuevo": {"fecha": "5/1/2026", "dias": 3, "espejo": None},
                "Viernes Santo": {"fecha": "6/4/2026", "dias": 3, "espejo": None},
                "Día del Trabajo": {"fecha": "4/5/2026", "dias": 3, "espejo": None},
                "Batalla de Pichincha": {"fecha": "25/5/2026", "dias": 3, "espejo": None},
                "Primer Grito de Independencia": {"fecha": "10/8/2026", "dias": 3, "espejo": "Batalla de Pichincha"},
                "Independencia de Guayaquil": {"fecha": "12/10/2026", "dias": 3, "espejo": "Batalla de Pichincha"},
                "Día de los Difuntos / Cuenca": {"fecha": "4/11/2026", "dias": 4, "espejo": "Carnaval"},
                "Navidad": {"fecha": "28/12/2026", "dias": 3, "espejo": "Año Nuevo"}
            }
            feriado_seleccionado = st.selectbox("📅 Feriado Nacional:", list(config_maestra_feriados.keys()), key="feriado_sel_key", on_change=guardar_feriado_callback)
            servicio_feriado = st.selectbox("🎯 Servicio:", sorted(list(df_raw[col_servicio].dropna().unique())), key="servicio_fer_key", on_change=guardar_servicio_fer_callback)
            
            provincia_feriado = st.selectbox("📍 Provincia:", ["Todas"] + df_raw[col_provincia].value_counts().index.tolist(), key="provincia_fer_key", on_change=guardar_provincia_fer_callback)
            if provincia_feriado != "Todas":
                ciudades_f_disp = sorted(df_raw[df_raw[col_provincia] == provincia_feriado][col_ciudad].dropna().unique().tolist())
                ciudad_feriado = st.multiselect("🏙️ Ciudades:", ciudades_f_disp, key="ciudad_fer_key", on_change=guardar_ciudad_fer_callback)
            else:
                ciudad_feriado = st.multiselect("🏙️ Ciudades:", options=[], disabled=True, placeholder="Filtre Provincia", key="ms_ciudad_p_dis")

        with col_c_fer:
            meta_feriado = config_maestra_feriados[feriado_seleccionado]
            fecha_original = meta_feriado["fecha"]
            feriado_espejo = meta_feriado["espejo"]
            
            df_data_feriado = df_raw[(df_raw[col_fecha] == fecha_original) & (df_raw[col_servicio] == servicio_feriado)].copy()
            es_simulado = False
            
            if df_data_feriado.empty and feriado_espejo is not None:
                fecha_espejo = config_maestra_feriados[feriado_espejo]["fecha"]
                df_data_feriado = df_raw[(df_raw[col_fecha] == fecha_espejo) & (df_raw[col_servicio] == servicio_feriado)].copy()
                es_simulado = True
                
            if provincia_feriado != "Todas" and not df_data_feriado.empty:
                df_data_feriado = df_data_feriado[df_data_feriado[col_provincia] == provincia_feriado]
                if ciudad_feriado: df_data_feriado = df_data_feriado[df_data_feriado[col_ciudad].isin(ciudad_feriado)]
            
            if es_simulado:
                st.markdown(f'<div class="banner-similitud">🔮 <b>Proyección por Similitud Activa:</b> Calculando retornos para <b>{feriado_seleccionado} ({fecha_original})</b> usando comportamiento espejo de <b>{feriado_espejo} ({meta_feriado["dias"]} días de descanso)</b></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="banner-feriado">📈 <b>Datos Históricos Reales:</b> Analizando Primer Día Laboral de Retorno del feriado del <b>{fecha_original}</b></div>', unsafe_allow_html=True)
            
            if not df_data_feriado.empty:
                df_neto_hora = df_data_feriado.groupby(col_hora_agrupada).size().reset_index(name='HISTORICO_CASOS')
                df_neto_hora = df_neto_hora.sort_values(by=col_hora_agrupada)
                
                registros_processed = []
                data_grafico_feriado = []
                mapeo_casos = {row[col_hora_agrupada]: row['HISTORICO_CASOS'] for _, row in df_neto_hora.iterrows()}
                
                for hr in range(24):
                    casos_reales = mapeo_casos.get(hr, 0)
                    casos_previos = mapeo_casos.get(hr - 1, 0)
                    unidades_calculadas = math.ceil(casos_reales + (0.4 * casos_previos))
                    if casos_reales == 0 and unidades_calculadas <= 0: unidades_calculadas = 0
                    elif unidades_calculadas <= 0: unidades_calculadas = 1
                        
                    string_gruas = f"🚛 {unidades_calculadas} U." if unidades_calculadas > 0 else "-"
                    registros_processed.append({"HORA": f"{hr:02d}:00", "HISTÓRICO CASOS": casos_reales, "GRÚAS REQUERIDAS": string_gruas})
                    data_grafico_feriado.append({"Hora": hr, "Casos Históricos": casos_reales, "Grúas Proyectadas": unidades_calculadas})
                
                col_tab_izq, col_graf_der = st.columns([4.5, 5.5])
                with col_tab_izq:
                    st.markdown("<span style='font-size:12px; font-weight:bold; color:#111;'>⏰ Distribución de Demanda y Flota Requerida</span>", unsafe_allow_html=True)
                    st.dataframe(pd.DataFrame(registros_processed), use_container_width=True, height=220, hide_index=True)
                
                with col_graf_der:
                    st.markdown("<span style='font-size:12px; font-weight:bold; color:#111;'>📈 Gráfico de Curva de Carga Operativa (Retorno)</span>", unsafe_allow_html=True)
                    if data_grafico_feriado:
                        df_gf = pd.DataFrame(data_grafico_feriado)
                        fig_feriado = go.Figure()
                        fig_feriado.add_trace(go.Scatter(x=df_gf["Hora"], y=df_gf["Casos Históricos"], name="📊 Histórico Base", mode="lines+markers", line=dict(color="#1f77b4", width=2)))
                        fig_feriado.add_trace(go.Scatter(x=df_gf["Hora"], y=df_gf["Grúas Proyectadas"], name="🚛 Grúas Solicitadas", mode="lines+markers", line=dict(color="#d62728", width=2, dash="dot")))
                        fig_feriado.update_layout(
                            xaxis=dict(tickmode="linear", tick0=0, dtick=2, title=dict(text="Hora del Día", font=dict(size=9))),
                            yaxis=dict(title=dict(text="Cantidad", font=dict(size=9))),
                            margin=dict(l=5, r=5, t=5, b=5), height=220, showlegend=True,
                            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9))
                        )
                        st.plotly_chart(fig_feriado, use_container_width=True, config={'displayModeBar': False})
            else:
                st.warning("⚠️ No existen registros históricos en la base para la fecha de retorno y filtros seleccionados.")
else:
    st.error("❌ No se pudo conectar con el servidor de datos de Google Sheets o la estructura de columnas es incorrecta.")
