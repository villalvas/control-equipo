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
    page_title="Monitor de Proyecciones 2026 - Control de Flota (Guayaquil)",
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
    
    .green-alert-area {
        background-color: #f1faf6;
        border: 1px solid #c5e9d9;
        padding: 10px;
        border-radius: 6px;
        color: #2e7d32;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

zona_ecuador = ZoneInfo("America/Guayaquil")
ahora_actual = datetime.now(zona_ecuador)
hora_estatica_str = ahora_actual.strftime('%I:%M:%S %p')

# Título Principal
st.title("🔮 Monitor de Proyección Horaria y Alerta Temprana de Flota")

# Subtítulo y Hora Global
st.markdown(f"**Centro de Control Geoanalítico - Guayaquil** | 🔄 Próximo refresco automático en 5 min. (Hora Actual: {hora_estatica_str} - Jueves, 18 Junio 2026)")

# --- MEMORIA COMPARTIDA GLOBAL (PERSISTENTE ENTRE TODOS LOS OPERADORES Y REFRESCOS) ---
# Usamos cache_resource para mantener el estado unificado sin importar quién acceda al enlace.
@st.cache_resource
def inicializar_memoria_compartida():
    # Mapeo inicial de saldo según el perfil de consumo real
    return {
        "creditos": 48, 
        "alertas_waze": [],
        "ultima_hora_waze": "Nunca",
        "filtros": { # NUEVO: Guardamos los filtros globalmente
            "dia_tipo": "TODOS",
            "servicio": "Todos",
            "provincia": "Todas",
            "ciudades": []
        }
    }

memoria_global = inicializar_memoria_compartida()

# Cuadrantes BBox autorizados
coordenadas_bbox_provincias = {
    'PICHINCHA': {"bottom_left": "-0.3700,-78.6500", "top_right": "-0.0500,-78.3500"}, 
    'GUAYAS': {"bottom_left": "-2.3000,-80.0500", "top_right": "-2.0000,-79.7500"},    
    'AZUAY': {"bottom_left": "-2.9500,-79.1000", "top_right": "-2.8500,-78.9500"},     
    'MANABI': {"bottom_left": "-1.1000,-80.8000", "top_right": "-0.9000,-80.4000"}
}

coordenadas_provincias = {
    'PICHINCHA': [-0.2298, -78.5249], 'GUAYAS': [-2.1894, -79.8890], 'AZUAY': [-2.9001, -79.0059],
    'MANABI': [-1.0543, -80.4544], 'EL ORO': [-3.2581, -79.9553], 'LOJA': [-3.9931, -79.2042],
    'TUNGURAHUA': [-1.2491, -78.6168], 'CHIMBORAZO': [-1.6743, -78.6483], 'ESMERALDAS': [0.9682, -79.6517],
    'LOS RÍOS': [-1.4558, -79.4622], 'LOS RIOS': [-1.4558, -79.4622],
    'SANTO DOMINGO DE LOS TSÁCHILAS': [-0.2530, -79.1754], 'SANTA ELENA': [-2.2262, -80.8584],
    'IMBABURA': [0.3517, -78.1223], 'COTOPAXI': [-0.9352, -78.6155], 'CARCHI': [0.7384, -77.7289],
    'SUCUMBÍOS': [0.0847, -76.8828], 'SUCUMBIOS': [0.0847, -76.8828], 'ORELLANA': [-0.5665, -76.9872],
    'NAPO': [-0.9902, -77.8129], 'PASTAZA': [-1.4870, -77.9954], 'MORONA SANTIAGO': [-2.3087, -78.1114],
    'ZAMORA CHINCHIPE': [-4.0692, -78.9566], 'GALÁPAGOS': [-0.7402, -90.3119], 'BOLÍVAR': [-1.5910, -79.0022],
    'BOLIVAR': [-1.5910, -79.0022], 'CAÑAR': [-2.5518, -78.9392]
}

diccionario_dias = {
    "LUNES": 0, "MARTES": 1, "MIÉRCOLES": 2, "MIERCOLES": 2, 
    "JUEVES": 3, "VIERNES": 4, "SÁBADO": 5, "SABADO": 5, "DOMINGO": 6
}

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
    col_estado_asist = "ESTADO DE ASISTENCIA"
    col_hora_agrupada = "HORA AGRUPADA"
    col_fecha = "FECHA CREACIÓN DE ASISTENCIA" if "FECHA CREACIÓN DE ASISTENCIA" in df_raw.columns else "FECHA CREACION DE ASISTENCIA"
    col_cobertura = "TIPO COBERTURA"

    df_raw[col_provincia] = df_raw[col_provincia].astype(str).str.strip().str.upper()
    if col_ciudad in df_raw.columns: df_raw[col_ciudad] = df_raw[col_ciudad].astype(str).str.strip()
    df_raw[col_cobertura] = df_raw[col_cobertura].astype(str).str.strip().str.upper() if col_cobertura in df_raw.columns else "LOCAL"

    st.write("### 🎛️ Panel de Filtros de Operación")
    f1, f2, f3, f4, f5 = st.columns([2, 2, 2, 3, 3])
    
    # ---------------------------------------------------------
    # --- IMPLEMENTACIÓN DE PERSISTENCIA GLOBAL DE FILTROS ---
    # ---------------------------------------------------------
    # Recuperamos los filtros guardados globalmente
    filtros_globales = memoria_global["filtros"]
    
    with f1:
        dias_en_orden = ["TODOS", "LUNES", "MARTES", "MIÉRCOLES", "JUEVES", "VIERNES", "SÁBADO", "DOMINGO"]
        dias_disponibles = [d for d in dias_en_orden if d == "TODOS" or d in list(df_raw[col_dia].str.upper().unique())]
        try:
            default_dia_index = dias_disponibles.index(filtros_globales["dia_tipo"])
        except ValueError:
            default_dia_index = 0
            
        dia_sel = st.selectbox("📅 Seleccionar Día Tipo:", dias_disponibles, index=default_dia_index)
        # Actualizar memoria global inmediatamente
        memoria_global["filtros"]["dia_tipo"] = dia_sel
    
    with f2:
        servicios_disponibles = sorted(["Todos"] + list(df_raw[col_servicio].dropna().unique()))
        try:
            default_servicio_index = servicios_disponibles.index(filtros_globales["servicio"])
        except ValueError:
            default_servicio_index = 0
            
        servicio_sel = st.selectbox("🎯 Seleccionar Servicio:", servicios_disponibles, index=default_servicio_index)
        memoria_global["filtros"]["servicio"] = servicio_sel
        
    with f3:
        provincias_disponibles = ["Todas"] + df_raw[col_provincia].value_counts().index.tolist()
        try:
            default_provincia_index = provincias_disponibles.index(filtros_globales["provincia"])
        except ValueError:
            default_provincia_index = 0
            
        provincia_sel = st.selectbox("📍 Seleccionar Provincia:", provincias_disponibles, index=default_provincia_index)
        memoria_global["filtros"]["provincia"] = provincia_sel
        
    with f4:
        if provincia_sel != "Todas":
            ciudades_disponibles = sorted(df_raw[df_raw[col_provincia] == provincia_sel][col_ciudad].dropna().unique().tolist())
            # Mantener solo las ciudades guardadas que siguen siendo válidas para la nueva provincia
            ciudades_validas_guardadas = [c for c in filtros_globales["ciudades"] if c in ciudades_disponibles]
            
            ciudad_sel = st.multiselect("🏙️ Filtrar Ciudades:", ciudades_disponibles, default=ciudades_validas_guardadas, placeholder="Todas las ciudades")
            memoria_global["filtros"]["ciudades"] = ciudad_sel
        else:
            ciudad_sel = st.multiselect("🏙️ Filtrar Ciudades:", options=[], disabled=True, placeholder="Filtre por Provincia primero")
            memoria_global["filtros"]["ciudades"] = []
            
    with f5:
        if col_estado_asist in df_raw.columns:
            estados_disponibles = sorted(list(df_raw[col_estado_asist].dropna().unique()))
            # Aquí no aplicamos persistencia global a los estados porque son muy transitorios, se mantiene local
            estado_sel = st.multiselect("📌 Filtrar por Estado:", options=estados_disponibles, default=[], placeholder="Todos los estados")
        else:
            estado_sel = []

    # --- Lógica de Procesamiento de Fechas basada en filtros persistentes ---
    if dia_sel.upper() == "TODOS":
        df_dia_especifico = df_raw.copy()
        num_fechas_reales = df_dia_especifico[col_fecha].nunique() if col_fecha in df_dia_especifico.columns else 1
        fecha_target_str = ahora_actual.strftime("%Y-%m-%d")
        dias_diferencia = 0
    else:
        # Aquí se mantiene la lógica de cálculo de fecha tipo
        ... # (Código de cálculo de fecha tipo omitido por brevedad, se mantiene igual)

    if num_fechas_reales <= 0: num_fechas_reales = 1

    # --- Lógica de Filtrado de Datos basada en filtros persistentes ---
    df_filtrado = df_dia_especifico.copy()
    if estado_sel and col_estado_asist in df_raw.columns: df_filtrado = df_filtrado[df_filtrado[col_estado_asist].isin(estado_sel)]
    if servicio_sel != "Todos": df_filtrado = df_filtrado[df_filtrado[col_servicio] == servicio_sel]
    if provincia_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado[col_provincia] == provincia_sel]
        if ciudad_sel: df_filtrado = df_filtrado[df_filtrado[col_ciudad].isin(ciudad_sel)]

    # --- Funciones de Clima Horario (Abstraídas, TTL=300) ---
    @st.cache_data(ttl=300)
    def obtener_clima_horario_futuro(lat, lon, fecha_objetivo_str):
        # Lógica Open-Meteo...
        ...

    @st.cache_data(ttl=300)
    def obtener_clima_actual_rapido(lat, lon):
        # Lógica Open-Meteo rápida...
        ...

    @st.cache_data(ttl=3600)
    def calcular_factor_lluvia_en_vivo(df_historico, lat, lon):
        # Lógica Archive-API factor lluvia...
        ...

    # --- Lógica Clima y Factor Ajuste ---
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
        
        # Ciudades Table (Persistente por provincia)
        if len(df_filtrado) > 0:
            ... # (Lógica tabla ciudades idéntica, se actualiza al cambiar la persistencia de provincia)

    with col_cen:
        # Matriz Horaria (Sincronizada por clima)
        ... # (Lógica matriz horaria idéntica, se actualiza sincronizadamente)

    with col_der:
        st.write("##### 🚛 Alertas e Incidentes")
        
        # --- NUEVA REGLA DE VALIDACIÓN PARA EL BOTÓN DE WAZE (PROVINCIA + SERVICIO) ---
        provincia_limpia = provincia_sel.upper().strip()
        es_provincia_valida = provincia_limpia in coordenadas_bbox_provincias and provincia_sel != "Todas"
        
        servicio_limpio = str(servicio_sel).upper().strip()
        es_servicio_valido = any(x in servicio_limpio for x in ["REMOLQUE", "GRÚA", "GRUA"]) and servicio_limpio != "TODOS"

        if es_provincia_valida and es_servicio_valido:
            btn_text = "🔍 Consultar Tráfico en Vivo (Waze)"
            is_disabled = False
        else:
            if not es_servicio_valido and not es_provincia_valida: btn_text = "🔒 Filtre Servicio Remolque y Región Válida"
            elif not es_servicio_valido: btn_text = "🔒 Waze solo para servicio de Remolque"
            else: btn_text = "🔒 Waze disponible solo en UIO/GYE/CUE/MNT"
            is_disabled = True

        btn_consultar = st.button(btn_text, use_container_width=True, disabled=is_disabled)
        
        # --- Función de Consulta Waze Real (ENDPOINT-AND-JAMS) ---
        api_key = "ak_823f13app2zd9qkia4z6vdi27ttb31z9a7v7pvlhnn878w3" # INTEGRADA
        def consultar_alertas_waze_real(bbox_dict):
            # ... (Lógica consulta Waze unificada alerts-and-jams)
            ...

        if btn_consultar and es_provincia_valida and es_servicio_valido:
            if memoria_global["creditos"] > 0:
                bbox_zona = coordenadas_bbox_provincias[provincia_limpia]
                
                with st.spinner(f"Conectando Waze ({provincia_sel.title()})..."):
                    resultado_waze = consultar_alertas_waze_real(bbox_zona)
                    # Mutación directa del diccionario compartido
                    memoria_global["alertas_waze"] = resultado_waze
                    memoria_global["ultima_hora_waze"] = ahora_actual.strftime('%I:%M:%S %p')
                    memoria_global["creditos"] -= 1 
            else:
                st.error("❌ Se ha alcanzado el límite global de 50 consultas del plan gratuito.")
        
        st.caption(f"⏱️ Último reporte Waze: **{memoria_global['ultima_hora_waze']}**")
        
        if not es_provincia_valida or not es_servicio_valido:
            st.warning("⚠️ El botón requiere Provincia autorizada Y especificar Servicio de Remolque.")
        elif not memoria_global["alertas_waze"]:
            st.info("💡 Parámetros correctos. Presiona el botón para consultar tráfico en vivo.")
        else:
            for incidente in memoria_global["alertas_waze"]:
                if "✅" in incidente: st.success(incidente)
                else: st.error(incidente)
                
        # Contador visual de saldo (Sincronizado, Inicia en 48)
        st.markdown(f"""
            <div class="card-saldo">
                <span style="font-size: 12px; color: #555555; font-weight: bold; display:block;">🔑 CRÉDITOS OPENWEBNINJA (COMPARTIDO)</span>
                <span style="font-size: 26px; color: #2e7d32; font-weight: 800;">{memoria_global['creditos']}</span>
                <span style="font-size: 14px; color: #777777;"> / 50 Restantes</span>
            </div>
        """, unsafe_allow_html=True)
        
        # Estado Monitor Meteorológico Guayaquil
        st.markdown(f"""
            <div class="green-alert-area">
                🟢 Monitor meteorológico y matriz analítica operando al 100% en tiempo real en Guayaquil.
            </div>
        """, unsafe_allow_html=True)
