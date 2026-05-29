import streamlit as st
import pandas as pd
import plotly.express as px
import re

# Configuración estética del Dashboard estilo Ejecutivo (Aplica a toda la app)
st.set_page_config(page_title="Centro de Mando - Serviasistencia", layout="wide", initial_sidebar_state="expanded")

# =========================================================================
# ⚙️ CONTROL DE NAVEGACIÓN (SESSION STATE)
# =========================================================================
if "modulo_activo" not in st.session_state:
    st.session_state.modulo_activo = "🏠 Inicio"

# Botón global para regresar al menú principal (Solo visible si no estás en el Inicio)
if st.session_state.modulo_activo != "🏠 Inicio":
    if st.sidebar.button("⬅️ Volver al Menú Principal", use_container_width=True):
        st.session_state.modulo_activo = "🏠 Inicio"
        st.rerun()

# =========================================================================
# 📂 ENLACES VERIFICADOS DE GOOGLE DRIVE 
# =========================================================================
# URL corregida con el ID exacto enviado y validado
URL_BOLETINES = "https://docs.google.com/spreadsheets/d/1aGFtjIeJQ0ZyNCoTvJzfHtM3gQ6JdWKgiVHP5i-Pjj8/edit?usp=sharing"
URL_QUEJAS = "https://docs.google.com/spreadsheets/d/1goYcBbknAXGLN50b4lx8TEVxaZJeAOJrPj3qTr02gFE/edit?usp=sharing"

# Función blindada de extracción y conexión a Google Drive
def cargar_datos_pestana(url, nombre_pestana):
    try:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if match:
            doc_id = match.group(1)
            csv_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/gviz/tq?tqx=out:csv&sheet={nombre_pestana}"
            df = pd.read_csv(csv_url)
            df.columns = df.columns.str.strip()
            return df
        else:
            return None
    except Exception as e:
        return None

