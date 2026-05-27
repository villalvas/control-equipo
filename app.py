import streamlit as st
import pandas as pd

# Configuración estética del Dashboard estilo Ejecutivo
st.set_page_config(page_title="Control de Boletines", layout="wide", initial_sidebar_state="expanded")

st.title("📊 Control de Boletines")
st.subheader("Monitoreo estratégico, KPIs y control de tiempos de entrega (Enero - Diciembre)")
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
    
    # Mapeo de las dos columnas de fechas críticas
    col_entrega = buscar_columna(['fecha de entrega de boletin', 'entrega de boletin', 'fecha entrega'], df_raw)
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
    # LÓGICA DE AUDITORÍA DE TIEMPOS (PROCESAMIENTO DE FECHAS)
    # ---------------------------------------------------------------------
    if col_entrega and col_odoo and col_entrega in df_filtrado.columns and col_odoo in df_filtrado.columns:
        
        # Convertimos temporalmente las columnas a formato Fecha de forma segura
        f_entrega_parsed = pd.to_datetime(df_filtrado[col_entrega], errors='coerce', dayfirst=True)
        f_odoo_parsed = pd.to_datetime(df_filtrado[col_odoo], errors='coerce', dayfirst=True)
        
        # Función interna para clasificar cada fila en tiempo real
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

        # Aplicamos la clasificación limpia sin emojis internos para cálculo seguro
        df_filtrado['Evaluación de Entrega Raw'] = [clasificar_tiempo(row, idx) for idx, row in df_filtrado.iterrows()]
        
        # Versión visual con emojis para las tablas del reporte gráfico
        mapeo_emojis = {
            "Pendiente de Carga": "⏳ Pendiente de Carga",
            "Entregado Atrasado": "⚠️ Entregado Atrasado",
            "Entregado a Tiempo": "🚀 Entregado a Tiempo",
            "Entregado (Formato Variable)": "✅ Entregado (Formato Variable)"
        }
        df_filtrado['Evaluación de Entrega'] = df_filtrado['Evaluación de Entrega Raw'].map(mapeo_emojis)
    else:
        st.warning("⚠️ Mapeo incompleto. Asegúrate de tener las columnas 'fecha de entrega de boletin' y 'fecha de carga odoo'.")
        df_filtrado['Evaluación de Entrega Raw'] = "Pendiente de Carga"
        df_filtrado['Evaluación de Entrega'] = "⏳ Pendiente de Carga"

    # ---------------------------------------------------------------------
    # TARJETAS DE INDICADORES (KPIs) AJUSTADAS
    # ---------------------------------------------------------------------
    total_boletines = len(df_filtrado)
    a_tiempo = len(df_filtrado[df_filtrado['Evaluación de Entrega Raw'] == "Entregado a Tiempo"])
    atrasados = len(df_filtrado[df_filtrado['Evaluación de Entrega Raw'] == "Entregado Atrasado"])
    pendientes = len(df_filtrado[df_filtrado['Evaluación de Entrega Raw'] == "Pendiente de Carga"])

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(label=f"📋 Total Casos ({mes_seleccionado})", value=f"{total_boletines} Cuentas")
    with c2:
        eficiencia_pct = int((a_tiempo / total_boletines) * 100) if total_boletines > 0 else 0
        st.metric(label="🚀 Eficiencia (A Tiempo)", value=f"{a_tiempo} Boletines", delta=f"{eficiencia_pct}% Puntualidad")
    with c3:
        st.metric(label="⏳ Pendientes de Carga", value=f"{pendientes} Activos", delta=f"{atrasados} con Retraso", delta_color="inverse")

    st.markdown("---")

    # ---------------------------------------------------------------------
    # BLOQUE GRÁFICO DE TIEMPOS
    # ---------------------------------------------------------------------
    col_izq, col_der = st.columns([1, 1])

    with col_izq:
        st.write(f"### 📈 Volumen de Cuentas por Comercial - {mes_seleccionado}")
        conteo_comerciales = df_filtrado[col_comercial].value_counts()
        if not conteo_comerciales.empty:
            st.bar_chart(conteo_comerciales)
        else:
            st.info("Sin datos suficientes.")

    with col_der:
        st.write("### 📊 Auditoría de SLA (Tiempos de Respuesta)")
        conteo_tiempos = df_filtrado['Evaluación de Entrega'].value_counts().to_frame().rename(columns={'Evaluación de Entrega': "Cantidad"})
        st.dataframe(conteo_tiempos, use_container_width=True)

    st.markdown("---")

    # Tabla general detallada
    st.write(f"### 🔍 Matriz General del Equipo Operativo ({mes_seleccionado})")
    st.dataframe(df_filtrado.drop(columns=['Evaluación de Entrega Raw'], errors='ignore'), use_container_width=True, hide_index=True)

else:
    st.warning(f"La pestaña '{mes_seleccionado}' está vacía o aún no ha sido creada en Google Drive. Cuando agregues los datos en tu Excel, el tablero aparecerá automáticamente aquí.")
