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

    # Aplicación de los filtros en cascada
    df_filtrado = df_raw.copy()
    
    if filtro_estatus != "TODOS":
        df_filtrado = df_filtrado[df_filtrado['Estatus de Entrega'] == filtro_estatus]
        
    if filtro_comercial != "TODOS":
        df_filtrado = df_filtrado[df_filtrado[col_comercial] == filtro_comercial]

    # ---------------------------------------------------------------------
    # TARJETAS DE INDICADORES (KPIs)
    # ---------------------------------------------------------------------
    total_boletines_vivos = len(df_raw)
    a_tiempo = len(df_raw[df_raw['Evaluación de Entrega Raw'] == "Entregado a Tiempo"])
    atrasados = len(df_raw[df_raw['Evaluación de Entrega Raw'] == "Entregado Atrasado"])
    formato_var = len(df_raw[df_raw['Evaluación de Entrega Raw'] == "Entregado (Formato Variable)"])
    pendientes = len(df_raw[df_raw['Evaluación de Entrega Raw'] == "Pendiente de Carga"])

    efectividad_pct = int((a_tiempo / total_boletines_vivos) * 100) if total_boletines_vivos > 0 else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(label=f"📋 Total Casos ({mes_seleccionado})
