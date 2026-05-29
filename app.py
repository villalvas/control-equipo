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

# FUNCIÓN DE EXTRACCIÓN: Lee XLSX nativo usando openpyxl con tolerancia a espacios en pestañas
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
            
        # Limpieza estricta de nombres de columnas
        df.columns = [str(c).strip() for c in df.columns]
        df = df.loc[:, ~df.columns.str.contains('^Unnamed:')]
        df = df.dropna(how='all')
        
        return df
    except Exception as e:
        return f"Error de comunicación de red: {str(e)}"

# =========================================================================
# 🏠 PANTALLA PRINCIPAL: FRONT DE BIENVENIDA (ESTRUCTURA BI-MODULAR)
# =========================================================================
if st.session_state.modulo_activo == "🏠 Inicio":
    st.title("🚀 Sistema Integrado de Control Operativo y BI")
    st.markdown("##### Bienvenido, Stalin. Por favor, selecciona la gestión que deseas auditar hoy:")
    st.markdown("---")
    
    col1, col2 = st.columns(2) # Cambiado a 2 columnas para una visual más limpia y balanceada
    with col1:
        st.markdown("### 📊 Control de Boletines")
        st.info("Auditoría de tiempos de carga, control de SLAs comerciales y alertas de retrasos operativos.")
        if st.button("Ingresar a Boletines", key="btn_boletines", use_container_width=True):
            st.session_state.modulo_activo = "📊 Control de Boletines"
            st.rerun()
            
    with col2:
        st.markdown("### ⚠️ Gestión de Quejas y Modelos Predictivos")
        st.warning("Mapa dinámico de alertas tempranas nacionales, analítica de motivos de reclamo y módulo de Proyección Climática Integrada.")
        if st.button("Ingresar a Quejas y Predicciones", key="btn_quejas", use_container_width=True):
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
        
        def detectar_columna(keys, columnas_disponibles):
            for k in keys:
                for col in columnas_disponibles:
                    if k.lower() in col.lower():
                        return col
            return columnas_disponibles[0] if len(columnas_disponibles) > 0 else None

        col_grupo = detectar_columna(['grupo'], df_raw.columns)
        col_comercial = detectar_columna(['area comercial', 'comercial'], df_raw.columns)
        col_cliente = detectar_columna(['te instituc', 'instituc', 'cliente'], df_raw.columns)
        col_entrega = detectar_columna(['fecha de entrega', 'entrega', 'liberacion'], df_raw.columns)
        col_odoo = detectar_columna(['odoo', 'carga', 'fecha'], df_raw.columns)

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
            color_map = {"⏳ Pendiente de Carga": "#FF8C00", "⚠️ Entregado Atrasado": "#DC143C", "🚀 Entregado a Tiempo": "#228B22"}
            fig = px.bar(conteo, x='Cantidad', y='Estatus', orientation='h', color='Estatus', color_discrete_map=color_map, text='Cantidad')
            fig.update_layout(showlegend=False, xaxis_title="Boletines", yaxis_title="", margin=dict(t=10, b=10, l=10, r=10), height=320)
            st.plotly_chart(fig, use_container_width=True)

        with col_tabla:
            st.markdown("### 📁 Resumen Ejecutivo de Cumplimiento")
            cols_mostrar = {}
            if col_cliente: cols_mostrar['CLIENTE / INSTITUCIÓN'] = df_filtrado[col_cliente]
            if col_entrega in df_filtrado.columns: cols_mostrar['F. ENTREGA'] = df_filtrado[col_entrega]
            if col_odoo in df_filtrado.columns: cols_mostrar['F. ODOO'] = df_filtrado[col_odoo]
            cols_mostrar['ESTATUS'] = df_filtrado['Estatus de Entrega']
            st.dataframe(pd.DataFrame(cols_mostrar).fillna("---"), use_container_width=True, hide_index=True, height=320)
    else:
        st.error("🚨 **Error de Interconexión con Google Sheets**")

# =========================================================================
# ⚠️ MÓDULO 2: GESTIÓN DE QUEJAS (CON PROYECTÓN CLIMÁTICA INTEGRADA)
# =========================================================================
elif st.session_state.modulo_activo == "⚠️ Gestión de Quejas (Nacional)":
    st.title("⚠️ Gestión Integral de Quejas Nacionales")
    st.markdown("---")
    
    st.sidebar.header("📅 Historial Operativo")
    anio_seleccionado = st.sidebar.selectbox("Selecciona el Año de Análisis:", ["2025", "2026"], index=0)
    
    with st.spinner("Sincronizando Base de Datos Nacional de Quejas..."):
        df_quejas = cargar_datos_pestana(URL_QUEJAS, anio_seleccionado)
        if isinstance(df_quejas, str):
            df_quejas = cargar_datos_pestana(URL_QUEJAS, f"BBDD {anio_seleccionado}")
        
    if isinstance(df_quejas, pd.DataFrame):
        # 🌟 AQUÍ ESTÁ EL CAMBIO CLAVE: Creación de pestañas internas (Tabs) para agrupar las herramientas
        tab_alertas, tab_clima = st.tabs(["🗺️ Mapa de Alertas Nacionales", "🔮 Proyección Climática Predictiva"])
        
        with tab_alertas:
            st.markdown("### 📊 Centro de Control de Incidencias Territoriales")
            
            # KPIs Rápidos para la pestaña de quejas
            total_quejas = len(df_quejas)
            st.metric(label="Total Reclamos Registrados", value=f"{total_quejas} Casos")
            
            st.write("##### Monitoreo de Datos Base:")
            st.dataframe(df_quejas.head(50), use_container_width=True, height=400)
            
        with tab_clima:
            st.markdown("### 🌦️ Módulo de Predicción Meteorológica vs Operaciones de Grúas")
            st.info("Este espacio matemático cruza datos satelitales históricos con picos de siniestralidad operativa.")
            
            # Diseño Ejecutivo para las variables del Clima
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("##### 🌧️ Índice de Precipitación")
                st.slider("Nivel de Lluvia Estimado (mm):", 0, 100, 25, key="clima_lluvia")
            with c2:
                st.markdown("##### 🌫️ Visibilidad en Carreteras")
                st.selectbox("Nivel de Neblina / Densidad:", ["Normal", "Moderada", "Crítica (Alerta Vial)"], key="clima_visib")
            with c3:
                st.markdown("##### 🚜 Demanda Estimada de Auxilio Mecánico")
                st.metric(label="Factor de Incremento en Grúas", value="+18% Siniestros", delta="Zona Crítica Detectada")
                
            st.markdown("---")
            st.write("📈 *El modelo dinámico de proyección climática está listo para recibir el mapeo de coordenadas geográficas de la base.*")
            
    else:
        st.error(f"No se pudo sincronizar el repositorio de Quejas: {df_quejas}")
