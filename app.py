import streamlit as st
import pandas as pd

# Configuración estética del Dashboard estilo Ejecutivo
st.set_page_config(page_title="Dashboard Operativo", layout="wide", initial_sidebar_state="expanded")

st.title("📊 Tablero de Control Operativo Avanzado (Data en Vivo)")
st.subheader("Monitoreo estratégico, KPIs y gestión de boletines del equipo")
st.markdown("---")

# =========================================================================
# CONEXIÓN EN VIVO A GOOGLE DRIVE
# =========================================================================
# ⚠️ CAMBIA EL LINK DE ABAJO CON TU ENLACE REAL DEL BOTÓN AZUL "COMPARTIR":
URL_DRIVE = "https://docs.google.com/spreadsheets/d/1aGFtjIeJQ0ZyNCoTvJzfHtM3gQ6JdWKgiVHP5i-Pjj8/edit?usp=sharing"

def cargar_datos_drive(url):
    try:
        csv_url = url.replace('/edit?usp=sharing', '/gviz/tq?tqx=out:csv').replace('/edit', '/gviz/tq?tqx=out:csv')
        df = pd.read_csv(csv_url)
        df.columns = df.columns.str.strip()  # Limpia espacios rebeldes en los encabezados
        return df
    except Exception as e:
        st.error(f"Error al conectar con Google Drive. Detalle: {e}")
        return None

df_raw = cargar_datos_drive(URL_DRIVE)

if df_raw is not None:
    # ---------------------------------------------------------------------
    # ASISTENTE DETECTOR DE COLUMNAS (Para mapear tus nuevos campos)
    # ---------------------------------------------------------------------
    def buscar_columna(opciones, df):
        for opcion in opciones:
            for col in df.columns:
                if opcion.lower() in col.lower():
                    return col
        return None

    # Buscamos campos clave de forma flexible (mayúsculas, minúsculas o nombres similares)
    col_comercial = buscar_columna(['comercial', 'region', 'vendedor', 'zona'], df_raw) or df_raw.columns[0]
    col_gestion = buscar_columna(['gestion', 'novedad', 'estado', 'estatus', 'etapa'], df_raw) or df_raw.columns[0]
    col_cliente = buscar_columna(['cliente', 'institucion', 'empresa', 'cuenta'], df_raw) or df_raw.columns[0]

    # ---------------------------------------------------------------------
    # SECCIÓN DE FILTROS (BARRA LATERAL)
    # ---------------------------------------------------------------------
    st.sidebar.header("🎯 Filtros Estratégicos")
    
    # Filtro 1: Comercial
    comerciales_disponibles = ["TODOS"] + list(df_raw[col_comercial].dropna().unique())
    filtro_comercial = st.sidebar.selectbox("Filtrar por Comercial / Región:", comerciales_disponibles)

    # Filtro 2: Estado de Gestión (¡Dinámico según tus nuevos datos!)
    estados_disponibles = ["TODOS"] + list(df_raw[col_gestion].dropna().unique())
    filtro_estado = st.sidebar.selectbox("Filtrar por Estado de Gestión:", estados_disponibles)

    # Aplicamos los filtros a la data en cascada
    df_filtrado = df_raw.copy()
    if filtro_comercial != "TODOS":
        df_filtrado = df_filtrado[df_filtrado[col_comercial] == filtro_comercial]
    if filtro_estado != "TODOS":
        df_filtrado = df_filtrado[df_filtrado[col_gestion] == filtro_estado]

    # ---------------------------------------------------------------------
    # TARJETAS DE INDICADORES (KPIs)
    # ---------------------------------------------------------------------
    total_boletines = len(df_filtrado)
    
    # Conteo inteligente de terminados y pendientes
    terminados = len(df_filtrado[df_filtrado[col_gestion].astype(str).str.contains('termina|finalizado|ok|hecho|entregado', na=False, case=False)])
    pendientes = total_boletines - terminados

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(label="📋 Total Casos Filtrados", value=f"{total_boletines} Cuentas")
    with c2:
        avance_pct = int((terminados / total_boletines) * 100) if total_boletines > 0 else 0
        st.metric(label="✅ Gestión Finalizada", value=f"{terminados} Boletines", delta=f"{avance_pct}% de Eficiencia")
    with c3:
        st.metric(label="⏳ Pendientes de Carga / Gestión", value=f"{pendientes} Cuentas", delta="Requiere Seguimiento", delta_color="inverse")

    st.markdown("---")

    # ---------------------------------------------------------------------
    # BLOQUE GRÁFICO (Muestra la distribución comercial y de estados)
    # ---------------------------------------------------------------------
    col_izq, col_der = st.columns([1, 1])

    with col_izq:
        st.write("### 📈 Cuentas Asignadas por Comercial")
        conteo_comerciales = df_filtrado[col_comercial].value_counts()
        if not conteo_comerciales.empty:
            st.bar_chart(conteo_comerciales)
        else:
            st.info("Sin datos para graficar.")

    with col_der:
        st.write("### 📊 Resumen Ejecutivo de Estatus")
        conteo_estados = df_filtrado[col_gestion].value_counts().to_frame().rename(columns={col_gestion: "Cantidad"})
        st.dataframe(conteo_estados, use_container_width=True)

    st.markdown("---")

    # ---------------------------------------------------------------------
    # VISTA TOTAL DE LA DATA (Incluye automáticamente tus nuevos campos)
    # ---------------------------------------------------------------------
    st.write("### 🔍 Matriz del Equipo Operativo (Columnas Dinámicas)")
    st.write(f"Mostrando un total de **{len(df_filtrado)}** registros coincidentes.")
    
    # Desplegamos toda la tabla con opción de búsqueda integrada por Streamlit
    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

else:
    st.warning("Estableciendo conexión segura con Google Drive... Por favor verifica el link del archivo.")
