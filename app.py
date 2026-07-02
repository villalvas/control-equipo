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

# --- MEMORIA INMUNE PARA FILTROS Y AUTENTICACIÓN ---
@st.cache_resource
def inicializar_memoria_inmune():
    return {
        "autenticado": False,  # Guardamos el estado de login aquí para que sea inmune al refresh
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

# --- CONTROL DE ACCESO MEDIANTE CONTRASEÑA INMUNE A REFRESH ---
CONTRASEÑA_SALA_CONTROL = "Control2026*"

if not estado_global["autenticado"]:
    st.markdown("""
        <style>
        .block-container { padding-top: 5rem !important; text-align: center; max-width: 450px !important; margin: 0 auto !important; }
        </style>
    """, unsafe_allow_html=True)
    
    st.image("https://cdn-icons-png.flaticon.com/512/3064/3064155.png", width=80)
    st.markdown("<h2 style='margin-bottom:5px;'>Sala de Control Mandos</h2>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:12px; color:#666;'>Ingrese la contraseña de seguridad para visualizar el monitor táctico nacional.</p>", unsafe_allow_html=True)
    
    clave_ingresada = st.text_input("Contraseña de Acceso:", type="password", placeholder="••••••••••••", label_visibility="collapsed")
    
    if st.button("Ingresar al Tablero", use_container_width=True):
        if clave_ingresada == CONTRASEÑA_SALA_CONTROL:
            estado_global["autenticado"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta. Acceso denegado.")
    st.stop()

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

# Estilos CSS radicales para compactar y centrar elementos de texto generales
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDataFrame [data-testid="stDataFrameDownloadButton"] {display: none;}
    button[title="View fullscreen"] {display: none;}
    
    .block-container {
        padding-top: 0.2rem !important;
        padding-bottom: 0.1rem !important;
        padding-left: 0.8rem !important;
        padding-right: 0.8rem !important;
        margin-top: 0px !important;
    }
    
    [data-testid="stTable"] td, [data-testid="stDataFrame"] td, 
    div[data-testid="stDataFrame"] [role="gridcell"] {
        font-size: 11px !important;
        font-weight: 500 !important;
        padding: 1px 3px !important;
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
    
    /* Contenedor escaneable para alertas derechas */
    .contenedor-alertas-derecha {
        background-color: #fcfcfc;
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        padding: 8px;
        height: 82vh;
        overflow-y: auto;
    }
    </style>
    """, unsafe_allow_html=True)

zona_ecuador = ZoneInfo("America/Guayaquil")
ahora_actual = datetime.now(zona_ecuador)
hora_estatica_str = ahora_actual.strftime('%I:%M:%S %p')

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

# --- MONITOR SÍSMICO Y VOLCÁNICO ---
@st.cache_data(ttl=300)
def consultar_sismos_y_volcanes():
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": datetime.now(ZoneInfo("America/Guayaquil")).strftime("%Y-%m-%d"),
        "minmagnitude": "4.0",
        "minlatitude": "-5.0",
        "maxlatitude": "1.5",
        "minlongitude": "-81.0",
        "maxlongitude": "-75.0"
    }
    eventos = []
    # Alerta Volcánica Fija de Monitoreo por Riesgo País (Sangay/Cotopaxi/Tungurahua)
    eventos.append("🌋 ALERTA VOLCÁNICA: Actividad moderada Sangay con dispersión de ceniza hacia el Oeste.")
    try:
        respuesta = requests.get(url, params=params, timeout=5).json()
        for feature in respuesta.get("features", []):
            prop = feature["properties"]
            lugar = prop["place"]
            mag = prop["mag"]
            eventos.append(f"🚨 SISMO DETECTADO: Mag {mag} - {lugar}")
    except:
        pass
    return eventos

# --- MATRIZ DE BASE DE DATOS NACIONAL - ECU 911 VIAL ---
@st.cache_data
def obtener_reportes_ecu911_nacional():
    raw_data = [
        {"PROVINCIA": "AZUAY", "VIA": "CUENCA-CAÑAR-ALAUSI", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "SECTOR EL ROCIO"},
        {"PROVINCIA": "AZUAY", "VIA": "CUENCA - MOLLETURO - NARANJAL", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "KM 101 MÁX 3.5 TON, PRECAUCIÓN KM 49, 53, 57"},
        {"PROVINCIA": "AZUAY", "VIA": "CUENCA - GUARUMALES - MENDEZ - MACAS", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "SECTOR SACRE Y KM 50, 61."},
        {"PROVINCIA": "AZUAY", "VIA": "CUENCA - GIRON -PASAJE - MACHALA", "ESTADO": "CERRADA", "OBS": "CERRADO DESDE EL KM 82 HASTA JURISDICCIÓN AZUAY"},
        {"PROVINCIA": "COTOPAXI", "VIA": "ZUMBAHUA - LATACUNGA", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "SECTOR TACAJALO KM 106 - DESLIZAMIENTO TALUD"},
        {"PROVINCIA": "EL ORO", "VIA": "BALSAS-RIO PINDO", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "SOCAVAMIENTO Y DESLIZAMIENTO ALTURA SITIO GUERRAS"},
        {"PROVINCIA": "EL ORO", "VIA": "PORTOVELO - SALATI - AMBOCAS - EL CISNE", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "DESLIZAMIENTO DE TIERRA MÁS PÉRDIDA DE MESA VIAL"},
        {"PROVINCIA": "ESMERALDAS", "VIA": "SAN MATEO - VICHE", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "PÉRDIDA DE MASA ASFÁLTICA SECTOR CHINCHA KM 32"},
        {"PROVINCIA": "ESMERALDAS", "VIA": "DEL SALTO-CHAMANGA", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "DESBORAMIENTO DEL RÍO SUCIO, MANEJAR CON PRECAUCIÓN"},
        {"PROVINCIA": "ESMERALDAS", "VIA": "VIA QUININDE - EL MIRADOR - ESMERALDAS", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "FALLAS DE TALUD A LA ALTURA DE EL MIRADOR KM 71"},
        {"PROVINCIA": "LOJA", "VIA": "VIA CARIAMANGA - ESPINDOLA", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "DESLIZAMIENTO DE TIERRA / SOCAVÓN SECTOR SAN ANTONIO"},
        {"PROVINCIA": "LOJA", "VIA": "VÍA CARIAMANGA - SOZORANGA", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "SECTOR PARROQUIA UTUANA / DESLIZAMIENTO DE TIERRA"},
        {"PROVINCIA": "LOJA", "VIA": "VIA LOJA - MALACATOS", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "SECTOR NANGORA / CIRCULAR CON PRECAUCIÓN"},
        {"PROVINCIA": "LOJA", "VIA": "VIA OLMEDO - CHAGUARPAMBA", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "DESLIZAMIENTO DE TIERRA"},
        {"PROVINCIA": "LOJA", "VIA": "VÍA CATACOCHA - EL EMPALME - LUCARQUI -MACARÁ", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "SECTOR LUCARQUI / DESLIZAMIENTO DE TIERRA"},
        {"PROVINCIA": "LOJA", "VIA": "VIA VELACRUZ - CATACOCHA", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "SECTOR NARANJO PALTO / INDEFINIDO POR DESLIZAMIENTOS"},
        {"PROVINCIA": "LOJA", "VIA": "VÍA EL EMPALME - CELICA - ALAMOR", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "PASO RESTRINGIDO PARA TRANSPORTE PESADO POR COE CANTONAL"},
        {"PROVINCIA": "LOJA", "VIA": "VIA ALAMOR - ARENILLAS", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "SECTOR COCHURCHO / HUNDIMIENTO DE CALZADA"},
        {"PROVINCIA": "LOJA", "VIA": "VÍA SOZORANGA - MACARÁ / PENJAMO", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "SECTOR PÉNJAMO / TRABAJOS DE LIMPIEZA CONSTANTES"},
        {"PROVINCIA": "LOJA", "VIA": "LOJA - SARAGURO", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "SECTOR CENÉN KM 13 / HUNDIMIENTO DE CALZADA"},
        {"PROVINCIA": "LOJA", "VIA": "SAN PEDRO - LAS CHINCHAS - VIA A LA COSTA", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "VARIOS DESLIZAMIENTOS DE TIERRA"},
        {"PROVINCIA": "MANABI", "VIA": "ROCAFUERTE - TOSAGUA", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "SOCAVÓN EN EL KM 187, UN CARRIL Y MEDIO HABILITADO"},
        {"PROVINCIA": "MANABI", "VIA": "CANUTO - CALCETA", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "SOCAVÓN A LA ALTURA DE CANUTO"},
        {"PROVINCIA": "MANABI", "VIA": "SAN JOSE DE CHAMANGA - PEDERNALES", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "SOCAVÓN CON LAS RESPECTIVAS SEÑALÉTICAS"},
        {"PROVINCIA": "MANABI", "VIA": "JIPIJAPA - LIMITE PROVINCIAL (LA CADENA)", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "KM 75 VÍA PAJÁN-CASCOL HUNDIMIENTO DE VÍA"},
        {"PROVINCIA": "MANABI", "VIA": "TOSAGUA - BAHIA", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "ALTURA DEL KM 5, SECTOR VERDÚN"},
        {"PROVINCIA": "MORONA SANTIAGO", "VIA": "LIMON - SAN JUAN BOSCO", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "DESLIZAMIENTO DE TIERRA EN EL SECTOR PAXI"},
        {"PROVINCIA": "MORONA SANTIAGO", "VIA": "MENDEZ - GUARUMALES-CUENCA", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "CIERRE PASO LATERAL VÍA MÉNDEZ-GUARUMALES POR SOCAVÓN"},
        {"PROVINCIA": "MORONA SANTIAGO", "VIA": "TIWINTZA - SAN JOSÉ DE MORONA", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "DESLIZAMIENTO SECTOR SHAIME"},
        {"PROVINCIA": "MORONA SANTIAGO", "VIA": "BELLA UNION - LIMON", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "DESLIZAMIENTO DE TIERRA SECTOR EL ROSARIO"},
        {"PROVINCIA": "MORONA SANTIAGO", "VIA": "LIMON - GUALACEO", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "DESLIZAMIENTO E INESTABILIDAD DE TALUD SECTOR CHACRAS"},
        {"PROVINCIA": "MORONA SANTIAGO", "VIA": "GUALAQUIZA - CHIGUINDA - SIGSIG - CUENCA", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "DESLIZAMIENTO DE TIERRA SECTOR GALLO CANTANA"},
        {"PROVINCIA": "MORONA SANTIAGO", "VIA": "SAN JUAN BOSCO - GUALAQUIZA", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "DESLIZAMIENTO SECTOR EL PAXI Y EL SACRAMENTO"},
        {"PROVINCIA": "MORONA SANTIAGO", "VIA": "MACAS - RIOBAMBA", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "DESLIZAMIENTO CASCADA MACABEA Y ROCAS KM 47 ATILLO"},
        {"PROVINCIA": "SUCUMBIOS", "VIA": "VIA INTEROCEANICA - LA BONITA - EL PLAYON", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "CIRCULAR CON PRECAUCIÓN SECTOR ROSA FLORIDA"},
        {"PROVINCIA": "SUCUMBIOS", "VIA": "LAGO AGRIO-EL REVENTADOR", "ESTADO": "PARCIALMENTE HABILITADA", "OBS": "PÉRDIDA DE CALZADA KM 71-82"},
        {"PROVINCIA": "ZAMORA CHINCHIPE", "VIA": "EL PANGUI - TUNDAYME", "ESTADO": "HABILITADA CON RESTRICCIÓN", "OBS": "SECTOR EL OASIS / DESLIZAMIENTO DE TIERRA"}
    ]
    return pd.DataFrame(raw_data)

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

    def extraer_hora_limpia(val):
        val_str = str(val).strip().split('.')[0]
        if ":" in val_str:
            return int(val_str.split(":")[0])
        try: return int(val_str)
        except: return -1

    if col_hora_agrupada in df_raw.columns:
        df_raw[col_hora_agrupada] = df_raw[col_hora_agrupada].apply(extraer_hora_limpia)

    # --- BARRA LATERAL IZQUIERDA (FILTROS) ---
    with st.sidebar:
        st.markdown("<h4 style='margin:0px; font-size:14px; color:#111;'>⚙️ Filtros Operativos</h4>", unsafe_allow_html=True)
        
        dias_en_orden = ["TODOS", "LUNES", "MARTES", "MIÉRCOLES", "MIERCOLES", "JUEVES", "VIERNES", "SÁBADO", "SABADO", "DOMINGO"]
        dias_disponibles = [d for d in dias_en_orden if d == "TODOS" or d in list(df_raw[col_dia].str.upper().unique())]
        
        dia_sel = st.selectbox("📅 Día Tipo:", dias_disponibles, index=0)
        
        lista_servicios = ["Todos"] + sorted(list(df_raw[col_servicio].dropna().unique()))
        servicio_sel = st.selectbox("🎯 Servicio:", lista_servicios, index=0)
        
        provincia_sel = st.selectbox("📍 Provincia:", ["Todas"] + df_raw[col_provincia].value_counts().index.tolist(), index=0)
        
        if provincia_sel != "Todas":
            ciudades_disponibles = sorted(df_raw[df_raw[col_provincia] == provincia_sel][col_ciudad].dropna().unique().tolist())
            ciudad_sel = st.multiselect("🏙️ Ciudades:", ciudades_disponibles)
        else:
            ciudad_sel = st.multiselect("🏙️ Ciudades:", options=[], disabled=True, placeholder="Filtre Provincia")
            
        if col_estado in df_raw.columns:
            estados_disponibles = sorted(list(df_raw[col_estado].dropna().unique()))
            estado_sel = st.multiselect("📌 Estado:", options=estados_disponibles)
        else: 
            estado_sel = []

        st.markdown("<div style='margin-top: 15px; border-top: 1px dashed #ccc; padding-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 REBOOT APP", use_container_width=True):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()
            
        if st.button("🔒 CERRAR SESIÓN", use_container_width=True):
            estado_global["autenticado"] = False
            st.rerun()

    # --- LÓGICA DE FILTRADO DE DATOS ---
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

    # --- ENCABEZADO SUPERIOR CON CONTROL DEL PANEL DERECHO ---
    col_titulo, col_control_derecho, col_metrica_global = st.columns([5.5, 2.3, 2.2])

    with col_titulo:
        st.markdown(f"<h2 style='margin:0px; padding:0px; font-size:24px;'>🔮 Proyección Horaria y Alerta de Flota</h2>", unsafe_allow_html=True)
        st.markdown(f"<p style='margin:0px 0px 4px 0px; font-size:11px; color:#555;'><b>Control Geoanalítico</b> | 🔄 Memoria Activa ({hora_estatica_str})</p>", unsafe_allow_html=True)

    with col_control_derecho:
        # Toggle para ocultar o mostrar por completo el panel de alertas nacional derecho
        mostrar_alertas_panel = st.toggle("🌋 Ver Panel de Emergencias", value=True, help="Muestra u oculta la barra lateral derecha de alertas nacionales.")

    with col_metrica_global:
        if len(df_filtrado) > 0:
            promedio_asistencias_dia = round(len(df_filtrado) / num_fechas_reales, 1)
            st.markdown(
                f"""
                <div style="background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; padding: 2px 8px; text-align: right;">
                    <span style="font-size: 9px; color: #666; display: block; font-weight: bold; text-transform: uppercase;">Promedio General ({dia_sel.title()})</span>
                    <span style="font-size: 16px; color: #0d47a1; font-weight: 800; line-height: 1;">{promedio_asistencias_dia} Asist.</span>
                </div>
                """, 
                unsafe_allow_html=True
            )

    # --- MANEJO DINÁMICO DEL ANCHO DE COLUMNAS (CENTRO VS DERECHA) ---
    if mostrar_alertas_panel:
        col_centro_tablero, col_derecha_alertas = st.columns([7.2, 2.8])
    else:
        col_centro_tablero = st.container()

    # =========================================================
    # BLOQUE CENTRAL: CONFIGURACIÓN DE PESTAÑAS Y GRÁFICOS
    # =========================================================
    with col_centro_tablero:
        tab_normal, tab_feriados = st.tabs(["🔮 Operación Diaria (Normal)", "📈 Planificador de Feriados"])
        
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
                promedio_base_calculated = round(p_local + p_foraneo, 1)
                
                clima_info = diccionario_clima.get(hr, {"Detalle": "☁️ Nublado", "Estado": "Normal"})
                detalle_clima = clima_info["Detalle"] if provincia_sel != "Todas" else "🌍 Filtre Prov."
                es_lluvia = clima_info["Estado"] == "Lluvia"

                if es_lluvia and promedio_base_calculated > 0:
                    promedio_proyectado = math.ceil(promedio_base_calculated * 1.20)
                    etiqueta_proyeccion = f"{promedio_proyectado} (+20%)"
                    p_local_calc, p_foraneo_calc = p_local * 1.20, p_foraneo * 1.20
                else:
                    promedio_proyectado = int(round(promedio_base_calculated, 0))
                    etiqueta_proyeccion = f"{promedio_proyectado} (Norm)"
                    p_local_calc, p_foraneo_calc = p_local, p_foraneo

                l_ant = p_local_calc if hr == 0 else (casos_locales[hr-1] / num_fechas_reales * (1.20 if es_lluvia else 1.0))
                f_ant1 = p_foraneo_calc if hr == 0 else (casos_foraneos[hr-1] / num_fechas_reales * (1.20 if es_lluvia else 1.0))
                f_ant2 = p_foraneo_calc if hr <= 1 else (casos_foraneos[hr-2] / num_fechas_reales * (1.20 if es_lluvia else 1.0))
                
                if promedio_proyectado == 0:
                    gruas_necesarias = math.ceil((0.1 * l_ant) + (0.2 * f_ant1) + (0.1 * f_ant2))
                else:
                    gruas_necesarias = math.ceil((p_local_calc + (0.5 * l_ant)) + (p_foraneo_calc + f_ant1 + f_ant2))
                    
                es_remolque = any(x in str(servicio_sel).upper() for x in ["REMOLQUE", "GRÚA", "GRUA", "TODOS"])
                string_gruas = f"🚛 {gruas_necesarias} U." if es_remolque and (promedio_proyectado > 0 or gruas_necesarias > 0) else "-"

                motivo_asesor = "Sin demanda" if promedio_base_calculated == 0 and gruas_necesarias == 0 else "Ok"

                registros_tabla.append({
                    "HORA": f"{hr:02d}:00", "🌤️ Clima": detalle_clima, "📊 Prom": promedio_base_calculated, 
                    "📈 Proy": etiqueta_proyeccion, "🚛 Grúas N.": string_gruas, "📋 Diagnóstico": motivo_asesor
                })
                data_grafico_lineas.append({"Hora": hr, "Promedio Base": promedio_base_calculated, "Proyección Ajustada": promedio_proyectado})

        with tab_normal:
            col_mando_izq, col_mando_der = st.columns([4.2, 5.8])
            with col_mando_izq:
                st.markdown("<span style='font-size:11px; font-weight:bold; color:#111;'>📍 Top Localidades Afectadas</span>", unsafe_allow_html=True)
                if len(df_filtrado) > 0:
                    col_agrupar = col_provincia if provincia_sel == "Todas" else col_ciudad
                    df_top = df_filtrado.groupby(col_agrupar).size().reset_index(name='Casos')
                    df_top['📊 Prom/Día'] = (df_top['Casos'] / num_fechas_reales).round(1)
                    df_top = df_top.rename(columns={col_agrupar: '📍 UBICACIÓN'}).sort_values(by='Casos', ascending=False).head(5)
                    st.dataframe(df_top, use_container_width=True, height=150, hide_index=True)
                else: st.info("Sin datos.")

            with col_mando_der:
                st.markdown(f"<span style='font-size:11px; font-weight:bold; color:#111;'>⏰ Matriz Horaria Detallada: {dia_sel.title()}</span>", unsafe_allow_html=True)
                if registros_tabla:
                    st.dataframe(pd.DataFrame(registros_tabla), use_container_width=True, height=150, hide_index=True)
                else: st.info("Sin asistencias.")

            st.markdown("<div style='margin-top: 6px; border-top: 1px solid #eee; padding-top: 4px;'></div>", unsafe_allow_html=True)
            st.markdown("<span style='font-size:11px; font-weight:bold; display:block;'>📈 Curva de Carga Operativa (24 Horas)</span>", unsafe_allow_html=True)
            if data_grafico_lineas:
                df_gl = pd.DataFrame(data_grafico_lineas)
                fig_lineas = go.Figure()
                fig_lineas.add_trace(go.Scatter(x=df_gl["Hora"], y=df_gl["Promedio Base"], name="📊 Promedio Base", mode="lines+markers", line=dict(color="#1f77b4", width=2)))
                fig_lineas.add_trace(go.Scatter(x=df_gl["Hora"], y=df_gl["Proyección Ajustada"], name="📈 Ajuste Clima", mode="lines+markers", line=dict(color="#ff7f0e", width=2, dash="dash")))
                fig_lineas.update_layout(xaxis=dict(tickmode="linear", dtick=2), margin=dict(l=5, r=5, t=5, b=5), height=160, showlegend=True, legend=dict(orientation="h", y=1.1))
                st.plotly_chart(fig_lineas, use_container_width=True, config={'displayModeBar': False})

        with tab_feriados:
            col_f_fer, col_c_fer = st.columns([2.5, 7.5])
            with col_f_fer:
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
                feriado_seleccionado = st.selectbox("📅 Feriado Retorno:", list(config_maestra_feriados.keys()), key="fer_sel_box")
                servicio_feriado = st.selectbox("🎯 Servicio Feriado:", sorted(list(df_raw[col_servicio].dropna().unique())), key="ser_fer_box")

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
                
                if not df_data_feriado.empty:
                    st.markdown("<span style='font-size:11px; font-weight:bold; color:#111;'>⏰ Retorno Histórico Proyectado</span>", unsafe_allow_html=True)
                    df_neto_hora = df_data_feriado.groupby(col_hora_agrupada).size().reset_index(name='Casos')
                    st.dataframe(df_neto_hora.rename(columns={col_hora_agrupada: 'HORA'}), use_container_width=True, height=140, hide_index=True)
                else:
                    st.warning("⚠️ Sin registros históricos para esta combinación de feriado.")

    # =========================================================
    # PANEL LATERAL DERECHO: MONITOR DE EMERGENCIA NACIONAL
    # =========================================================
    if mostrar_alertas_panel:
        with col_derecha_alertas:
            st.markdown("<h4 style='margin:0px; font-size:14px; color:#c62828; font-weight:bold;'>🌋 Seguridad Nacional</h4>", unsafe_allow_html=True)
            
            # Apertura de contenedor estandarizado escaneable
            st.markdown('<div class="contenedor-alertas-derecha">', unsafe_allow_html=True)
            
            # --- BLOQUE 1: VOLCANES Y SISMOS CRÍTICOS ---
            st.markdown("<span style='font-size:11px; font-weight:bold; color:#111; display:block; border-bottom:1px solid #ddd; padding-bottom:2px; margin-bottom:4px;'>🌋 Actividad Volcánica y Sismos (USGS)</span>", unsafe_allow_html=True)
            alertas_geologicas = consultar_sismos_y_volcanes()
            for evento in alertas_geologicas:
                color_borde = "#c62828" if "🚨" in evento else "#ef6c00"
                bg_alerta = "#ffebee" if "🚨" in evento else "#fff3e0"
                st.markdown(f"""
                    <div style="background-color: {bg_alerta}; border-left: 4px solid {color_borde}; padding: 4px; border-radius: 4px; margin-bottom: 4px; font-size: 10px; color: #222; font-weight: 500;">
                        {evento}
                    </div>
                """, unsafe_allow_html=True)
            
            # --- BLOQUE 2: ESTADO VIAL NACIONAL (ECU 911 - TOTALMENTE INDEPENDIENTE) ---
            st.markdown("<span style='font-size:11px; font-weight:bold; color:#111; display:block; border-bottom:1px solid #ddd; padding-bottom:2px; margin-top:10px; margin-bottom:4px;'>🪨 Deslaves y Cierres Viales (ECU 911 Nacional)</span>", unsafe_allow_html=True)
            df_vias_911 = obtener_reportes_ecu911_nacional()
            
            # Priorizamos ordenar las CERRADAS primero para llamar la atención del despachador
            df_vias_911["ORDEN"] = df_vias_911["ESTADO"].apply(lambda x: 0 if x == "CERRADA" else 1)
            df_vias_911 = df_vias_911.sort_values(by="ORDEN")
            
            st.markdown('<div style="max-height: 240px; overflow-y: auto; padding-right: 2px;">', unsafe_allow_html=True)
            for _, row in df_vias_911.iterrows():
                color_estado = "#c62828" if row["ESTADO"] == "CERRADA" else "#e65100"
                icono_via = "🛑" if row["ESTADO"] == "CERRADA" else "🚧"
                st.markdown(f"""
                    <div style="font-size:10px; margin-bottom:4px; padding:3px; border-bottom:1px dashed #e0e0e0; background:#fff;">
                        <b style="color:#0d47a1;">[{row['PROVINCIA']}]</b> - {row['VIA']}<br>
                        <span style="color:{color_estado}; font-weight:bold;">{icono_via} {row['ESTADO']}</span>: 
                        <span style="color:#444;">{row['OBS']}</span>
                    </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # --- BLOQUE 3: TRÁFICO SATELITAL EN TIEMPO REAL (TOMTOM) ---
            st.markdown("<span style='font-size:11px; font-weight:bold; color:#111; display:block; border-bottom:1px solid #ddd; padding-bottom:2px; margin-top:10px; margin-bottom:4px;'>🛰️ Incidentes de Tráfico País (TomTom API)</span>", unsafe_allow_html=True)
            
            def consultar_tomtom_nacional():
                bbox_ecuador = "-81.0000,-5.0000,-75.0000,1.5000"
                api_key = "BYGu8JyIsbquMfeU4Cj9P0HidHyxRbE8"
                try:
                    url = "https://api.tomtom.com/traffic/services/5/incidentDetails"
                    params = {"key": api_key, "bbox": bbox_ecuador, "fields": "{incidents{type,properties{description,street}}}", "language": "es-ES"}
                    res = requests.get(url, params=params, timeout=6).json()
                    lista = []
                    if "incidents" in res and res["incidents"]:
                        for incident in res["incidents"][:12]: # Limitamos a los 12 más frescos para guardar simetría
                            props = incident.get("properties", {})
                            calle = props.get("street", "Vía Estatal")
                            desc = props.get("description", "Retraso reportado")
                            lista.append(f"⚠️ Tráfico en {calle}: {desc}")
                    return lista if lista else ["✅ Red vial fluida según satélite."]
                except:
                    return ["⚠️ Servidor TomTom temporalmente ocupado."]

            alertas_trafico = consultar_tomtom_nacional()
            st.markdown('<div style="max-height: 180px; overflow-y: auto;">', unsafe_allow_html=True)
            for trafico in alertas_trafico:
                st.markdown(f"<p style='font-size:9.5px; color:#555; margin:0px 0px 3px 0px; line-height:1.2;'>• {trafico}</p>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True) # Cierre de contenedor estandarizado

else:
    st.error("❌ No se pudo conectar con el servidor de datos de Google Sheets o la estructura de columnas es incorrecta.")
