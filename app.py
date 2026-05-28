import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración estética del Dashboard estilo Ejecutivo
st.set_page_config(page_title="Control de Boletines", layout="wide", initial_sidebar_state="expanded")

st.title("📊 Control de Boletines")
st.markdown("---")

# =========================================================================
# CONEXIÓN EN VIVO A GOOGLE DRIVE
# =========================================================================
# ⚠️ RECUERDA CAMBIAR EL LINK DE ABAJO CON TU ENLACE REAL DE DRIVE:
URL_DRIVE = "https://docs.google.com/spreadsheets/d/1aGFtjIeJQ0ZyNCoTvJzfHtM3gQ6JdWKgiVHP5i-Pjj8/edit?usp=sharing"

def cargar_datos_pestana(url, nombre_pestana):
    try:
        csv_url = url.replace('/edit?usp=sharing', f'/gviz/tq?tqx=out:csv&sheet={nombre_pestana}').replace('/edit', f'/gviz/tq?tqx=out:csv&sheet={nombre_pestana}')
        df = pd.read_csv(csv_url)
        df.columns = df.columns.str.strip()  # Limpia espacios en blanco en los encabezados
        return df
    except Exception as e:
        st.error(f"Error al cargar la pestaña '{nombre_pestana}'. Verifica que el nombre en Drive sea exacto.")
        return None

# ---------------------------------------------------------------------
# FILTROS DE LA BARRA LATERAL IZQUIERDA
# ---------------------------------------------------------------------
st.sidebar.header("📅 Calendario Operativo")

meses_anuales = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
] 

mes_seleccionado = st.sidebar.selectbox("Selecciona el Mes a consultar:", meses_anuales, index=4)

df_raw = cargar_datos_pestana(URL_DRIVE, mes_seleccionado)

