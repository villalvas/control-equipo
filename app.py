import streamlit as st
import pandas as pd
import plotly.express as px
import re

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
URL_BOLETINES = "https://docs.google.com/spreadsheets/d/1aGFtjIeJQ0ZyNCoTvJzfHtM3gQ6JdwKgiVHP5i-Pjj8/edit?usp=sharing"
URL_QUEJAS = "https://docs.google.com/spreadsheets/d/1goYcBbknAXGLN50b4lx8TEVxaZJeAOJrPj3qTr02gFE/edit?usp=sharing"

# Función de extracción optimizada y blindada contra errores 404
def cargar_datos_pestana(url, nombre_pestana):
    try:
        # Extraer el ID del documento
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if match:
            doc_id = match.group(1)
            # Enlace de exportación limpia recomendada por Google
            csv_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&sheet={nombre_pestana}"
            
            # Leer los datos forzando el formato de texto y saltando líneas erróneas
            df = pd.read_csv(csv_url, on_bad_lines='skip')
            
            if df.empty:
                return "El archivo se descargó pero la estructura está vacía."
                
            # Limpieza profunda de los nombres de las columnas
            df.columns = [str(c).strip() for c in df.columns]
            df = df.loc[:, ~df.columns.str.contains('^Unnamed:')]
            df = df.dropna(how='all')
            return df
        return "No se pudo extraer un ID válido de la URL de Google Drive."
    except Exception as e:
        return str(e)

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
        st.markdown("### ⚠️ Gestión Integral de Quejas")
        st.warning("Mapa de calor dinámico nacional, alertas territoriales y módulo de analítica predictiva por clima.")
        if st.button("Ingresar a Control de Quejas", key="btn_quejas", use_container_width=True):
            st.session_state.modulo_activo = "⚠️ Gestión de Quejas (Nacional)"
            st.rerun()

