import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta

# =============================================================================
# 1. CONFIGURACIÓN DE PÁGINA E INTERFAZ (Estilo Sala de Control)
# =============================================================================
st.set_page_config(
    page_title="Tablero Control de Operaciones",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inyección de estilos CSS para un diseño compacto y limpio
st.markdown(
    """
    <style>
    [data-testid="stHeader"] {background-color: rgba(0,0,0,0); height: 2.5rem;}
    .block-container {padding-top: 1rem; padding-bottom: 0rem; max-width: 98%;}
    div[data-testid="stExpander"] div[role="button"] p { font-size: 11px !important; font-weight: bold; }
    .card-saldo {
        background-color: #f8f9fa;
        padding: 6px;
        border-radius: 4px;
        border-left: 3px solid #007bff;
        margin-top: 5px;
        text-align: center;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =============================================================================
# 2. INICIALIZACIÓN DEL ESTADO GLOBAL DE LA APP (Limpio de Waze)
# =============================================================================
@st.cache_resource
def inicializar_estado_global():
    return {
        "alertas_vias": [],
        "ultima_hora_vias": "Nunca"
    }

estado_global = inicializar_estado_global()
ahora_actual = datetime.now()

# Diccionario geográfico para consultas de contexto
coordenadas_provincias = {
    "PICHINCHA": (-0.2299, -78.5249), "GUAYAS": (-2.1894, -79.8894),
    "AZUAY": (-2.9001, -79.0045), "MANABI": (-1.0546, -80.4542),
    "LOS_RIOS": (-1.4558, -79.4623), "EL_ORO": (-3.2581, -79.9552),
    "LOJA": (-3.9931, -79.2042), "TUNGURAHUA": (-1.2491, -78.6168),
    "CHIMBORAZO": (-1.6744, -78.6483), "ESMERALDAS": (0.9682, -79.6517),
    "SANTO_DOMINGO": (-0.2530, -79.1754), "SANTA_ELENA": (-2.2262, -80.8584),
    "COTOPAXI": (-0.9352, -78.6155), "IMBABURA": (0.3392, -78.1222),
    "CARCHI": (0.7384, -77.7299), "BOLIVAR": (-1.5911, -79.0022),
    "CAÑAR": (-2.7397, -78.8486), "PASTAZA": (-1.4871, -77.9944),
    "MORONA_SANTIAGO": (-2.3087, -78.1184), "NAPO": (-0.9938, -77.8129),
    "ORELLANA": (-0.4665, -76.9872), "SUCUMBIOS": (0.0847, -76.8828),
    "ZAMORA_CHINCHIPE": (-4.0692, -78.9567)
}

# =============================================================================
# 3. BARRA SUPERIOR DE INFORMACIÓN
# =============================================================================
c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
with c1:
    st.markdown(f"**📅 Fecha:** {ahora_actual.strftime('%Y-%m-%d')}")
with c2:
    st.markdown(f"**⏰ Servidor:** {ahora_actual.strftime('%I:%M %p')}")
with c3:
    st.markdown("**📌 Estado de Red:** Operativo")
with c4:
    st.markdown("**🛡️ Nivel de Alerta:** Normal")

st.markdown("---")

# =============================================================================
# 4. SISTEMA DE PESTAÑAS PRINCIPALES
# =============================================================================
pestana_operacion, pestana_feriados, pestana_graficos = st.tabs([
    "🚛 Operación Diaria", 
    "📅 Planificación & Feriados", 
    "📈 Métricas & Gráficos"
])

# -----------------------------------------------------------------------------
# PESTAÑA A: OPERACIÓN DIARIA
# -----------------------------------------------------------------------------
with pestana_operacion:
    st.subheader("Monitoreo de Flujos y Canales Continentales")
    
    col_izq, col_der = st.columns([2, 1])
    
    with col_izq:
        st.markdown("### Resumen de Flotas Ejecutadas")
        # Simulación de DataFrame Operativo base
        df_operaciones = pd.DataFrame({
            "Ruta / Canal": ["Troncal Costa", "E20 Aloag", "Vía Puerto", "Perimetral"],
            "Unidades": [14, 22, 8, 19],
            "Estado": ["Fluido", "Retraso Moderado", "Fluido", "Fluido"]
        })
        st.dataframe(df_operaciones, use_container_width=True, hide_index=True)

    with col_der:
        st.markdown("### 🚦 Alertas TomTom Traffic")
        
        c_w1, c_w2 = st.columns([1, 2])
        
        with c_w1:
            ejecutar_consulta = st.button(
                "🔍 Escanear Vías",
                use_container_width=True,
                key="btn_tomtom_vias"
            )

            if ejecutar_consulta:
                def consultar_alertas_tomtom_nacional():
                    # TODO: Pon tu API Key real de TomTom Developers aquí
                    api_key_tomtom = "TU_API_KEY_TOMTOM"
                    alertas = []
                    
                    # Bounding Box única de Ecuador Continental (evita bucles pesados)
                    bbox_ecuador = "-81.0000,-5.0000,-75.0000,1.5000"
                    zoom_sala_control = "7" 
                    
                    try:
                        url = f"https://api.tomtom.com/traffic/services/5/incidentDetails/s3/{bbox_ecuador}/{zoom_sala_control}/-1/json"
                        params = {"key": api_key_tomtom, "language": "es-ES"}
                        
                        respuesta = requests.get(url, params=params, timeout=8).json()

                        if "tm" in respuesta and "poi" in respuesta["tm"]:
                            # Mapeamos los 4 incidentes críticos reportados
                            for item in respuesta["tm"]["poi"][:4]:
                                descripcion = item.get("description", "Vía afectada")
                                fclass = item.get("fclass", 0)
                                
                                if fclass in [1, 2]:
                                    icono = "⚠️"
                                elif fclass == 3:
                                    icono = "🚧"
                                else:
                                    icono = "🚦"

                                alertas.append(f"{icono} {descripcion[:45]}")
                        
                        return alertas if alertas else ["✅ Sin incidentes relevantes"]
                    except Exception:
                        return ["⚠️ Error consultando tráfico TomTom"]

                estado_global["alertas_vias"] = consultar_alertas_tomtom_nacional()
                estado_global["ultima_hora_vias"] = ahora_actual.strftime('%I:%M %p')
                st.rerun()

            st.markdown(
                """
                <div class="card-saldo">
                <span style="font-size:9px;color:#212529;font-weight:600;">TomTom Data Online</span>
                </div>
                """,
                unsafe_allow_html=True
            )

        with c_w2:
            st.markdown(
                f"""
                <span style='font-size:9px;color:#777'>
                Último análisis: {estado_global.get('ultima_hora_vias','Nunca')}
                </span>
                """,
                unsafe_allow_html=True
            )

            if not estado_global.get("alertas_vias"):
                st.markdown(
                    "<span style='font-size:9px;color:#999'>• Presione escanear para revisar vías</span>",
                    unsafe_allow_html=True
                )
            else:
                for incidente in estado_global["alertas_vias"]:
                    st.markdown(
                        f"""
                        <span style='font-size:9px; color:#d32f2f; font-weight:500;'>
                        • {incidente}
                        </span>
                        """,
                        unsafe_allow_html=True
                    )

# -----------------------------------------------------------------------------
# PESTAÑA B: PLANIFICACIÓN Y FERIADOS
# -----------------------------------------------------------------------------
with pestana_feriados:
    st.subheader("Calendario de Feriados Nacionales y Restricciones")
    
    # Base de datos estática de feriados nacionales ecuatorianos
    df_feriados = pd.DataFrame({
        "Fecha Feriado": ["2026-01-01", "2026-02-16", "2026-02-17", "2026-04-03", "2026-05-01", "2026-05-24"],
        "Festividad": ["Año Nuevo", "Carnaval", "Carnaval", "Viernes Santo", "Día del Trabajo", "Batalla de Pichincha"],
        "Impacto Logístico": ["Alto", "Crítico", "Crítico", "Medio", "Alto", "Bajo"]
    })
    
    st.markdown("Próximos eventos que impactan el transporte de carga pesada:")
    st.dataframe(df_feriados, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# PESTAÑA C: MÉTRICAS Y GRÁFICOS (Sección que faltaba completar)
# -----------------------------------------------------------------------------
with pestana_graficos:
    st.subheader("Análisis de Rendimiento de Flujo Semanal")
    
    # Reconstrucción de la data del gráfico donde se cortó el código anterior
    data_graf = {
        "Fecha": pd.date_range(end=datetime.today(), periods=7).strftime('%Y-%m-%d'),
        "Flujo_Esperado": np.random.randint(100, 150, size=7),
        "Flujo_Real": np.random.randint(95, 145, size=7)
    }

    df_gf = pd.DataFrame(data_graf)
    df_gf.set_index("Fecha", inplace=True)
    
    # Renderizado de gráfico de líneas nativo de Streamlit
    st.line_chart(df_gf, use_container_width=True)
    st.caption("Gráfico interactivo de variaciones de flujos de transporte: Esperado vs Real.")
