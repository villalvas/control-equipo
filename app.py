import streamlit as st
import pandas as pd

# Configuración de la página del navegador
st.set_page_config(page_title="Control Operativo - Mafer", layout="wide")

st.title("📊 Panel de Control Operativo Real (Data en Vivo de Drive)")
st.subheader("Herramienta de soporte basada en la gestión de boletines de Mayo 2026")
st.markdown("---")

# =========================================================================
# CONEXIÓN EN VIVO A GOOGLE DRIVE
# =========================================================================
# ⚠️ REEMPLAZA EL LINK DE ABAJO CON TU ENLACE REAL DE GOOGLE SHEETS:
URL_DRIVE = "https://docs.google.com/spreadsheets/d/1aGFtjIeJQ0ZyNCoTvJzfHtM3gQ6JdWKgiVHP5i-Pjj8/edit?usp=sharing"

def cargar_datos_drive(url):
    try:
        # Transforma el enlace compartido en un formato de descarga CSV que Streamlit lee directo
        csv_url = url.replace('/edit?usp=sharing', '/gviz/tq?tqx=out:csv').replace('/edit', '/gviz/tq?tqx=out:csv')
        return pd.read_csv(csv_url)
    except Exception as e:
        st.error(f"Error al conectar con Google Drive. Revisa el enlace compartido. Detalle: {e}")
        return None

# Carga de la información desde tu Google Drive
df_mafer_vivo = cargar_datos_drive(URL_DRIVE)

if df_mafer_vivo is not None:
    # 1. Filtramos para ver solo las cuentas del cronograma activo de Mafer
    df_activo = df_mafer_vivo[df_mafer_vivo['fecha de entrega inicial CRONOGRAMA'].notna()]
    df_activo = df_activo[df_activo['fecha de entrega inicial CRONOGRAMA'] != 'ninguna']
    
    # 2. Cálculo de métricas en tiempo real según tu columna "novedad gestion"
    pendientes = len(df_activo[df_activo['novedad gestion'] == 'gestion a realizar'])
    terminados = len(df_activo[df_activo['novedad gestion'].str.contains('terminada', na=False, case=False)])
    
    # Alertas basadas en los días críticos de mayo del archivo
    alertas = len(df_activo[df_activo['fecha de entrega inicial CRONOGRAMA'].str.contains('2026-05-07|2026-05-08|2026-05-10', na=False)])

    # 3. Despliegue de los indicadores (KPIs) en la parte superior
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="✅ Boletines Entregados", value=f"{terminados} Cuentas")
    with col2:
        st.metric(label="⏳ Gestiones Pendientes", value=f"{pendientes} Cuentas", delta="Falta trabajar", delta_color="inverse")
    with col3:
        st.metric(label="⚠️ Vencimientos Críticos (Mayo 7 al 10)", value=f"{alertas} Casos", delta="¡Atención Líder!", delta_color="inverse")
        
    st.markdown("---")
    
    # 4. Buscador y Filtro Comercial interactivo para el líder
    st.write("### 🔍 Buscador y Filtro Comercial")
    sucursales_disponibles = ["TODOS"] + list(df_activo['COMERCIAL'].dropna().unique())
    sucursal_seleccionada = st.selectbox("Filtrar por Región Comercial:", sucursales_disponibles)
    
    df_mostrar = df_activo.copy()
    if sucursal_seleccionada != "TODOS":
        df_mostrar = df_activo[df_activo['COMERCIAL'] == sucursal_seleccionada]
        
    # 5. Visualización de la Tabla de Datos Pulida
    st.write(f"Mostrando {len(df_mostrar)} boletines activos en el cronograma:")
    columnas_interes = ['GRUPO', 'COMERCIAL', 'CLIENTE INSTITUCIONAL', 'fecha de entrega inicial CRONOGRAMA', 'fecha CARGA en ODOO', 'novedad gestion']
    st.data_editor(df_mostrar[columnas_interes], use_container_width=True)
    
    # 6. Alerta dinámica de Plan de Acción
    if alertas > 0:
        st.error(f"🚨 **Alerta para el Líder (Plan de Acción Rankmi):** Se detectan {alertas} boletines acumulados en fechas críticas. Es necesario aplicar el rito de alineación corta (Daily) con Mafer para coordinar apoyos y evitar retrasos de carga en ODOO.")
else:
    st.warning("Por favor ingresa un enlace válido de Google Sheets en el archivo de código para mostrar el tablero.")
