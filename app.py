import streamlit as st
import pandas as pd

# Configuración estética del Dashboard estilo Ejecutivo
st.set_page_config(page_title="Dashboard Operativo Anual", layout="wide", initial_sidebar_state="expanded")

st.title("📊 Tablero de Control Operativo Anual")
st.subheader("Monitoreo estratégico, KPIs y gestión de boletines (Enero - Diciembre)")
st.markdown("---")

# =========================================================================
# CONEXIÓN EN VIVO A GOOGLE DRIVE (CONFIGURACIÓN PARA PESTAÑAS ANUALES)
# =========================================================================
# ⚠️ CAMBIA EL LINK DE ABAJO CON TU ENLACE REAL DEL BOTÓN AZUL "COMPARTIR":
URL_DRIVE = "https://docs.google.com/spreadsheets/d/1aGFtjIeJQ0ZyNCoTvJzfHtM3gQ6JdWKgiVHP5i-Pjj8/edit?usp=sharing"

def cargar_datos_pestana(url, nombre_pestana):
    try:
        csv_url = url.replace('/edit?usp=sharing', f'/gviz/tq?tqx=out:csv&sheet={nombre_pestana}').replace('/edit', f'/gviz/tq?tqx=out:csv&sheet={nombre_pestana}')
        df = pd.read_csv(csv_url)
        df.columns = df.columns.str.strip()  # Limpia espacios rebeldes en los encabezados
        return df
    except Exception as e:
        st.error(f"Error al cargar la pestaña '{nombre_pestana}'. Asegúrate de que el nombre esté escrito exactamente igual en tu Google Sheet.")
        return None

# ---------------------------------------------------------------------
# FILTRO DE MESES AUTOMÁTICO (BARRA LATERAL)
# ---------------------------------------------------------------------
st.sidebar.header("📅 Calendario Operativo")

meses_anuales = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
] 

# Selecciona por defecto "Mayo" como mes inicial
mes_seleccionado = st.sidebar.selectbox("Selecciona el Mes a consultar:", meses_anuales, index=4)

df_raw = cargar_datos_pestana(URL_DRIVE, mes_seleccionado)

if df_raw is not None and not df_raw.empty:
    
    # Asistente inteligente para mapear columnas principales de forma flexible
    def buscar_columna(opciones, df):
        for opcion in opciones:
            for col in df.columns:
                if opcion.lower() in col.lower():
                    return col
        return None

    col_comercial = buscar_columna(['comercial', 'region', 'vendedor', 'zona'], df_raw) or df_raw.columns[0]
    col_cliente = buscar_columna(['cliente', 'institucion', 'empresa', 'cuenta'], df_raw) or df_raw.columns[0]
    
    # Buscamos específicamente tu columna de Odoo
    col_odoo = buscar_columna(['odoo', 'fecha de carga odoo', 'carga odoo'], df_raw)

    # Filtro Secundario por Comercial
    st.sidebar.markdown("---")
    st.sidebar.header("🎯 Filtros de Equipo")
    comerciales_disponibles = ["TODOS"] + list(df_raw[col_comercial].dropna().unique())
    filtro_comercial = st.sidebar.selectbox(f"Filtrar {mes_seleccionado} por Comercial:", comerciales_disponibles)

    df_filtrado = df_raw.copy()
    if filtro_comercial != "TODOS":
        df_filtrado = df_filtrado[df_filtrado[col_comercial] == filtro_comercial]

    # ---------------------------------------------------------------------
    # TARJETAS DE INDICADORES (KPIs) - CORREGIDO BASADO EN ODOO
    # ---------------------------------------------------------------------
    total_boletines = len(df_filtrado)
    
    if col_odoo and col_odoo in df_filtrado.columns:
        # Un caso está terminado si la celda de Odoo NO está vacía (notna) y no contiene solo espacios en blanco
        terminados = len(df_filtrado[df_filtrado[col_odoo].notna() & (df_filtrado[col_odoo].astype(str).str.strip() != "")])
    else:
        st.warning("⚠️ No se encontró una columna que contenga la palabra 'odoo'. Usando conteo por defecto.")
        terminados = 0
        
    pendientes = total_boletines - terminados

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(label=f"📋 Total Casos ({mes_seleccionado})", value=f"{total_boletines} Cuentas")
    with c2:
        avance_pct = int((terminados / total_boletines) * 100) if total_boletines > 0 else 0
        st.metric(label="✅ Cargados en Odoo (Finalizados)", value=f"{terminados} Boletines", delta=f"{avance_pct}% de Eficiencia")
    with c3:
        st.metric(label="⏳ Pendientes de Carga", value=f"{pendientes} Cuentas", delta="Requiere Atención", delta_color="inverse")

    st.markdown("---")

    # ---------------------------------------------------------------------
    # BLOQUE GRÁFICO
    # ---------------------------------------------------------------------
    col_izq, col_der = st.columns([1, 1])

    with col_izq:
        st.write(f"### 📈 Volumen de Cuentas por Comercial - {mes_seleccionado}")
        conteo_comerciales = df_filtrado[col_comercial].value_counts()
        if not conteo_comerciales.empty:
            st.bar_chart(conteo_comerciales)
        else:
            st.info("Sin datos suficientes en este mes para generar gráficos.")

    with col_der:
        st.write("### 📊 Estatus de Carga en Odoo")
        if col_odoo and col_odoo in df_filtrado.columns:
            # Creamos una clasificación rápida en vivo para el gráfico resumido
            status_odoo = df_filtrado[col_odoo].notna() & (df_filtrado[col_odoo].astype(str).str.strip() != "")
            df_status = status_odoo.map({True: "Cargado en Odoo", False: "Pendiente"}).value_counts().to_frame().rename(columns={"index": "Estado", "count": "Cantidad"})
            st.dataframe(df_status, use_container_width=True)
        else:
            st.info("Columna 'fecha de carga odoo' no disponible para resumen.")

    st.markdown("---")

    # Tabla general detallada
    st.write(f"### 🔍 Matriz General del Equipo Operativo ({mes_seleccionado})")
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

else:
    st.warning(f"La pestaña '{mes_seleccionado}' está vacía o aún no ha sido creada en Google Drive. Cuando agregues los datos en tu Excel, el tablero aparecerá automáticamente aquí.")
