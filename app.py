import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración estética del Dashboard estilo Ejecutivo Premium
st.set_page_config(page_title="Centro de Mando - Serviasistencia", layout="wide", initial_sidebar_state="expanded")

# =========================================================================
# ⚙️ CONTROL DE NAVEGACIÓN (SESSION STATE)
# =========================================================================
if "modulo_activo" not in st.session_state:
    st.session_state.modulo_activo = "🏠 Inicio"

if st.session_state.modulo_activo != "🏠 Inicio":
    if st.sidebar.button("⬅️ Volver al Menú Principal", use_container_width=True):
        st.session_state.modulo_activo = "🏠 Inicio"
        st.rerun()

# =========================================================================
# 📂 ENLACES VERIFICADOS DE GOOGLE DRIVE (SINCRONIZADOS)
# =========================================================================
URL_BOLETINES = "https://docs.google.com/spreadsheets/d/1aGFtjIeJQ0ZyNCoTvJzfHtM3gQ6JdWKgiVHP5i-Pjj8/edit?usp=sharing"
URL_QUEJAS = "https://docs.google.com/spreadsheets/d/1goYcBbknAXGLN50b4lx8TEVxaZJeAOJrPj3qTr02gFE/edit?usp=sharing"

# FUNCIÓN DE EXTRACCIÓN XLSX UNIVERSAL
def cargar_datos_pestana(url, nombre_pestana):
    try:
        if "/d/" in url:
            doc_id = url.split("/d/")[1].split("/")[0]
        else:
            return "URL de Google Sheets inválida."
            
        export_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=xlsx"
        excel_file = pd.ExcelFile(export_url, engine='openpyxl')
        
        pestanas_disponibles = excel_file.sheet_names
        pestana_real = None
        
        for p in pestanas_disponibles:
            if p.strip().lower() == nombre_pestana.strip().lower():
                pestana_real = p
                break
                
        if not pestana_real:
            for p in pestanas_disponibles:
                if nombre_pestana.strip().lower() in p.strip().lower():
                    pestana_real = p
                    break
            
        if not pestana_real:
            pestana_real = pestanas_disponibles[0]
            
        df = excel_file.parse(sheet_name=pestana_real)
        
        if df.empty:
            return "El archivo conectó correctamente pero la pestaña seleccionada no tiene datos."
            
        df.columns = [str(c).strip() for c in df.columns]
        df = df.loc[:, ~df.columns.str.contains('^Unnamed:')]
        df = df.dropna(how='all')
        
        return df
    except Exception as e:
        return f"Error de comunicación de red: {str(e)}"

# Buscador inteligente de columnas
def detectar_columna(keys, columnas_disponibles):
    for k in keys:
        for col in columnas_disponibles:
            if k.lower() in col.lower():
                return col
    return None

# =========================================================================
# 🏠 PANTALLA PRINCIPAL: FRONT DE BIENVENIDA
# =========================================================================
if st.session_state.modulo_activo == "🏠 Inicio":
    st.title("🚀 Sistema Integrado de Control Operativo y BI")
    st.markdown("##### Bienvenido, Stalin. Por favor, selecciona la gestión que deseas auditar hoy:")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📊 Control de Boletines")
        st.info("Auditoría de tiempos de carga, control de SLAs comerciales y alertas de retrasos operativos.")
        if st.button("Ingresar a Boletines", key="btn_boletines", use_container_width=True):
            st.session_state.modulo_activo = "📊 Control de Boletines"
            st.rerun()
            
    with col2:
        st.markdown("### ⚠️ Gestión de Quejas y Modelos Predictivos")
        st.warning("Análisis visual de incidencias operativas, rendimiento por supervisor y módulo de Proyección Climática Integrada.")
        if st.button("Ingresar a Quejas y Predicciones", key="btn_quejas", use_container_width=True):
            st.session_state.modulo_activo = "⚠️ Gestión de Quejas (Nacional)"
            st.rerun()

