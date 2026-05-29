import streamlit as st
import pandas as pd
import plotly.express as px

# Configuración estética del Dashboard estilo Ejecutivo
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
# 📂 ENLACES VERIFICADOS DE GOOGLE DRIVE (CORREGIDOS)
# =========================================================================
# Enlace corregido con la 'W' mayúscula exacta que me proporcionaste
URL_BOLETINES = "https://docs.google.com/spreadsheets/d/1aGFtjIeJQ0ZyNCoTvJzfHtM3gQ6JdWKgiVHP5i-Pjj8/edit?usp=sharing"
URL_QUEJAS = "https://docs.google.com/spreadsheets/d/1goYcBbknAXGLN50b4lx8TEVxaZJeAOJrPj3qTr02gFE/edit?usp=sharing"

# FUNCIÓN DE EXTRACCIÓN: Descarga el libro completo usando formato XLSX e identifica la pestaña en memoria
def cargar_datos_pestana(url, nombre_pestana):
    try:
        if "/d/" in url:
            doc_id = url.split("/d/")[1].split("/")[0]
        else:
            return "URL de Google Sheets inválida."
            
        # Generamos el enlace de exportación directa en formato Excel estructurado
        export_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=xlsx"
        
        # Forzamos la lectura usando el motor de Excel openpyxl, idóneo para Streamlit Cloud
        excel_file = pd.ExcelFile(export_url, engine='openpyxl')
        
        # Buscamos coincidencias flexibles para evitar fallos por espacios accidentales
        pestanas_disponibles = excel_file.sheet_names
        pestana_real = None
        
        for p in pestanas_disponibles:
            if p.strip().lower() == nombre_pestana.strip().lower():
                pestana_real = p
                break
                
        # Si por alguna razón la pestaña del mes no coincide, toma la primera disponible para evitar romper la app
        if not pestana_real:
            st.sidebar.warning(f"⚠️ Pestaña '{nombre_pestana}' no hallada. Intentando cargar: {pestanas_disponibles[0]}")
            pestana_real = pestanas_disponibles[0]
            
        # Extraemos los datos de la pestaña procesada
        df = excel_file.parse(sheet_name=pestana_real)
        
        if df.empty:
            return "El archivo conectó correctamente pero la pestaña seleccionada no tiene datos."
            
        # Limpieza estética de cabeceras de columnas
        df.columns = [str(c).strip() for c in df.columns]
        df = df.loc[:, ~df.columns.str.contains('^Unnamed:')]
        df = df.dropna(how='all')
        
        return df
    except Exception as e:
        return f"Error de comunicación de red: {str(e)}"

# =========================================================================
# 🏠 PANTALLA PRINCIPAL: FRONT DE BIENVENIDA
# =========================================================================
if st.session_state.modulo_activo == "🏠 Inicio":
    st.title("🚀 Sistema Integrado de Control Operativo y BI")
    st.markdown("##### Bienvenido, Stalin. Por favor, selecciona la gestión que deseas auditar hoy:")
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 📊 Control de Boletines")
        st.info("Auditoría de tiempos de carga, control de SLAs comerciales y alertas de retrasos operativos.")
        if st.button("Ingresar a Boletines", key="btn_boletines", use_container_width=True):
            st.session_state.modulo_activo = "📊 Control de Boletines"
            st.rerun()
            
    with col2:
        st.markdown("### ⚠️ Gestión de Quejas")
        st.warning("Mapa dinámico de alertas tempranas, motivos de reclamo y estatus de resolución nacional.")
        if st.button("Ingresar a Quejas (Nacional)", key="btn_quejas", use_container_width=True):
            st.session_state.modulo_activo = "⚠️ Gestión de Quejas (Nacional)"
            st.rerun()

    with col3:
        st.markdown("### 🔮 Proyección Climatica")
        st.error("Modelo analítico predictivo que cruza alertas de satélites meteorológicos con demanda de grúas.")
        if st.button("Ingresar a Predicciones", key="btn_predicciones", use_container_width=True):
            st.success("Módulo predictivo en fase de inicialización de datos de satélite.")