if df_raw is not None and not df_raw.empty:
    
    # Asistente inteligente para mapear columnas dinámicas de la hoja
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
    col_observacion = buscar_columna(['observacion retraso', 'observaciones retraso', 'observacion'], df_raw)
    
    # Mapeo flexible para la columna de límites de entrega
    col_dias_max = buscar_columna(['dias maximas', 'dias maximos', 'dias maxima', 'dias maximo', 'maximas', 'maximos'], df_raw)

    # ---------------------------------------------------------------------
    # LÓGICA DE AUDITORÍA DE TIEMPOS (SLA)
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

    # Filtros Secundarios en Barra Lateral
    st.sidebar.markdown("---")
    st.sidebar.header("🔍 Filtrar Clientes por Estado")
    opciones_estatus = ["TODOS", "🚀 Entregado a Tiempo", "⚠️ Entregado Atrasado", "⏳ Pendiente de Carga"]
    filtro_estatus = st.sidebar.selectbox("Selecciona un Estatus:", opciones_estatus)

    st.sidebar.markdown("---")
    st.sidebar.header("🎯 Filtros de Equipo")
    comerciales_disponibles = ["TODOS"] + list(df_raw[col_comercial].dropna().unique())
    filtro_comercial = st.sidebar.selectbox("Filtrar por Comercial:", comerciales_disponibles)

    st.sidebar.markdown("---")
    st.sidebar.header("🔄 Frecuencia de Entrega")
    recurrencias_disponibles = ["TODOS"]
    if col_recurrencia in df_raw.columns:
        recurrencias_disponibles += list(df_raw[col_recurrencia].dropna().unique())
    filtro_recurrencia = st.sidebar.selectbox("Selecciona Recurrencia:", recurrencias_disponibles)

    # ---------------------------------------------------------------------
    # PROCESAMIENTO DE FILTROS EN CASCADA
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

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(label="Total Casos del Mes", value=f"{total_boletines_vivos} Cuentas")
    with c2:
        st.metric(label="Efectividad de Gestión", value=f"{efectividad_pct}% A Tiempo", delta=f"{a_tiempo} de {total_boletines_vivos} Boletines")
    with c3:
        st.metric(label="Pendientes de Carga", value=f"{pendientes} Pendientes", delta=f"{atrasados} con Retraso", delta_color="inverse")

    st.markdown("---")

    # =========================================================================
    # MAQUETACIÓN: GRÁFICO (40%) | TABLA DETALLADA (60%)
    # =========================================================================
    col_grafico, col_tabla = st.columns([4, 6])

    # --- COLUMNA IZQUIERDA: GRÁFICO DE SLA (40%) ---
    with col_grafico:
        st.write("### 📊 Auditoría de SLA")
        
        conteo_tiempos = df_filtrado['Estatus de Entrega'].value_counts().reset_index()
        conteo_tiempos.columns = ['Estatus de Entrega', 'Cantidad']
        
        if not conteo_tiempos.empty:
            conteo_tiempos['Porcentaje'] = ((conteo_tiempos['Cantidad'] / total_boletines_vivos) * 100).round(1)
            conteo_tiempos['Etiqueta'] = conteo_tiempos.apply(lambda r: f"{r['Cantidad']} ({r['Porcentaje']}%)", axis=1)
            
            fig_sla = px.bar(
                conteo_tiempos, 
                x='Cantidad', 
                y='Estatus de Entrega', 
                text='Etiqueta',
                orientation='h', 
                color='Estatus de Entrega',
                color_discrete_map={
                    "🚀 Entregado a Tiempo": "#2ca02c",
                    "⚠️ Entregado Atrasado": "#d62728",
                    "⏳ Pendiente de Carga": "#ff7f0e",
                    "✅ Entregado (Formato Variable)": "#1f77b4"
                }
            )
            fig_sla.update_traces(textposition='outside')
            fig_sla.update_layout(xaxis_title="Boletines", yaxis_title=None, showlegend=False, height=310, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_sla, use_container_width=True)
        else:
            st.info("Sin datos para graficar con el filtro actual.")

    # --- COLUMNA DERECHA: TABLA DE DETALLE RESUMEN (60%) ---
    with col_tabla:
        st.write("### 🗂️ Resumen Ejecutivo de Cumplimiento")
        
        if col_grupo in df_filtrado.columns and col_cliente in df_filtrado.columns:
            # Estructura de datos fija
            estructura_columnas = {
                'GRUPO': df_filtrado[col_grupo].fillna("---"),
                'CLIENTE / INSTITUCIÓN': df_filtrado[col_cliente].fillna("---"),
                'F. ENTREGA': df_filtrado[col_entrega].fillna("---"),
                'F. ODOO': df_filtrado[col_odoo].fillna("---")
            }
            
            # Mostrar MÁX. DÍAS siempre si la columna existe en el Drive
            mostrar_dias = (col_dias_max is not None) and (col_dias_max in df_filtrado.columns)
            # Observación se mantiene exclusiva de los casos con atraso real
            mostrar_obs = (filtro_estatus == "⚠️ Entregado Atrasado") and (col_observacion is not None) and (col_observacion in df_filtrado.columns)
            
            if mostrar_dias:
                estructura_columnas['MÁX. DÍAS'] = df_filtrado[col_dias_max].fillna("---")
            if mostrar_obs:
                estructura_columnas['OBSERVACIÓN RETRASO'] = df_filtrado[col_observacion].fillna("Sin observación")
                
            estructura_columnas['ESTATUS'] = df_filtrado['Estatus de Entrega']
            
            df_tabla_final = pd.DataFrame(estructura_columnas)
            
            # 🔄 AJUSTE CORE: Parsear la fecha de entrega temporalmente para ordenar cronológicamente de más antiguo a más reciente
            fechas_ordenamiento = pd.to_datetime(df_tabla_final['F. ENTREGA'], errors='coerce', dayfirst=True)
            df_tabla_final['_orden_fecha'] = fechas_ordenamiento
            
            # Ordenar por fecha cronológica y limpiar columna auxiliar
            df_tabla_final = df_tabla_final.sort_values(by='_orden_fecha', na_position='last').reset_index(drop=True)
            df_tabla_final = df_tabla_final.drop(columns=['_orden_fecha'])
            
            # Construcción segura de la fila totalizadora
            total_items = len(df_tabla_final)
            datos_fila_total = {
                'GRUPO': "🟦 TOTAL GENERAL 🟦",
                'CLIENTE / INSTITUCIÓN': f"📊 {total_items} Casos Filtrados",
                'F. ENTREGA': "═══════════",
                'F. ODOO': "═══════════"
            }
            
            if mostrar_dias:
                datos_fila_total['MÁX. DÍAS'] = "═══════"
            if mostrar_obs:
                datos_fila_total['MA X. DÍAS'] = "═══════" if mostrar_dias else None # Previene descuadres de diccionario
                datos_fila_total['OBSERVACIÓN RETRASO'] = "══════════════════════"
                
            datos_fila_total['ESTATUS'] = "📈 Resumen de Selección"
            
            fila_acumulada = pd.DataFrame([datos_fila_total])
            df_desplegar = pd.concat([df_tabla_final, fila_acumulada], ignore_index=True)
            
            st.dataframe(df_desplegar, use_container_width=True, hide_index=True)
        else:
            st.warning("No se encontraron las columnas necesarias en el archivo origen.")
else:
    st.warning(f"La pestaña '{mes_seleccionado}' está vacía o no existe.")
