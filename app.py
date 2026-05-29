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
        st.markdown("### ⚠️ Gestión de Quejas Operativas")
        st.warning("Análisis visual de incidencias de servicio por tipo de queja, problemas específicos, cuentas afectadas y tipos de servicios.")
        if st.button("Ingresar a Quejas Operativas", key="btn_quejas", use_container_width=True):
            st.session_state.modulo_activo = "⚠️ Gestión de Quejas (Nacional)"
            st.rerun()

# =========================================================================
# 📊 MÓDULO 1: CONTROL DE BOLETINES
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
        col_dias_maximos = detectar_columna(['dias maximas', 'días máximas', 'dias maximas del mes'], df_raw.columns)
        col_frecuencia = detectar_columna(['frecuencia', 'recurrencia', 'periodo', 'recurrencia de boletin'], df_raw.columns)

        if col_entrega in df_raw.columns and col_odoo in df_raw.columns:
            f_entrega_parsed = pd.to_datetime(df_raw[col_entrega], errors='coerce', dayfirst=True)
            f_odoo_parsed = pd.to_datetime(df_raw[col_odoo], errors='coerce', dayfirst=True)
            
            def calcular_sla(fila, idx):
                val_odoo = str(fila[col_odoo]).strip()
                if pd.isna(fila[col_odoo]) or val_odoo == "" or val_odoo.lower() == "nan":
                    return "Pendiente de Carga"
                d_entrega = f_entrega_parsed.loc[idx]
                d_odoo = f_odoo_parsed.loc[idx]
                if pd.isna(d_entrega) or pd.isna(d_odoo):
                    return "Entregado a Tiempo"
                return "Entregado Atrasado" if d_odoo > d_entrega else "Entregado a Tiempo"
                
            df_raw['Estatus Interno'] = [calcular_sla(row, idx) for idx, row in df_raw.iterrows()]
        else:
            df_raw['Estatus Interno'] = "Pendiente de Carga"

        mapa_emojis = {
            "Pendiente de Carga": "⏳ Pendiente de Carga",
            "Entregado Atrasado": "⚠️ Entregado Atrasado",
            "Entregado a Tiempo": "🚀 Entregado a Tiempo"
        }
        df_raw['Estatus de Entrega'] = df_raw['Estatus Interno'].map(mapa_emojis)

        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔍 Filtrar Clientes por Estado")
        filtro_estatus = st.sidebar.selectbox("Selecciona un Estatus:", ["TODOS", "🚀 Entregado a Tiempo", "⚠️ Entregado Atrasado", "⏳ Pendiente de Carga"])
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🎯 Filtros de Equipo")
        filtro_comercial = "TODOS"
        if col_comercial and col_comercial in df_raw.columns:
            valores_comercial = ["TODOS"] + list(df_raw[col_comercial].dropna().unique())
            filtro_comercial = st.sidebar.selectbox("Filtrar por Comercial:", valores_comercial)

        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔄 Frecuencia de Entrega")
        filtro_recurrencia = st.sidebar.selectbox("Selecciona Recurrencia:", ["TODOS", "Mensual", "Semanal", "Inmediata"])

        df_base_calculo = df_raw.copy()
        if col_comercial and filtro_comercial != "TODOS":
            df_base_calculo = df_base_calculo[df_base_calculo[col_comercial] == filtro_comercial]
        if col_frecuencia and filtro_recurrencia != "TODOS":
            df_base_calculo = df_base_calculo[df_base_calculo[col_frecuencia].astype(str).str.lower().str.contains(filtro_recurrencia.lower(), na=False)]

        total_casos_mes = len(df_base_calculo)
        a_tiempo = len(df_base_calculo[df_base_calculo['Estatus Interno'] == "Entregado a Tiempo"])
        atrasados = len(df_base_calculo[df_base_calculo['Estatus Interno'] == "Entregado Atrasado"])
        pendientes = len(df_base_calculo[df_base_calculo['Estatus Interno'] == "Pendiente de Carga"])
        
        porcentaje_efectividad = int((a_tiempo / total_casos_mes) * 100) if total_casos_mes > 0 else 0

        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1: st.metric(label="Total Casos del Segmento", value=f"{total_casos_mes} Cuentas")
        with kpi2: st.metric(label="Efectividad de Gestión", value=f"{porcentaje_efectividad}% A Tiempo", delta=f"{a_tiempo} de {total_casos_mes} Boletines")
        with kpi3: st.metric(label="Pendientes de Carga", value=f"{pendientes} Pendientes", delta=f"{atrasados} con Retraso", delta_color="inverse")

        df_filtrado_visual = df_base_calculo.copy()
        if filtro_estatus != "TODOS":
            df_filtrado_visual = df_filtrado_visual[df_filtrado_visual['Estatus de Entrega'] == filtro_estatus]

        st.markdown("---")
        col_grafica, col_tabla = st.columns([4, 6])
        
        with col_grafica:
            st.markdown("### 📊 Auditoría de SLA")
            conteo = df_filtrado_visual['Estatus de Entrega'].value_counts().reset_index()
            conteo.columns = ['Estatus', 'Cantidad']
            total_grafico = conteo['Cantidad'].sum()
            conteo['Porcentaje'] = ((conteo['Cantidad'] / total_grafico) * 100).round(1) if total_grafico > 0 else 0
            conteo['Etiqueta'] = conteo.apply(lambda r: f"{r['Cantidad']} ({r['Porcentaje']}%)", axis=1)
            
            color_map = {"⏳ Pendiente de Carga": "#FF8C00", "⚠️ Entregado Atrasado": "#DC143C", "🚀 Entregado a Tiempo": "#228B22"}
            fig = px.bar(conteo, x='Cantidad', y='Estatus', orientation='h', color='Estatus', color_discrete_map=color_map, text='Etiqueta')
            fig.update_traces(textposition='inside')
            fig.update_layout(showlegend=False, xaxis_title="Boletines", yaxis_title="", margin=dict(t=10, b=10, l=10, r=10), height=320)
            st.plotly_chart(fig, use_container_width=True)

        with col_tabla:
            st.markdown("### 📁 Resumen Ejecutivo de Cumplimiento")
            cols_mostrar = {}
            if col_cliente: cols_mostrar['CLIENTE / INSTITUCIÓN'] = df_filtrado_visual[col_cliente]
            if col_entrega in df_filtrado_visual.columns: cols_mostrar['F. ENTREGA'] = df_filtrado_visual[col_entrega]
            if col_odoo in df_filtrado_visual.columns: cols_mostrar['F. ODOO'] = df_filtrado_visual[col_odoo]
            
            if col_dias_maximos and col_dias_maximos in df_filtrado_visual.columns:
                cols_mostrar['DIAS MAXIMAS DEL MES PARA ENTREGA DE BOLETIN'] = df_filtrado_visual[col_dias_maximos]
            else:
                cols_mostrar['DIAS MAXIMAS DEL MES PARA ENTREGA DE BOLETIN'] = df_filtrado_visual.get('DIAS MAXIMAS DEL MES PARA ENTREGA DE BOLETIN', "---")
                
            cols_mostrar['ESTATUS'] = df_filtrado_visual['Estatus de Entrega']
            st.dataframe(pd.DataFrame(cols_mostrar).fillna("---"), use_container_width=True, hide_index=True, height=320)
    else:
        st.error("🚨 **Error de Interconexión con Google Sheets**")