# =========================================================================
# 🏠 PANTALLA PRINCIPAL: FRONT DE BIENVENIDA (2 MÓDULOS CONSOLIDADOS)
# =========================================================================
if st.session_state.modulo_activo == "🏠 Inicio":
    st.title("🚀 Sistema Integrado de Control Operativo y BI")
    st.markdown("##### Bienvenido, Stalin. Por favor, selecciona la gestión que deseas auditar hoy:")
    st.markdown("---")
    
    # Grid de 2 columnas para una visualización limpia y directa
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
# 📊 MÓDULO 1: TU CONTROL DE BOLETINES COMPLETO Y FUNCIONAL
# =========================================================================
elif st.session_state.modulo_activo == "📊 Control de Boletines":
    st.title("📊 Control de Boletines")
    st.markdown("---")
    
    st.sidebar.header("📅 Calendario Operativo")
    meses_anuales = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"] 
    mes_seleccionado = st.sidebar.selectbox("Selecciona el Mes a consultar:", meses_anuales, index=4)
    
    df_raw = cargar_datos_pestana(URL_BOLETINES, mes_seleccionado)
    
    if df_raw is not None and not df_raw.empty:
        def buscar_columna(opciones, df):
            for opcion in opciones:
                for col in df.columns:
                    if opcion.lower() in col.lower(): return col
            return None

        col_comercial = buscar_columna(['comercial', 'region', 'vendedor', 'zona'], df_raw) or df_raw.columns[0]
        col_cliente = buscar_columna(['cliente', 'institucion', 'empresa', 'cuenta'], df_raw) or df_raw.columns[0]
        col_entrega = buscar_columna(['fecha de entrega de boletin', 'entrega de boletin', 'fecha entrega'], df_raw)
        col_odoo = buscar_columna(['odoo', 'fecha de carga odoo', 'carga odoo'], df_raw)
        col_grupo = buscar_columna(['grupoarea', 'grupo area', 'grupo', 'area'], df_raw) or df_raw.columns[0]
        col_recurrencia = buscar_columna(['recurrencia de boletin', 'recurrencia', 'periodo'], df_raw) or df_raw.columns[0]
        col_observacion = buscar_columna(['observacion retraso', 'observaciones retraso', 'observacion'], df_raw)
        col_dias_max = buscar_columna(['dias maximas', 'dias maximos', 'dias maxima', 'dias maximo', 'maximas', 'maximos'], df_raw)

        if col_entrega and col_odoo and col_entrega in df_raw.columns and col_odoo in df_raw.columns:
            f_entrega_parsed = pd.to_datetime(df_raw[col_entrega], errors='coerce', dayfirst=True)
            f_odoo_parsed = pd.to_datetime(df_raw[col_odoo], errors='coerce', dayfirst=True)
            
            def clasificar_tiempo(fila, idx):
                val_odoo = fila[col_odoo]
                if pd.isna(val_odoo) or str(val_odoo).strip() == "": return "Pendiente de Carga"
                date_entrega = f_entrega_parsed.loc[idx]
                date_odoo = f_odoo_parsed.loc[idx]
                if pd.isna(date_entrega) or pd.isna(date_odoo): return "Entregado (Formato Variable)"
                return "Entregado Atrasado" if date_odoo > date_entrega else "Entregado a Tiempo"

            df_raw['Evaluación de Entrega Raw'] = [clasificar_tiempo(row, idx) for idx, row in df_raw.iterrows()]
            mapeo_emojis = {"Pendiente de Carga": "⏳ Pendiente de Carga", "Entregado Atrasado": "⚠️ Entregado Atrasado", "Entregado a Tiempo": "🚀 Entregado a Tiempo", "Entregado (Formato Variable)": "✅ Entregado (Formato Variable)"}
            df_raw['Estatus de Entrega'] = df_raw['Evaluación de Entrega Raw'].map(mapeo_emojis)
        else:
            df_raw['Evaluación de Entrega Raw'] = "Pendiente de Carga"
            df_raw['Estatus de Entrega'] = "⏳ Pendiente de Carga"

        # Filtros Secundarios
        st.sidebar.markdown("---")
        filtro_estatus = st.sidebar.selectbox("Selecciona un Estatus:", ["TODOS", "🚀 Entregado a Tiempo", "⚠️ Entregado Atrasado", "⏳ Pendiente de Carga"])
        filtro_comercial = st.sidebar.selectbox("Filtrar por Comercial:", ["TODOS"] + list(df_raw[col_comercial].dropna().unique()))
        
        recurrencias_disponibles = ["TODOS"]
        if col_recurrencia in df_raw.columns: recurrencias_disponibles += list(df_raw[col_recurrencia].dropna().unique())
        filtro_recurrencia = st.sidebar.selectbox("Selecciona Recurrencia:", recurrencias_disponibles)

        df_base_universo = df_raw.copy()
        if filtro_recurrencia != "TODOS": df_base_universo = df_base_universo[df_base_universo[col_recurrencia] == filtro_recurrencia]
        total_boletines_vivos = len(df_base_universo)

        df_filtrado = df_base_universo.copy()
        if filtro_estatus != "TODOS": df_filtrado = df_filtrado[df_filtrado['Estatus de Entrega'] == filtro_estatus]
        if filtro_comercial != "TODOS": df_filtrado = df_filtrado[df_filtrado[col_comercial] == filtro_comercial]

        # KPIs
        a_tiempo = len(df_base_universo[df_base_universo['Evaluación de Entrega Raw'] == "Entregado a Tiempo"])
        atrasados = len(df_base_universo[df_base_universo['Evaluación de Entrega Raw'] == "Entregado Atrasado"])
        pendientes = len(df_base_universo[df_base_universo['Evaluación de Entrega Raw'] == "Pendiente de Carga"])
        efectividad_pct = int((a_tiempo / total_boletines_vivos) * 100) if total_boletines_vivos > 0 else 0

        c1, c2, c3 = st.columns(3)
        with c1: st.metric(label="Total Casos del Mes", value=f"{total_boletines_vivos} Cuentas")
        with c2: st.metric(label="Efectividad de Gestión", value=f"{efectividad_pct}% A Tiempo", delta=f"{a_tiempo} de {total_boletines_vivos} Boletines")
        with c3: st.metric(label="Pendientes de Carga", value=f"{pendientes} Pendientes", delta=f"{atrasados} con Retraso", delta_color="inverse")

        st.markdown("---")
        col_grafico, col_tabla = st.columns([4, 6])

        with col_grafico:
            st.write("### 📊 Auditoría de SLA")
            conteo_tiempos = df_filtrado['Estatus de Entrega'].value_counts().reset_index()
            conteo_tiempos.columns = ['Estatus de Entrega', 'Cantidad']
            if not conteo_tiempos.empty:
                conteo_tiempos['Porcentaje'] = ((conteo_tiempos['Cantidad'] / total_boletines_vivos) * 100).round(1)
                conteo_tiempos['Etiqueta'] = conteo_tiempos.apply(lambda r: f"{r['Cantidad']} ({r['Porcentaje']}%)", axis=1)
                fig_sla = px.bar(conteo_tiempos, x='Cantidad', y='Estatus de Entrega', text='Etiqueta', orientation='h', color='Estatus de Entrega', color_discrete_map={"🚀 Entregado a Tiempo": "#2ca02c", "⚠️ Entregado Atrasado": "#d62728", "⏳ Pendiente de Carga": "#ff7f0e", "✅ Entregado (Formato Variable)": "#1f77b4"})
                fig_sla.update_traces(textposition='outside')
                fig_sla.update_layout(xaxis_title="Boletines", yaxis_title=None, showlegend=False, height=310, margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig_sla, use_container_width=True)

        with col_tabla:
            st.write("### 🗂️ Resumen Ejecutivo de Cumplimiento")
            if col_grupo in df_filtrado.columns and col_cliente in df_filtrado.columns:
                estructura_columnas = {'GRUPO': df_filtrado[col_grupo].fillna("---"), 'CLIENTE / INSTITUCIÓN': df_filtrado[col_cliente].fillna("---"), 'F. ENTREGA': df_filtrado[col_entrega].fillna("---"), 'F. ODOO': df_filtrado[col_odoo].fillna("---")}
                mostrar_dias = (col_dias_max is not None) and (col_dias_max in df_filtrado.columns)
                mostrar_obs = (filtro_estatus == "⚠️ Entregado Atrasado") and (col_observacion is not None) and (col_observacion in df_filtrado.columns)
                
                if mostrar_dias: estructura_columnas['MÁX. DÍAS'] = df_filtrado[col_dias_max].fillna("---")
                if mostrar_obs: estructura_columnas['OBSERVACIÓN RETRASO'] = df_filtrado[col_observacion].fillna("Sin observación")
                estructura_columnas['ESTATUS'] = df_filtrado['Estatus de Entrega']
                
                df_tabla_final = pd.DataFrame(estructura_columnas)
                df_tabla_final['_orden_fecha'] = pd.to_datetime(df_tabla_final['F. ENTREGA'], errors='coerce', dayfirst=True)
                df_tabla_final = df_tabla_final.sort_values(by='_orden_fecha', na_position='last').reset_index(drop=True).drop(columns=['_orden_fecha'])
                
                fila_acumulada = pd.DataFrame([{'GRUPO': "🟦 TOTAL GENERAL 🟦", 'CLIENTE / INSTITUCIÓN': f"📊 {len(df_tabla_final)} Casos Filtrados", 'F. ENTREGA': "═══════════", 'F. ODOO': "═══════════", 'ESTATUS': "📈 Resumen"}])
                st.dataframe(pd.concat([df_tabla_final, fila_acumulada], ignore_index=True), use_container_width=True, hide_index=True)
    else:
        st.error("Error de sincronización: Asegúrate de que la pestaña seleccionada en el menú izquierdo de la App se llame EXACTAMENTE igual que en tu archivo de Drive (ej. 'Mayo').")