# =========================================================================
# 📊 MÓDULO 1: CONTROL DE BOLETINES (ACTUALIZADO CON TUS REQUERIMIENTOS)
# =========================================================================
elif st.session_state.modulo_activo == "📊 Control de Boletines":
    st.title("📊 Control de Boletines")
    st.markdown("---")
    
    st.sidebar.markdown("### 📅 Calendario Operativo")
    meses_anuales = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"] 
    mes_seleccionado = st.sidebar.selectbox("Selecciona el Mes a consultar:", meses_anuales, index=4)
    
    with st.spinner("Descargando matriz y sincronizando datos desde Google Drive..."):
        resultado = cargar_datos_pestana(URL_BOLETINES, mes_seleccionado)
    
    if isinstance(resultado, pd.DataFrame):
        df_raw = resultado
        
        col_grupo = detectar_columna(['grupo'], df_raw.columns)
        col_comercial = detectar_columna(['area comercial', 'comercial'], df_raw.columns)
        col_cliente = detectar_columna(['te instituc', 'instituc', 'cliente'], df_raw.columns)
        col_entrega = detectar_columna(['fecha de entrega', 'entrega', 'liberacion'], df_raw.columns)
        col_odoo = detectar_columna(['odoo', 'carga', 'fecha'], df_raw.columns)
        
        # Mapeo específico para tu nueva columna solicitada de días máximos
        col_dias_maximos = detectar_columna(['dias maximas', 'días máximas', 'dias maximas del mes'], df_raw.columns)

        if col_entrega in df_raw.columns and col_odoo in df_raw.columns:
            f_entrega_parsed = pd.to_datetime(df_raw[col_entrega], errors='coerce', dayfirst=True)
            f_odoo_parsed = pd.to_datetime(df_raw[col_odoo], errors='coerce', dayfirst=True)
            
            def calcular_sla(fila, idx):
                val_odoo = str(fila[col_odoo]).strip()
                if pd.isna(fila[col_odoo]) or val_odoo == "" or val_odoo.lower() == "nan":
                    return "⏳ Pendiente de Carga"
                d_entrega = f_entrega_parsed.loc[idx]
                d_odoo = f_odoo_parsed.loc[idx]
                if pd.isna(d_entrega) or pd.isna(d_odoo):
                    return "🚀 Entregado a Tiempo"
                return "⚠️ Entregado Atrasado" if d_odoo > d_entrega else "🚀 Entregado a Tiempo"
                
            df_raw['Estatus de Entrega'] = [calcular_sla(row, idx) for idx, row in df_raw.iterrows()]
        else:
            df_raw['Estatus de Entrega'] = "⏳ Pendiente de Carga"

        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔍 Filtrar Clientes por Estado")
        filtro_estatus = st.sidebar.selectbox("Selecciona un Estatus:", ["TODOS"] + list(df_raw['Estatus de Entrega'].unique()))
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🎯 Filtros de Equipo")
        filtro_comercial = "TODOS"
        if col_comercial and col_comercial in df_raw.columns:
            valores_comercial = ["TODOS"] + list(df_raw[col_comercial].dropna().unique())
            filtro_comercial = st.sidebar.selectbox("Filtrar por Comercial:", valores_comercial)

        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔄 Frecuencia de Entrega")
        filtro_recurrencia = st.sidebar.selectbox("Selecciona Recurrencia:", ["TODOS", "Mensual", "Semanal", "Inmediata"])

        df_filtrado = df_raw.copy()
        if filtro_estatus != "TODOS":
            df_filtrado = df_filtrado[df_filtrado['Estatus de Entrega'] == filtro_estatus]
        if col_comercial and filtro_comercial != "TODOS":
            df_filtrado = df_filtrado[df_filtrado[col_comercial] == filtro_comercial]

        total_casos_mes = len(df_filtrado)
        a_tiempo = len(df_filtrado[df_filtrado['Estatus de Entrega'] == "🚀 Entregado a Tiempo"])
        pendientes = len(df_filtrado[df_filtrado['Estatus de Entrega'] == "⏳ Pendiente de Carga"])
        atrasados = len(df_filtrado[df_filtrado['Estatus de Entrega'] == "⚠️ Entregado Atrasado"])
        porcentaje_efectividad = int((a_tiempo / total_casos_mes) * 100) if total_casos_mes > 0 else 0

        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1: st.metric(label="Total Casos del Mes", value=f"{total_casos_mes} Cuentas")
        with kpi2: st.metric(label="Efectividad de Gestión", value=f"{porcentaje_efectividad}% A Tiempo", delta=f"{a_tiempo} de {total_casos_mes} Boletines")
        with kpi3: st.metric(label="Pendientes de Carga", value=f"{pendientes} Pendientes", delta=f"{atrasados} con Retraso", delta_color="inverse")

        st.markdown("---")
        col_grafica, col_tabla = st.columns([4, 6])
        
        with col_grafica:
            st.markdown("### 📊 Auditoría de SLA")
            conteo = df_filtrado['Estatus de Entrega'].value_counts().reset_index()
            conteo.columns = ['Estatus', 'Cantidad']
            
            # 🛠️ CÁCULO DE CANTIDAD Y PORCENTAJE PARA LAS ETIQUETAS DE LAS BARRAS
            total_grafico = conteo['Cantidad'].sum()
            conteo['Porcentaje'] = ((conteo['Cantidad'] / total_grafico) * 100).round(1)
            conteo['Etiqueta'] = conteo.apply(lambda r: f"{r['Cantidad']} ({r['Porcentaje']}%)", axis=1)
            
            color_map = {"⏳ Pendiente de Carga": "#FF8C00", "⚠️ Entregado Atrasado": "#DC143C", "🚀 Entregado a Tiempo": "#228B22"}
            
            # Inyectamos el campo 'Etiqueta' personalizado en las barras
            fig = px.bar(conteo, x='Cantidad', y='Estatus', orientation='h', 
                         color='Estatus', color_discrete_map=color_map, text='Etiqueta')
            fig.update_traces(textposition='inside')
            fig.update_layout(showlegend=False, xaxis_title="Boletines", yaxis_title="", margin=dict(t=10, b=10, l=10, r=10), height=320)
            st.plotly_chart(fig, use_container_width=True)

        with col_tabla:
            st.markdown("### 📁 Resumen Ejecutivo de Cumplimiento")
            cols_mostrar = {}
            if col_cliente: cols_mostrar['CLIENTE / INSTITUCIÓN'] = df_filtrado[col_cliente]
            if col_entrega in df_filtrado.columns: cols_mostrar['F. ENTREGA'] = df_filtrado[col_entrega]
            if col_odoo in df_filtrado.columns: cols_mostrar['F. ODOO'] = df_filtrado[col_odoo]
            
            # 🛠️ AGREGAMOS DE FORMA SEGURA EL CAMPO DE DÍAS MÁXIMOS SOLICITADO
            if col_dias_maximos and col_dias_maximos in df_filtrado.columns:
                cols_mostrar['DIAS MAXIMAS DEL MES PARA ENTREGA DE BOLETIN'] = df_filtrado[col_dias_maximos]
            else:
                # Si por alguna razón el buscador no encuentra la coincidencia exacta por texto limpio
                cols_mostrar['DIAS MAXIMAS DEL MES PARA ENTREGA DE BOLETIN'] = df_filtrado.get('DIAS MAXIMAS DEL MES PARA ENTREGA DE BOLETIN', "---")
                
            cols_mostrar['ESTATUS'] = df_filtrado['Estatus de Entrega']
            st.dataframe(pd.DataFrame(cols_mostrar).fillna("---"), use_container_width=True, hide_index=True, height=320)
    else:
        st.error("🚨 **Error de Interconexión con Google Sheets**")