# =========================================================================
# 📊 MÓDULO 1: CONTROL DE BOLETINES
# =========================================================================
elif st.session_state.modulo_activo == "📊 Control de Boletines":
    st.title("📊 Control de Boletines")
    st.markdown("---")
    
    st.sidebar.header("📅 Calendario Operativo")
    meses_anuales = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"] 
    mes_seleccionado = st.sidebar.selectbox("Selecciona el Mes a consultar:", meses_anuales, index=4) # Por defecto Mayo
    
    with st.spinner("Descargando matriz y sincronizando datos desde Google Drive..."):
        resultado = cargar_datos_pestana(URL_BOLETINES, mes_seleccionado)
    
    if isinstance(resultado, pd.DataFrame):
        df_raw = resultado
        
        # Mapeo flexible e inteligente de nombres de columnas de tu Excel
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

        # Lógica Automatizada de Semáforo / Estatus SLA
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
                    return "✅ Entregado"
                return "⚠️ Entregado Atrasado" if d_odoo > d_entrega else "🚀 Entregado a Tiempo"
                
            df_raw['Estatus de Entrega'] = [calcular_sla(row, idx) for idx, row in df_raw.iterrows()]
        else:
            df_raw['Estatus de Entrega'] = "⏳ Datos en Proceso"

        # Filtros interactivos en la barra lateral
        st.sidebar.markdown("---")
        filtro_estatus = st.sidebar.selectbox("Filtrar por Estatus SLA:", ["TODOS"] + list(df_raw['Estatus de Entrega'].unique()))
        
        filtro_comercial = "TODOS"
        if col_comercial and col_comercial in df_raw.columns:
            valores_comercial = ["TODOS"] + list(df_raw[col_comercial].dropna().unique())
            filtro_comercial = st.sidebar.selectbox("Filtrar por Área Comercial:", valores_comercial)

        df_filtrado = df_raw.copy()
        if filtro_estatus != "TODOS":
            df_filtrado = df_filtrado[df_filtrado['Estatus de Entrega'] == filtro_estatus]
        if col_comercial and filtro_comercial != "TODOS":
            df_filtrado = df_filtrado[df_filtrado[col_comercial] == filtro_comercial]

        # KPIs Ejecutivos
        total_casos = len(df_raw)
        casos_filtrados = len(df_filtrado)
        
        c1, c2, c3 = st.columns(3)
        with c1: st.metric(label="Total Casos Registrados", value=f"{total_casos} Filas")
        with c2: st.metric(label="Casos Filtrados", value=f"{casos_filtrados} Filas")
        with c3: st.metric(label="Estado de Conexión", value="🟢 Sincronizado")

        st.markdown("---")
        
        # Gráficas y Tablas Dinámicas
        col_graf, col_tab = st.columns([4, 6])
        
        with col_graf:
            st.write("### 📊 Cumplimiento de SLAs")
            conteo = df_filtrado['Estatus de Entrega'].value_counts().reset_index()
            conteo.columns = ['Estatus', 'Cantidad']
            fig = px.pie(conteo, values='Cantidad', names='Estatus', hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Safe)
            fig.update_layout(margin=dict(t=20, b=20, l=10, r=10), height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col_tab:
            st.write("### 🗂️ Vista General de Datos")
            cols_mostrar = {}
            if col_grupo: cols_mostrar['Grupo'] = df_filtrado[col_grupo]
            if col_comercial: cols_mostrar['Área Comercial'] = df_filtrado[col_comercial]
            if col_cliente: cols_mostrar['Cliente'] = df_filtrado[col_cliente]
            if col_entrega in df_filtrado.columns: cols_mostrar['F. Entrega'] = df_filtrado[col_entrega]
            if col_odoo in df_filtrado.columns: cols_mostrar['F. Carga Odoo'] = df_filtrado[col_odoo]
            cols_mostrar['Resultado SLA'] = df_filtrado['Estatus de Entrega']
            
            st.dataframe(pd.DataFrame(cols_mostrar).fillna("---"), use_container_width=True, hide_index=True)

    else:
        st.error("🚨 **Error Crítico de Interconexión**")
        st.info(f"**Detalle enviado por el sistema:** {resultado}")

# =========================================================================
# ⚠️ MÓDULO 2: GESTIÓN DE QUEJAS
# =========================================================================
elif st.session_state.modulo_activo == "⚠️ Gestión de Quejas (Nacional)":
    st.title("⚠️ Gestión Integral de Quejas")
    st.markdown("---")
    
    st.sidebar.header("📅 Historial Operativo")
    anio_seleccionado = st.sidebar.selectbox("Selecciona el Año de Análisis:", ["2025", "2026"], index=0)
    
    df_quejas = cargar_datos_pestana(URL_QUEJAS, anio_seleccionado)
    if isinstance(df_quejas, str):
        df_quejas = cargar_datos_pestana(URL_QUEJAS, f"BBDD {anio_seleccionado}")
        
    if isinstance(df_quejas, pd.DataFrame):
        st.success(f"🟢 Conexión exitosa al repositorio de Quejas ({anio_seleccionado}).")
        st.write("### Muestra de la base operativa de reclamos:")
        st.dataframe(df_quejas.head(20), use_container_width=True)
    else:
        st.error(f"No se pudo sincronizar la pestaña de quejas: {df_quejas}")