# =========================================================================
# ⚠️ MÓDULO 2: GESTIÓN DE QUEJAS OPERATIVAS (FILTROS ADICIONALES INTEGRADOS)
# =========================================================================
elif st.session_state.modulo_activo == "⚠️ Gestión de Quejas (Nacional)":
    st.title("⚠️ Panel Inteligente de Control de Quejas Operativas")
    st.markdown("---")
    
    st.sidebar.header("📅 Historial Operativo")
    anio_seleccionado = st.sidebar.selectbox("Selecciona el Año de Análisis:", ["2025", "2026"], index=0)
    
    meses_lista = ["TODOS", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    filtro_q_mes = st.sidebar.selectbox("Filtrar Quejas por Mes:", meses_lista, index=0)
    
    with st.spinner("Sincronizando Base Operativa de Quejas con Google Drive..."):
        df_quejas = cargar_datos_pestana(URL_QUEJAS, anio_seleccionado)
        if isinstance(df_quejas, str):
            df_quejas = cargar_datos_pestana(URL_QUEJAS, f"BBDD {anio_seleccionado}")
        
    if isinstance(df_quejas, pd.DataFrame):
        col_tipo_queja = detectar_columna(['tipo de queja', 'tipo_queja', 'queja'], df_quejas.columns)
        col_problema = detectar_columna(['problema', 'motivo', 'causa', 'novedad'], df_quejas.columns)
        col_cuenta = detectar_columna(['cuenta', 'cliente', 'institucion', 'empresa'], df_quejas.columns)
        col_servicio = detectar_columna(['servicio', 'producto', 'asistencia', 'cobertura'], df_quejas.columns)
        col_mes_quejas = detectar_columna(['mes', 'fecha', 'período', 'periodo'], df_quejas.columns)
        col_provincia = detectar_columna(['provincia', 'ciudad', 'sucursal', 'region', 'ubicacion'], df_quejas.columns)

        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🎛️ Filtros Avanzados")
        
        filtro_q_tipo = "TODOS"
        if col_tipo_queja and col_tipo_queja in df_quejas.columns:
            valores_q = ["TODOS"] + list(df_quejas[col_tipo_queja].dropna().unique())
            filtro_q_tipo = st.sidebar.selectbox("Filtrar por Tipo de Queja:", valores_q)
            
        filtro_q_cuenta = "TODOS"
        if col_cuenta and col_cuenta in df_quejas.columns:
            valores_c = ["TODOS"] + list(df_quejas[col_cuenta].dropna().unique())
            filtro_q_cuenta = st.sidebar.selectbox("Filtrar por Cuenta Corporativa:", valores_c)

        # NUEVO: Filtro dinámico por Problema en el menú izquierdo
        filtro_q_problema = "TODOS"
        if col_problema and col_problema in df_quejas.columns:
            valores_p = ["TODOS"] + list(df_quejas[col_problema].dropna().unique())
            filtro_q_problema = st.sidebar.selectbox("Filtrar por Problema Específico:", valores_p)

        # NUEVO: Filtro dinámico por Servicio en el menú izquierdo
        filtro_q_servicio = "TODOS"
        if col_servicio and col_servicio in df_quejas.columns:
            valores_s = ["TODOS"] + list(df_quejas[col_servicio].dropna().unique())
            filtro_q_servicio = st.sidebar.selectbox("Filtrar por Tipo de Servicio:", valores_s)

        # Aplicación estricta de todos los filtros cruzados sobre la data
        df_q_filtrado = df_quejas.copy()
        
        if col_mes_quejas and filtro_q_mes != "TODOS":
            df_q_filtrado = df_q_filtrado[df_q_filtrado[col_mes_quejas].astype(str).str.lower().str.contains(filtro_q_mes.lower(), na=False)]
        if filtro_q_tipo != "TODOS":
            df_q_filtrado = df_q_filtrado[df_q_filtrado[col_tipo_queja] == filtro_q_tipo]
        if filtro_q_cuenta != "TODOS":
            df_q_filtrado = df_q_filtrado[df_q_filtrado[col_cuenta] == filtro_q_cuenta]
        if filtro_q_problema != "TODOS":
            df_q_filtrado = df_q_filtrado[df_q_filtrado[col_problema] == filtro_q_problema]
        if filtro_q_servicio != "TODOS":
            df_q_filtrado = df_q_filtrado[df_q_filtrado[col_servicio] == filtro_q_servicio]

        total_quejas_reg = len(df_q_filtrado)
        tipos_unicos = df_q_filtrado[col_tipo_queja].nunique() if col_tipo_queja else 0
        problemas_unicos = df_q_filtrado[col_problema].nunique() if col_problema else 0
        servicios_unicos = df_q_filtrado[col_servicio].nunique() if col_servicio else 0

        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric(label="Total Quejas Auditadas", value=f"{total_quejas_reg} Casos")
        with m2: st.metric(label="Tipos de Queja Identificados", value=f"{tipos_unicos} Tipos")
        with m3: st.metric(label="Tipos de Problemas Críticos", value=f"{problemas_unicos} Frecuentes")
        with m4: st.metric(label="Servicios Afectados", value=f"{servicios_unicos} Ramos")

        st.markdown("---")
        
        # 📊 FILA 1 DE GRÁFICAS: TIPO DE QUEJA Y PROBLEMAS CRÍTICOS
        g_col1, g_col2 = st.columns(2)
        
        with g_col1:
            st.markdown("#### 📌 1. Distribución por Tipo de Queja")
            if col_tipo_queja and col_tipo_queja in df_q_filtrado.columns:
                df_g1 = df_q_filtrado[col_tipo_queja].value_counts().reset_index()
                df_g1.columns = ['Tipo de Queja', 'Cantidad']
                df_g1['Porcentaje'] = ((df_g1['Cantidad'] / total_quejas_reg) * 100).round(1) if total_quejas_reg > 0 else 0
                df_g1['Etiqueta'] = df_g1.apply(lambda r: f"{r['Cantidad']} ({r['Porcentaje']}%)", axis=1)
                
                fig_g1 = px.bar(df_g1, x='Cantidad', y='Tipo de Queja', orientation='h', text='Etiqueta',
                                color='Tipo de Queja', color_discrete_sequence=px.colors.qualitative.Dark2)
                fig_g1.update_traces(textposition='inside')
                fig_g1.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'}, height=330, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_g1, use_container_width=True)
            else:
                st.info("La columna de Tipo de queja no está mapeada en esta pestaña.")

        with g_col2:
            st.markdown("#### 🎯 2. Top 10 Problemas Más Frecuentes")
            if col_problema and col_problema in df_q_filtrado.columns:
                df_g2 = df_q_filtrado[col_problema].value_counts().reset_index().head(10)
                df_g2.columns = ['Problema', 'Cantidad']
                df_g2['Porcentaje'] = ((df_g2['Cantidad'] / total_quejas_reg) * 100).round(1) if total_quejas_reg > 0 else 0
                df_g2['Etiqueta'] = df_g2.apply(lambda r: f"{r['Cantidad']} ({r['Porcentaje']}%)", axis=1)
                
                fig_g2 = px.bar(df_g2, x='Cantidad', y='Problema', orientation='h', text='Etiqueta',
                                color='Cantidad', color_continuous_scale='Reds')
                fig_g2.update_layout(coloraxis_showscale=False, yaxis={'categoryorder':'total ascending'}, height=330, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_g2, use_container_width=True)
            else:
                st.info("La columna de Problema no está mapeada en esta pestaña.")

        st.markdown("---")
        
        # 📊 FILA 2 DE GRÁFICAS: CUENTAS Y SERVICIOS AFECTADOS
        g_col3, g_col4 = st.columns(2)
        
        with g_col3:
            st.markdown("#### 🏢 3. Top 10 Cuentas con Mayor Nivel de Incidencias")
            if col_cuenta and col_cuenta in df_q_filtrado.columns:
                df_g3 = df_q_filtrado[col_cuenta].value_counts().reset_index().head(10)
                df_g3.columns = ['Cuenta', 'Cantidad']
                df_g3['Porcentaje'] = ((df_g3['Cantidad'] / total_quejas_reg) * 100).round(1) if total_quejas_reg > 0 else 0
                df_g3['Etiqueta'] = df_g3.apply(lambda r: f"{r['Cantidad']} ({r['Porcentaje']}%)", axis=1)
                
                fig_g3 = px.bar(df_g3, x='Cantidad', y='Cuenta', orientation='h', text='Etiqueta',
                                color='Cantidad', color_continuous_scale='Blues')
                fig_g3.update_layout(coloraxis_showscale=False, yaxis={'categoryorder':'total ascending'}, height=330, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_g3, use_container_width=True)
            else:
                st.info("La columna de Cuenta no está mapeada en esta pestaña.")

        with g_col4:
            st.markdown("#### 🛠️ 4. Top 10 Servicios con Mayor Nivel de Quejas")
            if col_servicio and col_servicio in df_q_filtrado.columns:
                df_g4 = df_q_filtrado[col_servicio].value_counts().reset_index().head(10)
                df_g4.columns = ['Servicio', 'Cantidad']
                df_g4['Porcentaje'] = ((df_g4['Cantidad'] / total_quejas_reg) * 100).round(1) if total_quejas_reg > 0 else 0
                df_g4['Etiqueta'] = df_g4.apply(lambda r: f"{r['Cantidad']} ({r['Porcentaje']}%)", axis=1)
                
                fig_g4 = px.bar(df_g4, x='Cantidad', y='Servicio', orientation='h', text='Etiqueta',
                                color='Servicio', color_discrete_sequence=px.colors.qualitative.Prism)
                fig_g4.update_traces(textposition='inside')
                fig_g4.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'}, height=330, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_g4, use_container_width=True)
            else:
                st.info("La columna de Servicio no está mapeada en esta pestaña.")
                
        # 📊 FILA CENTRAL COMPLETA: TOP 10 DE PROVINCIAS
        st.markdown("---")
        st.markdown("#### 🗺️ 5. Top 10 Provincias con Mayor Nivel de Quejas")
        if col_provincia and col_provincia in df_q_filtrado.columns:
            df_g5 = df_q_filtrado[col_provincia].value_counts().reset_index().head(10)
            df_g5.columns = ['Provincia', 'Cantidad']
            df_g5['Porcentaje'] = ((df_g5['Cantidad'] / total_quejas_reg) * 100).round(1) if total_quejas_reg > 0 else 0
            df_g5['Etiqueta'] = df_g5.apply(lambda r: f"{r['Cantidad']} ({r['Porcentaje']}%)", axis=1)
            
            fig_g5 = px.bar(df_g5, x='Cantidad', y='Provincia', orientation='h', text='Etiqueta',
                            color='Cantidad', color_continuous_scale='Viridis')
            fig_g5.update_layout(coloraxis_showscale=False, yaxis={'categoryorder':'total ascending'}, height=380, margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_g5, use_container_width=True)
        else:
            st.info("No se encontró una columna de ubicación geográfica ('Provincia', 'Ciudad') mapeada en esta pestaña de Drive.")
            
    else:
        st.error(f"No se pudo sincronizar el repositorio de Quejas: {df_quejas}")
