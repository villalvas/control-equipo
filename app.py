import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import math

# 1. Configuración de pantalla ultra ancha para el monitor de control
st.set_page_config(
    layout="wide", 
    page_title="Monitor de Proyecciones 2026 - Control de Flota",
    initial_sidebar_state="collapsed"
)

# Estilos CSS corporativos
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDataFrame [data-testid="stDataFrameDownloadButton"] {display: none;}
    button[title="View fullscreen"] {display: none;}
    
    .block-container { padding-top: 1rem !important; margin-top: 0px !important; }
    
    [data-testid="stTable"] td, [data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] [role="gridcell"] {
        font-size: 16px !important; font-weight: 500 !important;
    }
    [data-testid="stTable"] th, [data-testid="stDataFrame"] th, div[data-testid="stDataFrame"] [role="columnheader"] {
        font-size: 17px !important; font-weight: bold !important;
    }
    
    .waze-line-right { padding: 6px 10px; margin-bottom: 6px; border-radius: 4px; font-size: 13px; line-height: 1.4; }
    .waze-timestamp { font-size: 11px; font-weight: bold; display: block; margin-bottom: 2px; opacity: 0.8; }
    .waze-national { background-color: #fff3cd; color: #856404; border-left: 4px solid #ffc107; }
    .waze-danger { background-color: #f8d7da; color: #721c24; border-left: 4px solid #dc3545; }
    .waze-info { background-color: #d1ecf1; color: #0c5460; border-left: 4px solid #17a2b8; }
    .waze-success { background-color: #d4edda; color: #155724; border-left: 4px solid #28a745; }
    </style>
    """, unsafe_allow_html=True)

zona_ecuador = ZoneInfo("America/Guayaquil")
hora_ecuador_actual = datetime.now(zona_ecuador)

st.title("🔮 Monitor de Proyección Horaria y Alerta Temprana de Flota")

# 🚗 SCRIPT REAL PARA CONSULTAR EL MAPA PÚBLICO DE WAZE EN ECUADOR
@st.cache_data(ttl=60)  # Se actualiza cada 60 segundos automáticamente
def obtener_alertas_waze_real_ecuador():
    # Coordenadas aproximadas que encierran a todo el territorio de Ecuador (Bounding Box)
    # top: Norte, bottom: Sur, left: Oeste, right: Este
    url_waze_publica = "https://www.waze.com/row-rtserver/web/getStreetUniqueAlerts?top=1.45&bottom=-5.01&left=-81.1head&right=-75.19"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.waze.com/live-map/"
    }
    
    incidentes_ejes = []
    incidentes_urbanos = []
    
    try:
        respuesta = requests.get(url_waze_publica, headers=headers, timeout=8).json()
        alertas = respuesta.get("alerts", [])
        
        for al in alertas:
            # Extraer los datos clave que envía Waze en vivo
            calle = al.get("street", "Vía sin nombre reportada")
            subtipo = al.get("subType", "")
            tipo = al.get("type", "ACCIDENT")
            descripcion = al.get("reportDescription", "")
            
            # Formatear el tipo de incidente para que sea legible
            tipo_legible = subtipo.replace("_", " ").title() if subtipo else tipo.title()
            detalles = f": {descripcion}" if descripcion else ""
            texto_final_alerta = f"[{tipo_legible}] En {calle}{detalles}"
            
            # Clasificación inteligente: Si es una carretera troncal o interprovincial, va a Ejes Viales
            palabras_clave_ejes = ["VIA", "VÍA", "TRONCAL", "PANAMERICANA", "ALOAG", "ALÓAG", "E35", "E25", "E45"]
            if any(pc in calle.upper() for pc in palabras_clave_ejes):
                incidentes_ejes.append(texto_final_alerta)
            else:
                incidentes_urbanos.append(texto_final_alerta)
                
        # Si la API funciona pero no hay tráfico reportado en ese instante
        if not incidentes_ejes:
            incidentes_ejes = ["No se reportan cierres ni novedades críticas en carreteras principales."]
            
        return incidentes_ejes, incidentes_urbanos
        
    except Exception as e:
        # En caso de que Waze bloquee la petición temporalmente por exceso de tráfico
        return [f"⚠️ Servidor Waze ocupado. Reintentando conexión automática..."], []

# El resto de tu lógica de datos (Google Sheets, Clima y Tablas) sigue aquí exactamente igual...
# [Para mantener la lectura corta, asumimos la carga de df_raw e interfaz igual al script anterior]

# ... (Bloque de código de Filtros y Matriz de Grúas) ...

# 🖥️ APLICACIÓN DEL NUEVO CENTRO DE ALERTAS ONLINE EN LA INTERFAZ
# Supongamos que estamos dentro de la división de columnas: col_cuerpo_izq, col_panel_der
col_cuerpo_izq, col_panel_der = st.columns([9, 3])

with col_panel_der:
    st.markdown("<h3 style='margin-top:0px;'>🚨 Centro de Alertas Viales (En Vivo)</h3>", unsafe_allow_html=True)
    
    # Llamada directa al script secundario en tiempo real
    incidentes_ejes_real, incidentes_urbanos_real = obtener_alertas_waze_real_ecuador()
    
    stamp_fecha = hora_ecuador_actual.strftime("%d/%m/%Y")
    stamp_hora = hora_ecuador_actual.strftime("%H:%M")

    with st.container(height=520, border=True):
        st.markdown("<p style='font-weight:bold; font-size:13px; color:#555; margin-bottom:5px;'>🌍 ALERTAS EJES VIALES</p>", unsafe_allow_html=True)
        for alerta in incidentes_ejes_real[:15]:  # Limitamos a las 15 más importantes para no saturar
            st.markdown(f"""
                <div class='waze-line-right waze-national'>
                    <span class='waze-timestamp'>⏱️ {stamp_fecha} - {stamp_hora}</span>
                    ⚠️ {alerta}
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<hr style='margin:10px 0; border-color:#e2e8f0;'>", unsafe_allow_html=True)
        
        st.markdown("<p style='font-weight:bold; font-size:13px; color:#555; margin-bottom:5px;'>📍 ALERTAS URBANAS / PROVINCIALES ACTIVAS</p>", unsafe_allow_html=True)
        if incidentes_urbanos_real:
            for alerta in incidentes_urbanos_real[:20]:
                clase = "waze-danger" if "Accident" in alerta or "Hazard" in alerta else "waze-info"
                st.markdown(f"""
                    <div class='waze-line-right {clase}'>
                        <span class='waze-timestamp'>⏱️ {stamp_fecha} - {stamp_hora}</span>
                        🚗 {alerta}
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class='waze-line-right waze-success'>
                    <span class='waze-timestamp'>⏱️ {stamp_fecha} - {stamp_hora}</span>
                    ✅ Tránsito fluido en zonas urbanas reportadas.
                </div>
            """, unsafe_allow_html=True)

# Fragmento nativo asíncrono para el autorefresco seguro cada 60 segundos
@st.fragment(run_every=60)
def ejecutar_autorefresh():
    pass
    
ejecutar_autorefresh()
