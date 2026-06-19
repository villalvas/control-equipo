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
    initial_sidebar_state="collapsed"
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
    div[data-testid="stVerticalBlock"] > div {
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
        gap: 0px !important;
    }
    /* Optimizar el espaciado de los selectores de filtros */
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
        "creditos": 48,
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

# Título del Monitor Principal de Control
st.markdown(f"<h2 style='margin:0px; padding:0px; font-size:26px;'>🔮 Proyección Horaria y Alerta de Flota</h2>", unsafe_allow_html=True)
st.markdown(f"<p style='margin:0px 0px 6px 0px; font-size:11px; color:#555;'><b>Control Geoanalítico</b> | 🔄 Refresco automático en 15 min. (Última Actualización: {hora_estatica_str})</p>", unsafe_allow_html=True)

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

    # --- ARQUITECTURA DE CONTENEDORES MAESTROS SIN SCROLL ---
    col_sidebar, col_main_content = st.columns([1.6, 8.4])
    
    if "dia_sel_key" not in st.session_state: st.session_state["dia_sel_key"] = estado_global["filtros_persistentes"]["dia_sel"]
    if "servicio_sel_key" not in st.session_state: st.session_state["servicio_sel_key"] = estado_global["filtros_persistentes"]["servicio_sel"]
    if "provincia_sel_key" not in st.session_state: st.session_state["provincia_sel_key"] = estado_global["filtros_persistentes"]["provincia_sel"]
    if "ciudad_sel_key" not in st.session_state: st.session_state["ciudad_sel_key"] = estado_global["filtros_persistentes"]["ciudad_sel"]
    if "estado_sel_key" not in st.session_state: st.session_state["estado_sel_key"] = estado_global["filtros_persistentes"]["estado_sel"]

    def guardar_dia_callback(): estado_global["filtros_persistentes"]["dia_sel"] = st.session_state["dia_sel_key"]
    def guardar_servicio_callback(): estado_global["filtros_persistentes"]["servicio_sel"] = st.session_state["servicio_sel_key"]
    def guardar_provincia_callback():
        estado_global["filtros_persistentes"]["provincia_sel"] = st.session_state["provincia_sel_key"]
        estado_global["filtros_persistentes"]["ciudad_sel"] = []
        st.session_state["ciudad_sel_key"] = []
    def guardar_ciudad_callback(): estado_global["filtros_persistentes"]["ciudad_sel"] = st.session_state["ciudad_sel_key"]
    def guardar_estado_callback(): estado_global["filtros_persistentes"]["estado_sel"] = st.session_state["estado_sel_key"]

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

    # --- PROCESAMIENTO GENERAL ---
    if dia_sel.upper() == "TODOS":
        df_filtrado_dia = df_raw.copy()
        num_fechas_reales = df_filtrado_dia[col_fecha].nunique() if col_fecha in df_filtrado_dia.columns else 1
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
        df_horas_raw[col_hora_agrupada] = pd.to_numeric(df_horas_raw[col_hora_agrupada], errors='coerce').fillna(-1).astype(int)
        
        casos_locales, casos_foraneos = [0] * 24, [0] * 24
        for hr in range(24):
            df_b = df_horas_raw[df_horas_raw[col_hora_agrupada] == hr]
            for _, fila in df_b.iterrows():
                if "FOR" in str(fila[col_cobertura]).upper(): casos_foraneos[hr] += 1
                else: casos_locales[hr] += 1

        for hr in range(24):
            p_local, p_foraneo = casos_locales[hr] / num_fechas_reales, casos_foraneos[hr] / num_fechas_reales
            promedio_base_calculado = int(round(p_local + p_foraneo, 0))
            
            clima_info = diccionario_clima.get(hr, {"Detalle": "☁️ Nublado", "Estado": "Normal"})
            detalle_clima = clima_info["Detalle"] if provincia_sel != "Todas" else "🌍 Filtre Prov."
            es_lluvia = clima_info["Estado"] == "Lluvia"

            if es_lluvia and promedio_base_calculado > 0:
                promedio_proyectado = math.ceil(promedio_base_calculado * 1.20)
                etiqueta_proyeccion = f"{promedio_proyectado} (+20%)"
                p_local_calc = p_local * 1.20
                p_foraneo_calc = p_foraneo * 1.20
            else:
                promedio_proyectado = promedio_base_calculado
                etiqueta_proyeccion = f"{promedio_proyectado} (Norm)"
                p_local_calc = p_local
                p_foraneo_calc = p_foraneo

            l_ant = p_local_calc if hr == 0 else (casos_locales[hr-1] / num_fechas_reales * (1.20 if es_lluvia else 1.0))
            f_ant1 = p_foraneo_calc if hr == 0 else (casos_foraneos[hr-1] / num_fechas_reales * (1.20 if es_lluvia else 1.0))
            f_ant2 = p_foraneo_calc if hr <= 1 else (casos_foraneos[hr-2] / num_fechas_reales * (1.20 if es_lluvia else 1.0))
            
            gruas_necesarias = math.ceil((p_local_calc + (0.5 * l_ant)) + (p_foraneo_calc + f_ant1 + f_ant2))
            es_remolque = any(x in str(servicio_sel).upper() for x in ["REMOLQUE", "GRÚA", "GRUA", "TODOS"])
            
            string_gruas = f"🚛 {gruas_necesarias} U." if es_remolque and (promedio_proyectado > 0 or gruas_necesarias > 0) else "-"
            val_gruas_grafico = gruas_necesarias if es_remolque else 0

            if promedio_base_calculado == 0 and gruas_necesarias == 0:
                motivo_asesor = "Sin demanda"
            else:
                explicaciones = []
                if promedio_proyectado > 0:
                    if es_lluvia: explicaciones.append(f"{promedio_proyectado} por lluvia")
                    else: explicaciones.append(f"{promedio_proyectado} nuevos")
                if gruas_necesarias > promedio_proyectado:
                    explicaciones.append("arrastre ant.")
                motivo_asesor = " + ".join(explicaciones) if explicaciones else "Ok"

            if promedio_base_calculado > 0 or string_gruas != "-":
                registros_tabla.append({
                    "HORA": f"{hr:02d}:00", "🌤️ Clima": detalle_clima, "📊 Prom": promedio_base_calculado, 
                    "📈 Proy": etiqueta_proyeccion, "🚛 Grúas N.": string_gruas, "📋 Diagnóstico": motivo_asesor
                })
            
            data_grafico_lineas.append({
                "Hora": hr, "Promedio Base": promedio_base_calculado,
                "Proyección Ajustada": promedio_proyectado, "Grúas Necesarias": val_gruas_grafico
            })

    with col_main_content:
        tab_normal, tab_feriados = st.tabs(["🔮 Operación Diaria (Normal)", "📈 Planificador de Feriados"])

        with tab_normal:
            # --- FILA SUPERIOR CENTRAL: LOCALIDADES AFECTADAS Y MATRIZ HORARIA ---
            col_mando_izq, col_mando_der = st.columns([4.0, 6.0])
            
            with col_mando_izq:
                st.markdown("<span style='font-size:12px; font-weight:bold; color:#111;'>📍 Top Localidades Affected</span>", unsafe_allow_html=True)
                if len(df_filtrado) > 0:
                    # Determinación de columna y agrupación
                    if provincia_sel == "Todas":
                        df_top = df_filtrado.groupby(col_provincia).size().reset_index(name='Casos')
                        df_top = df_top.rename(columns={col_provincia: 'Eje'})
                    else:
                        df_top = df_filtrado.groupby(col_ciudad).size().reset_index(name='Casos')
                        df_top = df_top.rename(columns={col_ciudad: 'Eje'})
                    
                    # Ordenar estrictamente de Mayor a Menor para el Top 5
                    df_top = df_top.sort_values(by='Casos', ascending=False).head(5)
                    
                    # Generación del gráfico horizontal mediante Plotly con etiquetas explícitas
                    # Nota: Plotly grafica de abajo hacia arriba en barras horizontales, por ende invertimos el eje en el layout para mantener el mayor arriba.
                    fig_top = go.Figure(go.Bar(
                        x=df_top['Casos'],
                        y=df_top['Eje'],
                        orientation='h',
                        text=df_top['Casos'],              # Muestra la cantidad directamente
                        textposition='outside',            # Posiciona el número fuera de la barra
                        marker_color='#444444',            # Tono oscuro ejecutivo idéntico al mock
                        textfont=dict(size=11, fontfamily="Arial")
                    ))
                    fig_top.update_layout(
                        margin=dict(l=5, r=40, t=5, b=5),  # Margen derecho amplio para el número
                        height=140,
                        xaxis=dict(showgrid=False, visible=False), # Ocultamos el eje X para ahorrar espacio
                        yaxis=dict(autorange="reversed", font=dict(size=11)), # Forzado estricto de Mayor arriba
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)'
                    )
                    st.plotly_chart(fig_top, use_container_width=True, config={'displayModeBar': False})
                else:
                    st.info("Sin datos.")

            with col_mando_der:
                st.markdown(f"<span style='font-size:12px; font-weight:bold; color:#111;'>⏰ Matriz Horaria Detallada: {dia_sel.title()}</span>", unsafe_allow_html=True)
                if registros_tabla: 
                    st.dataframe(pd.DataFrame(registros_tabla), use_container_width=True, height=140, hide_index=True)
                else:
                    st.info("Sin asistencias.")

            # --- FILA INFERIOR CENTRAL: CURVA LINEAL + RESUMEN EJECUTIVO / WAZE ---
            st.markdown("<div style='margin-top: 4px; border-top: 1px solid #ddd; padding-top: 2px;'></div>", unsafe_allow_html=True)
            
            col_grafico_full, col_resumen_waze = st.columns([6.8, 3.2])
            
            with col_grafico_full:
                st.markdown("<span style='font-size:13px; font-weight:bold; display:block;'>📈 Curva de Carga Operativa (24 Horas)</span>", unsafe_allow_html=True)
                if data_grafico_lineas:
                    df_gl = pd.DataFrame(data_grafico_lineas)
                    fig_lineas = go.Figure()
                    fig_lineas.add_trace(go.Scatter(x=df_gl["Hora"], y=df_gl["Promedio Base"], name="📊 Base", mode="lines+markers", line=dict(color="#1f77b4", width=2)))
                    fig_lineas.add_trace(go.Scatter(x=df_gl["Hora"], y=df_gl["Proyección Ajustada"], name="📈 Proy", mode="lines+markers", line=dict(color="#ff7f0e", width=2, dash="dash")))
                    fig_lineas.add_trace(go.Scatter(x=df_gl["Hora"], y=df_gl["Grúas Necesarias"], name="🚛 Requeridas", mode="lines+markers", line=dict(color="#2ca02c", width=2.5)))
                    fig_lineas.update_layout(
                        xaxis=dict(tickmode="linear", tick0=0, dtick=1, title=dict(text="Hora del Día", font=dict(size=10))),
                        yaxis=dict(title=dict(text="Unidades / Incidentes", font=dict(size=10))),
                        margin=dict(l=5, r=5, t=5, b=5),
                        height=150,
                        showlegend=True,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9))
                    )
                    st.plotly_chart(fig_lineas, use_container_width=True, config={'displayModeBar': False})

            with col_resumen_waze:
                promedio_asistencias_dia = int(round(len(df_filtrado) / num_fechas_reales, 0))
                st.markdown(f"<span style='font-size:11px; color:#555;'>Promedio ({dia_sel.title()})</span>", unsafe_allow_html=True)
                st.markdown(f"<h3 style='margin:0px; padding:0px; font-size:28px; line-height:1;'>{promedio_asistencias_dia} Asist.</h3>", unsafe_allow_html=True)
                
                st.markdown("<span style='font-size:11px; font-weight:bold; color:#1e88e5; display:block; margin-top:4px;'>🚛 Alertas Waze Realtime</span>", unsafe_allow_html=True)
                
                c_w1, c_w2 = st.columns([4.5, 5.5])
                with c_w1:
                    ejecutar_consulta = st.button("🔍 Escanear Mapa", use_container_width=True, key="btn_waze_comp")
                    if ejecutar_consulta and estado_global["creditos"] > 0:
                        bbox_nacional_ecuador = {"bottom_left": "-5.0000,-81.0000", "top_right": "1.5000,-75.0000"}
                        def consultar_alertas_waze_real(bbox_dict):
                            api_key = "ak_823f13app2zd9qkia4z6vdi27ttb31z9a7v7pvlhnn878w3"
                            try:
                                url = "https://api.openwebninja.com/waze/alerts-and-jams"
                                headers = {"X-API-Key": api_key}
                                params = {"bottom_left": "-2.2500,-79.9500", "top_right": "-2.1000,-79.8000"} if provincia_sel == "Todas" else {"bottom_left": bbox_dict["bottom_left"], "top_right": bbox_dict["top_right"]}
                                respuesta = requests.get(url, headers=headers, params=params, timeout=10).json()
                                alertas = []
                                if "alerts" in respuesta and respuesta["alerts"]:
                                    for item in respuesta["alerts"][:2]:
                                        tipo = item.get("type", "TRÁFICO").replace("_", " ")
                                        calle = item.get("street", "Vía pública")
                                        alertas.append(f"⚠️ {tipo} en {calle[:12]}...")
                                return alertas if alertas else ["✅ Flujo normal."]
                            except: return ["⚠️ Error de conexión."]
                        
                        estado_global["alertas_waze"] = consultar_alertas_waze_real(bbox_nacional_ecuador)
                        estado_global["ultima_hora_waze"] = ahora_actual.strftime('%I:%M %p')
                        estado_global["creditos"] -= 1
                    
                    st.markdown(f'<div class="card-saldo"><span style="font-size:9px;color:#444;">Tk: <b>{estado_global["creditos"]}</b>/50</span></div>', unsafe_allow_html=True)
                
                with c_w2:
                    st.markdown(f"<span style='font-size:9px; color:#777; display:block;'>Último: {estado_global['ultima_hora_waze']}</span>", unsafe_allow_html=True)
                    if not estado_global["alertas_waze"]: 
                        st.markdown("<span style='font-size:9px; color:#999;'>• Requiere escaneo.</span>", unsafe_allow_html=True)
                    else:
                        for incidente in estado_global["alertas_waze"][:1]:
                            st.markdown(f"<span style='font-size:9px; color:#d32f2f; font-weight:500;'>• {incidente}</span>", unsafe_allow_html=True)

        with tab_feriados:
            col_f_fer, col_c_fer = st.columns([3.0, 7.0])
            with col_f_fer:
                calendario_feriados_2026 = {
                    "Año Nuevo (Retorno Ene 5)": {"fecha_datos_historicos": "5/1/2026", "tipo": "Retorno"},
                    "Carnaval (Retorno Feb 18)": {"fecha_datos_historicos": "18/2/2026", "tipo": "Retorno"},
                    "Viernes Santo (Retorno Abr 6)": {"fecha_datos_historicos": "6/4/2026", "tipo": "Retorno"}
                }
                feriado_seleccionado = st.selectbox("📅 Feriado:", list(calendario_feriados_2026.keys()))
                servicio_feriado = st.selectbox("🎯 Servicio Feriado:", sorted(list(df_raw[col_servicio].dropna().unique())), index=0)
            
            with col_c_fer:
                meta_feriado = calendario_feriados_2026[feriado_seleccionado]
                fecha_buscar_str = meta_feriado["fecha_datos_historicos"]
                df_data_feriado = df_raw[(df_raw[col_fecha] == fecha_buscar_str) & (df_raw[col_servicio] == servicio_feriado)]
                
                st.markdown(f'<div class="banner-feriado">🇨🇪 Base Histórica: <b>{fecha_buscar_str}</b> ({meta_feriado["tipo"]})</div>', unsafe_allow_html=True)
                if not df_data_feriado.empty:
                    st.dataframe(df_data_feriado[[col_provincia, col_hora_agrupada]].head(5), use_container_width=True, height=130, hide_index=True)
                else:
                    st.caption("Sin registros históricos para este corte.")