# =========================================================================
# 📊 MÓDULO 1: CONTROL DE BOLETINES
# =========================================================================
elif st.session_state.modulo_activo == "📊 Control de Boletines":
    st.title("📊 Control de Boletines")
    st.markdown("---")
    
    st.sidebar.header("📅 Calendario Operativo")
    meses_anuales = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"] 
    mes_seleccionado = st.sidebar.selectbox("Selecciona el Mes a consultar:", meses_anuales, index=4) # Por defecto Mayo
    
    resultado = cargar_datos_pestana(URL_BOLETINES, mes_seleccionado)
    
    # Comprobar si la carga fue exitosa (devolvió un DataFrame)
    if isinstance(resultado, pd.DataFrame):
        df_raw = resultado
        
        # Buscador inteligente de columnas basado en tu captura real
        def detectar_columna(keys, columnas_disponibles):
            for k in keys:
                for col in columnas_disponibles:
                    if k.lower() in col.lower():
                        return col
            return columnas_disponibles[0] if len(columnas_disponibles) > 0 else None

        col_grupo = detectar_columna(['grupo'], df_raw.columns)
        col_comercial = detectar_columna(['area comercial', 'comercial'], df_raw.columns)
        col_cliente = detectar_columna(['te instituc', 'instituc', 'cliente'], df_raw.columns)
        col_recurrencia = detectar_columna(['rencia', 'recurrencia'], df_raw.columns)
        col_entrega = detectar_columna(['fecha de entrega', 'entrega'], df_raw.columns)
        col_odoo = detectar_columna(['odoo', 'carga'], df_raw.columns)
        col_dias_max = detectar_columna(['dias max', 'maximas', 'maximo'], df_raw.columns)

        # Análisis de Estatus SLA automático
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
            df_raw['Estatus de Entrega'] = "⏳ En Proceso / Sin Fechas"

        # Filtros en la barra lateral
        st.sidebar.markdown("---")
        filtro_estatus = st.sidebar.selectbox("Filtrar por Estatus SLA:", ["TODOS"] + list(df_raw['Estatus de Entrega'].unique()))
        
        filtro_comercial = "TODOS"
        if col_comercial and col_comercial in df_raw.columns:
            valores_comercial = ["TODOS"] + list(df_raw[col_comercial].dropna().unique())
            filtro_comercial = st.sidebar.selectbox("Filtrar por Área Comercial:", valores_comercial)

        # Aplicar los filtros
        df_filtrado = df_raw.copy()
        if filtro_estatus != "TODOS":
            df_filtrado = df_filtrado[df_filtrado['Estatus de Entrega'] == filtro_estatus]
        if col_comercial and filtro_comercial != "TODOS":
            df_filtrado = df_filtrado[df_filtrado[col_comercial] == filtro_comercial]

        # Despliegue de Indicadores Clave (KPIs)
        total_casos = len(df_raw)
        casos_filtrados = len(df_filtrado)
        
        c1, c2, c3 = st.columns(3)
        with c1: st.metric(label="Total Registros en Drive", value=f"{total_casos} Filas")
        with c2: st.metric(label="Registros Filtrados", value=f"{casos_filtrados} Filas")
        with c3: st.metric(label="Estatus Conexión", value="🟢 Activa")

        st.markdown("---")
        
        # Visualizaciones del Dashboard
        col_graf, col_tab = st.columns([4, 6])
        
        with col_graf:
            st.write("### 📊 Proporción del Estado Operativo")
            conteo = df_filtrado['Estatus de Entrega'].value_counts().reset_index()
            conteo.columns = ['Estatus', 'Cantidad']
            fig = px.pie(conteo, values='Cantidad', names='Estatus', hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(margin=dict(t=20, b=20, l=10, r=10), height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col_tab:
            st.write("### 🗂️ Vista de Datos del Archivo Real")
            cols_mostrar = {}
            if col_grupo: cols_mostrar['Grupo'] = df_filtrado[col_grupo]
            if col_comercial: cols_mostrar['Área Comercial'] = df_filtrado[col_comercial]
            if col_cliente: cols_mostrar['Cliente / Institución'] = df_filtrado[col_cliente]
            if col_entrega in df_filtrado.columns: cols_mostrar['F. Entrega'] = df_filtrado[col_entrega]
            if col_odoo in df_filtrado.columns: cols_mostrar['F. Odoo'] = df_filtrado[col_odoo]
            cols_mostrar['Estado'] = df_filtrado['Estatus de Entrega']
            
            st.dataframe(pd.DataFrame(cols_mostrar).fillna("---"), use_container_width=True, hide_index=True)

    else:
        # En caso de que falle, se muestra esta ventana informativa interactiva
        st.error("🚨 **Error de Sincronización con Google Drive**")
        st.warning(f"**Detalle Devuelto por los Servidores:** {resultado}")
        
        st.markdown("""
        ### 🔍 Pasos para solucionar esto en 1 minuto:
        1. Ve a tu archivo de Google Drive (**Control de Boletines**).
        2. Mira el nombre de la pestaña abajo del todo. Asegúrate de que no tenga un espacio al final (ej: escribir `"Mayo "` con un espacio invisible hará que falle). Debe ser exactamente **`Mayo`**.
        3. Si el error persiste, es probable que Google requiera el ID interno de la hoja. ¡Pásame el mensaje que aparezca arriba en el cuadro amarillo para darte la solución quirúrgica!
        """)

# =========================================================================
# ⚠️ MÓDULO 2: GESTIÓN INTEGRAL DE QUEJAS
# =========================================================================
elif st.session_state.modulo_activo == "⚠️ Gestión de Quejas (Nacional)":
    st.title("⚠️ Gestión Integral de Quejas Nacionales")
    st.markdown("---")
    
    st.sidebar.header("📅 Historial Operativo")
    anio_seleccionado = st.sidebar.selectbox("Selecciona el Año de Auditoría:", ["2025", "2026"], index=0)
    
    df_quejas = cargar_datos_pestana(URL_QUEJAS, anio_seleccionado)
    
    if isinstance(df_quejas, pd.DataFrame):
        st.success(f"¡Sincronización Exitosa! Conectado al módulo de Quejas.")
        st.dataframe(df_quejas.head(15), use_container_width=True)
    else:
        st.error(f"No se pudo leer el archivo de Quejas: {df_quejas}")
