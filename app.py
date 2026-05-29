import streamlit as st
import pandas as pd
import plotly.express as px
import urllib.parse

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
# 📂 ENLACES VERIFICADOS DE GOOGLE DRIVE 
# =========================================================================
# Tus enlaces de hojas compartidas (Asegurados en modo "Cualquier persona con el enlace puede ver")
URL_BOLETINES = "https://docs.google.com/spreadsheets/d/1aGFtjIeJQ0ZyNCoTvJzfHtM3gQ6JdwKgiVHP5i-Pjj8/edit?usp=sharing"
URL_QUEJAS = "https://docs.google.com/spreadsheets/d/1goYcBbknAXGLN50b4lx8TEVxaZJeAOJrPj3qTr02gFE/edit?usp=sharing"

# Función de extracción universal corregida (Evita el Error 404 de Google)
def cargar_datos_pestana(url, nombre_pestana):
    try:
        # Extraemos el ID único del documento usando división de cadena estándar
        if "/d/" in url:
            doc_id = url.split("/d/")[1].split("/")[0]
        else:
            return "URL de Google Sheets no válida."
            
        # Codificamos el nombre de la pestaña de forma segura para URLs de internet
        pestana_codificada = urllib.parse.quote(nombre_pestana)
        
        # Endpoint de Google alternativo y ultra-estable para peticiones externas CSV
        csv_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/gviz/tq?tqx=out:csv&sheet={pestana_codificada}"
        
        # Realizamos la lectura directa mediante pandas
        df = pd.read_csv(csv_url, on_bad_lines='skip')
        
        if df.empty:
            return "El archivo se conectó correctamente pero la pestaña no contiene registros estructurados."
            
        # Limpieza de las cabeceras de columnas para evitar espacios en blanco invisibles
        df.columns = [str(c).strip() for c in df.columns]
        df = df.loc[:, ~df.columns.str.contains('^Unnamed:')]
        
        # Eliminamos filas que estén completamente en blanco en el Excel
        df = df.dropna(how='all')
        return df
    except Exception as e:
        return f"Error de comunicación de red: {str(e)}"

# =========================================================================
# 🏠 PANTALLA PRINCIPAL: FRONT DE BIENVENIDA (ESTILO ORIGINAL)
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
        st.markdown("### 🔮 Proyección Climatática")
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
    
    with st.spinner("Estableciendo conexión segura con Google Drive..."):
        resultado = cargar_datos_pestana(URL_BOLETINES, mes_seleccionado)
    
    if isinstance(resultado, pd.DataFrame):
        df_raw = resultado
        
        # Mapeo flexible e inteligente de nombres de columnas
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

        # Barra lateral de filtros dinámicos
        st.sidebar.markdown("---")
        filtro_estatus = st.sidebar.selectbox("Filtrar por Estatus SLA:", ["TODOS"] + list(df_raw['Estatus de Entrega'].unique()))
        
        filtro_comercial = "TODOS"
        if col_comercial and col_comercial in df_raw.columns:
            valores_comercial = ["TODOS"] + list(df_raw[col_comercial].dropna().unique())
            filtro_comercial = st.sidebar.selectbox("Filtrar por Área Comercial:", valores_comercial)

        # Filtrado del DataFrame
        df_filtrado = df_raw.copy()
        if filtro_estatus != "TODOS":
            df_filtrado = df_filtrado[df_filtrado['Estatus de Entrega'] == filtro_estatus]
        if col_comercial and filtro_comercial != "TODOS":
            df_filtrado = df_filtrado[df_filtrado[col_comercial] == filtro_comercial]

        # Despliegue de KPIs Ejecutivos
        total_casos = len(df_raw)
        casos_filtrados = len(df_filtrado)
        
        c1, c2, c3 = st.columns(3)
        with c1: st.metric(label="Total Casos en Base de Datos", value=f"{total_casos} Registros")
        with c2: st.metric(label="Registros Bajo Filtro Actual", value=f"{casos_filtrados} Filas")
        with c3: st.metric(label="Canal de Enlace", value="🟢 Sincronizado")

        st.markdown("---")
        
        # Gráficas y Tablas
        col_graf, col_tab = st.columns([4, 6])
        
        with col_graf:
            st.write("### 📊 Resumen Estadístico de Entregas")
            conteo = df_filtrado['Estatus de Entrega'].value_counts().reset_index()
            conteo.columns = ['Estatus', 'Cantidad']
            fig = px.pie(conteo, values='Cantidad', names='Estatus', hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Safe)
            fig.update_layout(margin=dict(t=20, b=20, l=10, r=10), height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col_tab:
            st.write("### 🗂️ Matriz Operativa de Datos")
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
        st.info(f"**Detalle técnico:** {resultado}")
        st.markdown("""
        **¿Cómo resolverlo rápido?**
        Verifica en tu Google Sheets que la pestaña seleccionada se llame exactamente igual (ej: `Mayo`, con la primera letra en mayúscula y sin espacios accidentales al principio o al final).
        """)

# =========================================================================
# ⚠️ MÓDULO 2: GESTIÓN DE QUEJAS
# =========================================================================
elif st.session_state.modulo_activo == "⚠️ Gestión de Quejas (Nacional)":
    st.title("⚠️ Gestión Integral de Quejas")
    st.markdown("---")
    
    st.sidebar.header("📅 Historial Operativo")
    anio_seleccionado = st.sidebar.selectbox("Selecciona el Año de Análisis:", ["2025", "2026"], index=0)
    
    # Intentamos cargar la hoja por año o formato BBDD estándar
    df_quejas = cargar_datos_pestana(URL_QUEJAS, anio_seleccionado)
    if isinstance(df_quejas, str):
        df_quejas = cargar_datos_pestana(URL_QUEJAS, f"BBDD {anio_seleccionado}")
        
    if isinstance(df_quejas, pd.DataFrame):
        st.success(f"🟢 Conexión exitosa al repositorio de Quejas ({anio_seleccionado}).")
        st.write("### Muestra de la base operativa de reclamos:")
        st.dataframe(df_quejas.head(15), use_container_width=True)
    else:
        st.error(f"No se pudo sincronizar la pestaña de quejas: {df_quejas}")