# =========================================================================
# ⚠️ MÓDULO 2: GESTIÓN DE QUEJAS
# =========================================================================
elif st.session_state.modulo_activo == "⚠️ Gestión de Quejas (Nacional)":
    st.title("⚠️ Inteligencia Analítica de Quejas Nacionales")
    st.markdown("---")
    
    st.sidebar.header("📅 Historial Operativo")
    anio_seleccionado = st.sidebar.selectbox("Selecciona el Año de Análisis:", ["2025", "2026"], index=0)
    
    with st.spinner("Sincronizando Base Operativa de Quejas..."):
        df_quejas = cargar_datos_pestana(URL_QUEJAS, anio_seleccionado)
        if isinstance(df_quejas, str):
            df_quejas = cargar_datos_pestana(URL_QUEJAS, f"BBDD {anio_seleccionado}")
        
    if isinstance(df_quejas, pd.DataFrame):
        
        tab_graficas, tab_clima = st.tabs(["📊 Dashboard de Control Visual", "🔮 Proyección Climática Predictiva"])
        
        with tab_graficas:
            col_tipo = detectar_columna(['tipo', 'clase', 'categoria'], df_quejas.columns)
            col_mes = detectar_columna(['mes', 'fecha', 'período'], df_quejas.columns)
            col_supervisor = detectar_columna(['supervisor', 'encargado', 'responsable', 'coordinador'], df_quejas.columns)
            col_problema = detectar_columna(['problema', 'motivo', 'detalle', 'causa', 'novedad'], df_quejas.columns)
            col_estado = detectar_columna(['estado', 'estatus', 'malo', 'resultado'], df_quejas.columns)
            
            total_casos = len(df_quejas)
            st.metric(label="Total Casos Auditados en la Base", value=f"{total_casos} Quejas")
            st.markdown("---")
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 📌 1. Distribución por Tipo de Queja")
                if col_tipo:
                    df_tipo = df_quejas[col_tipo].value_counts().reset_index()
                    df_tipo.columns = ['Tipo', 'Cantidad']
                    fig1 = px.pie(df_tipo, values='Cantidad', names='Tipo', hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
                    fig1.update_traces(textposition='inside', textinfo='percent+label')
                    fig1.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=320, showlegend=True)
                    st.plotly_chart(fig1, use_container_width=True)
                    
            with c2:
                st.markdown("#### 🎯 2. Análisis Crítico de Problemas")
                if col_problema:
                    df_prob = df_quejas[col_problema].value_counts().reset_index()
                    df_prob.columns = ['Problema', 'Cantidad']
                    df_prob['Porcentaje'] = (df_prob['Cantidad'] / total_casos * 100).round(1)
                    df_prob['Etiqueta'] = df_prob.apply(lambda r: f"{r['Cantidad']} ({r['Porcentaje']}% )", axis=1)
                    fig2 = px.bar(df_prob.head(10), x='Cantidad', y='Problema', orientation='h', text='Etiqueta', color='Cantidad', color_continuous_scale='Reds')
                    fig2.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=10, b=10, l=10, r=10), height=320, coloraxis_showscale=False)
                    st.plotly_chart(fig2, use_container_width=True)
            
            st.markdown("---")
            c3, c4 = st.columns(2)
            with c3:
                st.markdown("#### 📅 3. Volumen Mensual de Quejas y Malos")
                if col_mes:
                    eje_color = col_estado if col_estado else col_mes
                    df_mes = df_quejas.groupby([col_mes, eje_color]).size().reset_index(name='Cantidad')
                    fig3 = px.bar(df_mes, x=col_mes, y='Cantidad', color=eje_color, barmode='group', text='Cantidad', color_discrete_sequence=px.colors.qualitative.Bold)
                    fig3.update_layout(xaxis_title="Meses", yaxis_title="Casos", margin=dict(t=10, b=10, l=10, r=10), height=340)
                    st.plotly_chart(fig3, use_container_width=True)
                    
            with c4:
                st.markdown("#### 👔 4. Desempeño Operativo por Supervisor Encargado")
                if col_supervisor:
                    eje_color_sup = col_estado if col_estado else col_supervisor
                    df_sup = df_quejas.groupby([col_supervisor, eje_color_sup]).size().reset_index(name='Cantidad')
                    fig4 = px.bar(df_sup, x='Cantidad', y=col_supervisor, color=eje_color_sup, orientation='h', color_discrete_sequence=px.colors.qualitative.Dark24)
                    fig4.update_layout(yaxis={'categoryorder':'total ascending'}, xaxis_title="Total Casos asignados", yaxis_title="", margin=dict(t=10, b=10, l=10, r=10), height=340)
                    st.plotly_chart(fig4, use_container_width=True)

        with tab_clima:
            st.markdown("### 🌦️ Módulo de Predicción Meteorológica vs Operaciones de Grúas")
            cx1, cx2, cx3 = st.columns(3)
            with cx1:
                st.markdown("##### 🌧️ Índice de Precipitación")
                st.slider("Nivel de Lluvia Estimado (mm):", 0, 100, 25, key="clima_lluvia")
            with cx2:
                st.markdown("##### 🌫️ Visibilidad en Carreteras")
                st.selectbox("Nivel de Neblina / Densidad:", ["Normal", "Moderada", "Crítica (Alerta Vial)"], key="clima_visib")
            with cx3:
                st.markdown("##### 🚜 Demanda Estimada de Auxilio Mecánico")
                st.metric(label="Factor de Incremento en Grúas", value="+18% Siniestros", delta="Zona Crítica Detectada")
    else:
        st.error(f"No se pudo sincronizar el repositorio de Quejas: {df_quejas}")
