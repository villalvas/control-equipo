import streamlit as st
import pandas as pd
import plotly.express as px  # Librería para los gráficos interactivos

# Configuración estética del Dashboard estilo Ejecutivo
st.set_page_config(page_title="Control de Boletines", layout="wide", initial_sidebar_state="expanded")

st.title("📊 Control de Boletines")
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
        df.columns = df.columns.str.strip()  # Limpia espacios en los encabezados
        return df
    except Exception as e:
        st.error(f"Error al cargar la pestaña '{nombre_pestana}'. Asegúrate de que el nombre esté escrito exactamente igual.")
        return None

# ---------------------------------------------------------------------
# FILTROS DE LA BARRA LATERAL IZQUIERDA
# ---------------------------------------------------------------------
st.sidebar.header("📅 Calendario Operativo")

meses_anuales = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
] 

# 1. Filtro de Mes
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
    col_entrega = buscar_columna(['fecha de entrega de boletin', 'entrega de boletin', 'fecha entrega'], df_raw)
    col_odoo = buscar_columna(['odoo', 'fecha de carga odoo', 'carga odoo'], df_raw)
    col_grupo = buscar_columna(['grupoarea', 'grupo area', 'grupo', 'area'], df_raw) or df_raw.columns[0]
    col_recurrencia = buscar_columna(['recurrencia de boletin', 'recurrencia', 'periodo'], df_raw) or df_raw.columns[0]
    
    # Identificar la nueva columna de observaciones por retraso de forma flexible
    col_observacion = buscar_columna(['observacion retraso', 'observaciones retraso', 'observacion'], df_raw)

    # ---------------------------------------------------------------------
    # LÓGICA DE AUDITORÍA DE TIEMPOS (PROCESAMIENTO DE FECHAS)
    # ---------------------------------------------------------------------
    if col_entrega and col_odoo and col_entrega in df_raw.columns and col_odoo in df_raw.columns:
        f_entrega_parsed = pd.to_datetime(df_raw[col_entrega], errors='coerce', dayfirst=True)
        f_odoo_parsed = pd.to_datetime(df_raw[col_odoo], errors='coerce', dayfirst=True)
        
        def clasificar_tiempo(fila, idx):
            val_odoo = fila[col_odoo]
            if pd.isna(val_odoo) or str(val_odoo).strip() == "":
                return "Pendiente de Carga"
            
            date_entrega = f_entrega_parsed.loc[idx]
            date_odoo = f_odoo_parsed.loc[idx]
            
            if pd.isna(date_entrega) or pd.isna(date_odoo):
                return "Entregado (Formato Variable)"
            
            if date_odoo > date_entrega:
                return "Entregado Atrasado"
            else:
                return "Entregado a Tiempo"

        df_raw['Evaluación de Entrega Raw'] = [clasificar_tiempo(row, idx) for idx, row in df_raw.iterrows()]
        
        mapeo_emojis = {
            "Pendiente de Carga": "⏳ Pendiente de Carga",
            "Entregado Atrasado": "⚠️ Entregado Atrasado",
            "Entregado a Tiempo": "🚀 Entregado a Tiempo",
            "Entregado (Formato Variable)": "✅ Entregado (Formato Variable)"
        }
        df_raw['Estatus de Entrega'] = df_raw['Evaluación de Entrega Raw'].map(mapeo_emojis)
    else:
        df_raw['Evaluación de Entrega Raw'] = "Pendiente de Carga"
        df_raw['Estatus de Entrega'] = "⏳ Pendiente de Carga"

    # 2. Filtro Lateral Interactivos de Estatus
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtrar Clientes por Estado")
    opciones_estatus = ["TODOS", "🚀 Entregado a Tiempo", "⚠️ Entregado Atrasado", "⏳ Pendiente de Carga"]
    filtro_estatus = st.sidebar.selectbox("Selecciona un Estatus:", opciones_estatus)

    # 3. Filtro de Comercial
    st.sidebar.markdown("---")
    st.sidebar.header("🎯 Filtros de Equipo")
    comerciales_disponibles = ["TODOS"] + list(df_raw[col_comercial].dropna().unique())
    filtro_comercial = st.sidebar.selectbox(f"Filtrar por Comercial:", comerciales_disponibles)

    # 4. Filtro Lateral de Recurrencia
    st.sidebar.markdown("---")
    st.sidebar.header("🔄 Frecuencia de Entrega")
    recurrencias_disponibles = ["TODOS"]
    if col_recurrencia in df_raw.columns:
        recurrencias_disponibles += list(df_raw[col_recurrencia].dropna().unique())
    filtro_recurrencia = st.sidebar.selectbox("Selecciona Recurrencia:", recurrencias_disponibles)

    # ---------------------------------------------------------------------
    # APLICACIÓN DE FILTROS EN CASCADA Y CÁLCULO BASE DEL TOTAL
    # ---------------------------------------------------------------------
    df_base_universo = df_raw.copy()
    if filtro_recurrencia != "TODOS":
        df_base_universo = df_base_universo[df_base_universo[col_recurrencia] == filtro_recurrencia]

    total_boletines_vivos = len(df_base_universo)

    df_filtrado = df_base_universo.copy()
    if filtro_estatus != "TODOS":
        df_filtrado = df_filtrado[df_filtrado['Estatus de Entrega'] == filtro_estatus]
    if filtro_comercial != "TODOS":
        df_filtrado = df_filtrado[df_filtrado[col_comercial] == filtro_comercial]

    # ---------------------------------------------------------------------
    # TARJETAS DE INDICADORES (KPIs)
    # ---------------------------------------------------------------------
    a_tiempo = len(df_base_universo[df_base_universo['Evaluación de Entrega Raw'] == "Entregado a Tiempo"])
    atrasados = len(df_base_universo[df_base_universo['Evaluación de Entrega Raw'] == "Entregado Atrasado"])
    pendientes = len(df_base_universo[df_base_universo['Evaluación de Entrega Raw'] == "Pendiente de Carga"])

    efectividad_pct = int((a_tiempo / total_boletines_vivos) * 100) if total_boletines_vivos > 0 else 0

    c1, c2, r_col3 = st.columns(3)
    with c1:
        st.metric(label="Total Casos del Mes", value=f"{total_boletines_vivos} Cuentas")
    with c2:
        st.metric(label="Efectividad de Gestión", value=f"{efectividad_pct}% A Tiempo", delta=f"{a_tiempo} de {total_boletines_vivos} Boletines")
    with r_col3:
        st.metric(label="Pendientes de Carga", value=f"{pendientes} Pendientes", delta=f"{atrasados} con Retraso", delta_color="inverse")

    st.markdown("---")

    # =========================================================================
    # DISEÑO ROBUSTO EN PARALELO: GRÁFICO (40%) | TABLA INTEGRAL DETALLADA (60%)
    # =========================================================================
    col_grafico, col_tabla = st.columns([4, 6])

    # --- COLUMNA IZQUIERDA: GRÁFICO DE SLA AL 40% ---
    with col_grafico:
        st.write("### 📊 Auditoría de SLA")
        
        conteo_tiempos = df_filtrado['Estatus de Entrega'].value_counts().reset_index()
        conteo_tiempos.columns = ['Estatus de Entrega', 'Cantidad']
        
        if not conteo_tiempos.empty:
            conteo_tiempos['Porcentaje'] = ((conteo_tiempos['Cantidad'] / total_boletines_vivos) * 100).round(1)
            conteo_tiempos['Etiqueta'] = conteo_tiempos.apply(lambda r: f"{r['Cantidad']} ({r['Porcentaje']}%)", axis=1)
            
            fig_sla = px.bar(conteo_tiempos, x