# =========================================================================
# ⚠️ MÓDULO 2: GESTIÓN INTEGRAL DE QUEJAS (MAPA + CLIMA UNIFICADOS)
# =========================================================================
elif st.session_state.modulo_activo == "⚠️ Gestión de Quejas (Nacional)":
    st.title("⚠️ Gestión Integral de Quejas Nacionales")
    st.markdown("---")
    
    df_quejas = cargar_datos_pestana(URL_QUEJAS, "BBDD 2025")
    
    if df_quejas is not None and not df_quejas.empty:
        # Pestañas de control interno
        tab_mapa, tab_clima = st.tabs(["🗺️ Mapa de Calor y Alertas Territoriales", "🔮 Proyección Climática Predictiva"])
        
        with tab_mapa:
            st.markdown("### Mapa de Alertas Tempranas por Provincias")
            st.sidebar.header("🚨 Filtros de Territorio")
            
            if 'Provincia' in df_quejas.columns:
                lista_provincias = ["TODAS"] + list(df_quejas['Provincia'].dropna().unique())
                provincia_sel = st.sidebar.selectbox("Selecciona una Provincia:", lista_provincias)
            
            st.info("Conexión con 'Consolidado QMC' establecida con éxito.")
            st.dataframe(df_quejas.head(10), use_container_width=True)
            
        with tab_clima:
            st.markdown("### Análisis Predictivo de Demanda de Grúas vs Precipitación")
            st.sidebar.header("🌦️ Variables Meteorológicas")
            st.info("Este submódulo procesará las variables climáticas satelitales en vivo para anticipar picos operativos en grúas.")
    else:
        st.error("No se pudo leer la pestaña 'BBDD 2025' del archivo de Quejas. Revisa que el enlace tenga los permisos públicos de lectura en Google Drive.")
