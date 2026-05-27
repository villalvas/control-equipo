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
        # Formateamos el URL para extraer la pestaña seleccionada por su nombre
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

# Ya quedan definidos los 12 meses del año. 
# NOTA: En tu Drive, las pestañas deben llamarse exactamente así (Enero, Febrero, Marzo...)
meses_anuales = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
] 

# Selecciona por defecto "Mayo" que es el mes actual para que no aparezca vacío
mes_seleccionado = st.sidebar.selectbox("Selecciona el Mes a consultar:", meses_anuales, index=4)

# Cargamos la data del mes elegido
df_raw = cargar_datos_pestana(URL_DRIVE, mes_seleccionado)

if df_raw is not None and not df_raw.empty:
    
    # Asistente inteligente para mapear columnas (Comercial, Gestión, Cliente)
    def buscar_columna(opciones, df):
        for opcion in opciones:
            for col in df.columns:
                if opcion.lower() in col.lower():
                    return col
        return None

    col_comercial = buscar_columna(['comercial', 'region', 'vendedor', 'zona'], df_raw) or df_raw.columns[0]
    col_gestion = buscar_columna(['gestion', 'novedad', 'estado', 'estatus', 'etapa'], df_raw) or df_raw.columns[0]
    col_cliente = buscar_columna(['cliente', 'institucion', 'empresa', 'cuenta'], df_raw) or df_raw.columns[0]

    # Filtro Secundario por Comercial
    st.sidebar.markdown("---")
    st.sidebar.header("🎯 Filtros de Equipo")
    comerciales_disponibles = ["TODOS"] + list(df_raw[col_comercial].dropna().unique())
    filtro_comercial = st.sidebar.selectbox(f"Filtrar {mes_seleccionado} por Comercial:", comerciales_disponibles)

    df_filtrado = df_raw.copy()
    if filtro_comercial != "TODOS":
        df_filtrado = df_filtrado[df_filtrado[col_comercial] == filtro_comercial]

    # ---------------------------------------------------------------------
    # TARJETAS DE INDICADORES (KPIs)
    # ---------------------------------------------------------------------
    total_boletines = len(df_filtrado)
    terminados = len(df_filtrado[df_filtrado[col_gestion].astype(str).str.contains('termina|finalizado|ok|hecho|entregado', na=False, case=False)])
    pendientes = total_boletines - terminados

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(label=f"📋 Total Casos ({mes_seleccionado})", value=f"{total_boletines} Cuentas")
    with c2:
        avance_pct = int((terminados / total_boletines) * 100) if total_boletines > 0 else 0
        st.metric(label="✅ Gestión Finalizada", value=f"{terminados} Boletines", delta=f"{avance_pct}% de Eficiencia")
    with c3:
        st.metric(label="⏳ Pendientes de Gestión", value=f"{pendientes} Cuentas", delta="Requires Atención", delta_color="inverse")

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
        st.write("### 📊 Resumen Ejecutivo de Estatus")
        conteo_estados = df_filtrado[col_gestion].value_counts().to_frame().rename(columns={col_gestion: "Cantidad"})
        st.dataframe(conteo_estados, use_container_width=True)

    st.markdown("---")

    # Tabla general detallada
    st.write(f"### 🔍 Matriz General del Equipo Operativo ({mes_seleccionado})")
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

else:
    st.warning(f"La pestaña '{mes_seleccionado}' está vacía o aún no ha sido creada en Google Drive. Cuando agregues los datos en tu Excel, el tablero aparecerá automáticamente aquí.")
