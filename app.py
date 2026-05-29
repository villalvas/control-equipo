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
URL_BOLETINES = "https://docs.google.com/spreadsheets/d/1aGFtjIeJQ0ZyNCoTvJzfHtM3gQ6JdwKgiVHP5i-Pjj8/edit?usp=sharing"
URL_QUEJAS = "https://docs.google.com/spreadsheets/d/1goYcBbknAXGLN50b4lx8TEVxaZJeAOJrPj3qTr02gFE/edit?usp=sharing"

# Función de extracción avanzada: Extrae el ID del documento de forma inmune a fallos
def cargar_datos_pestana(url, nombre_pestana):
    try:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if match:
            doc_id = match.group(1)
            pestana_limpia = str(nombre_pestana).strip().replace(" ", "%20")
            csv_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/gviz/tq?tqx=out:csv&sheet={pestana_limpia}"
            
            df = pd.read_csv(csv_url)
            df.columns = df.columns.str.strip()
            df = df.dropna(how='all')
            return df
        return None
    except Exception:
        return None

# =========================================================================
# 🏠 PANTALLA PRINCIPAL: FRONT DE BIENVENIDA (MÓDULOS CONSOLIDADOS)
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
# 📊 MÓDULO 1: CONTROL DE BOLETINES (MAPEADO EXACTO A TU EXCEL REAL)
# =========================================================================
elif st.session_state.modulo_activo == "📊 Control de Boletines":
    st.title("📊 Control de Boletines")
    st.markdown("---")
    
    st.sidebar.header("📅 Calendario Operativo")
    meses_anuales = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"] 
    mes_seleccionado = st.sidebar.selectbox("Selecciona el Mes a consultar:", meses_anuales, index=4)
    
    df_raw = cargar_datos_pestana(URL_BOLETINES, mes_seleccionado)
    
    if df_raw is not None and not df_raw.empty:
        # Buscador inteligente adaptado a los encabezados reales de tus capturas
        def buscar_columna(opciones, df):
            for opcion in opciones:
                for col in df.columns:
                    if opcion.lower() in col.lower(): return col
            return None

        # Asignaciones basadas estrictamente en la anatomía de tu documento de Drive
        col_grupo = buscar_columna(['grupo'], df_raw) or df_raw.columns[0]
        col_comercial = buscar_columna(['area comercial', 'comercial', 'region'], df_raw) or df_raw.columns[1]
        col_cliente = buscar_columna(['te instituc', 'instituc', 'cliente', 'empresa'], df_raw) or df_raw.columns[2]
        col_recurrencia = buscar_columna(['rencia de b', 'recurrencia', 'periodo'], df_raw) or df_raw.columns[3]
        
        # Columnas de fechas y alertas
        col_entrega = buscar_columna(['fecha de entrega', 'entrega de boletin', 'fecha entrega'], df_raw)
        col_odoo = buscar_columna(['odoo', 'fecha de carga', 'carga odoo'], df_raw)
        col_observacion = buscar_columna(['observacion retraso', 'observaciones', 'motivo'], df_raw)
        col_dias_max = buscar_columna(['dias maximas', 'maximas', 'dias maximos', 'dias maximo'], df_raw)

        # Evaluación de tiempos de SLA
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

        st.sidebar.markdown("---")
        filtro_estatus = st.sidebar.selectbox("Selecciona un Estatus:", ["TODOS", "🚀 Entregado a Tiempo", "⚠️ Entregado Atrasado", "⏳ Pendiente de Carga"])
        
        filtro_comercial = "TODOS"
        if col_comercial in df_raw.columns:
            filtro_comercial = st.sidebar.selectbox("Filtrar por Área Comercial:", ["TODOS"] + list(df_raw[col_comercial].dropna().unique()))
        
        recurrencias_disponibles = ["TODOS"]
        if col_recurrencia in df_raw.columns: 
            recurrencias_disponibles += list(df_raw[col_recurrencia].dropna().unique())
        filtro_recurrencia = st.sidebar.selectbox("Selecciona Recurrencia:", recurrencias_disponibles)

        # Aplicación de los filtros dinámicos sobre el dataframe principal
        df_base_universo = df_raw.copy()
        if col_recurrencia in df_base_universo.columns and filtro_recurrencia != "TODOS": 
            df_base_universo = df_base_universo[df_base_universo[col_recurrencia] == filtro_recurrencia]
        total_boletines_vivos = len(df_base_universo)

        df_filtrado = df_base_universo.copy()
        if filtro_estatus != "TODOS": 
            df_filtrado = df_filtrado[df_filtrado['Estatus de Entrega'] == filtro_estatus]
        if col_comercial in df_filtrado.columns and filtro_comercial != "TODOS": 
            df_filtrado = df_filtrado[df_filtrado[col_comercial] == filtro_comercial]

        # Cálculo de las métricas principales de control
        a_tiempo = len(df_base_universo[df_base_universo['Evaluación de Entrega Raw'] == "Entregado a Tiempo"])
        atrasados = len(df_base_universo[df_base_universo['Evaluación de Entrega Raw'] == "Entregado Atrasado"])
        pendientes = len(df_base_universo[df_base_universo['Evaluación de Entrega Raw'] == "Pendiente de Carga"])
        efectividad_pct = int((a_tiempo / total_boletines_vivos) * 100) if total_boletines_vivos > 0 else 0

        # Bloque de visualización de KPI Metrics
        c1, c2, c3 = st.columns(3)
        with c1: st.metric(label="Total Casos del Mes", value=f"{total_boletines_vivos} Cuentas")
        with c2: st.metric(label="Efectividad de Gestión", value=f"{efectividad_pct}% A Tiempo", delta=f"{a_tiempo} de {total_boletines_vivos} Boletines")
        with c3: st.metric(label="Pendientes de Carga", value=f"{pendientes} Pendientes", delta=f"{atrasados} con Retraso", delta_color="inverse")

        st.markdown("---")
        col_grafico, col_tabla = st.columns([4, 6])

        with col_grafico:
            st.write("### 📊 Auditoría de SLA")
            if 'Estatus de Entrega' in df_filtrado.columns:
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
            # Estructuración y modelado final de la tabla para visualización de Stalin
            estructura_columnas = {
                'GRUPO': df_filtrado[col_grupo].fillna("---"), 
                'ÁREA COMERCIAL': df_filtrado[col_comercial].fillna("---"),
                'CLIENTE / INSTITUCIÓN': df_filtrado[col_cliente].fillna("---")
            }
            
            if col_entrega and col_entrega in df_filtrado.columns: estructura_columnas['F. ENTREGA'] = df_filtrado[col_entrega].fillna("---")
            if col_odoo and col_odoo in df_filtrado.columns: estructura_columnas['F. ODOO'] = df_filtrado[col_odoo].fillna("---")
            if col_dias_max and col_dias_max in df_filtrado.columns: estructura_columnas['MÁX. DÍAS'] = df_filtrado[col_dias_max].fillna("---")
            if (filtro_estatus == "⚠️ Entregado Atrasado") and col_observacion and col_observacion in df_filtrado.columns: 
                estructura_columnas['OBSERVACIÓN RETRASO'] = df_filtrado[col_observacion].fillna("Sin observacion")
                
            estructura_columnas['ESTATUS'] = df_filtrado['Estatus de Entrega']
            df_tabla_final = pd.DataFrame(estructura_columnas)
            
            fila_acumulada = pd.DataFrame([{'GRUPO': "🟦 TOTAL GENERAL 🟦", 'ÁREA COMERCIAL': "═══════════", 'CLIENTE / INSTITUCIÓN': f"📊 {len(df_tabla_final)} Casos Filtrados", 'ESTATUS': "📈 Resumen"}])
            st.dataframe(pd.concat([df_tabla_final, fila_acumulada], ignore_index=True), use_container_width=True, hide_index=True)
    else:
        st.error(f"Error crítico de sincronización: No se pudo mapear la estructura de la pestaña '{mes_seleccionado}'. Asegúrate de que las columnas del archivo sigan el orden predeterminado.")

# =========================================================================
# ⚠️ MÓDULO 2: GESTIÓN INTEGRAL DE QUEJAS (BUSCA FORMATOS '2025' O 'BBDD 2025')
# =========================================================================
elif st.session_state.modulo_activo == "⚠️ Gestión de Quejas (Nacional)":
    st.title("⚠️ Gestión Integral de Quejas Nacionales")
    st.markdown("---")
    
    st.sidebar.header("📅 Historial Operativo")
    anio_seleccionado = st.sidebar.selectbox("Selecciona el Año de Auditoría:", ["2025", "2026"], index=0)
    
    df_quejas = cargar_datos_pestana(URL_QUEJAS, anio_seleccionado)
    if df_quejas is None or df_quejas.empty:
        df_quejas = cargar_datos_pestana(URL_QUEJAS, f"BBDD {anio_seleccionado}")
    
    if df_quejas is not None and not df_quejas.empty:
        tab_mapa, tab_clima = st.tabs(["🗺️ Mapa de Calor y Alertas Territoriales", "🔮 Proyección Climática Predictiva"])
        
        with tab_mapa:
            st.markdown(f"### Mapa de Alertas Tempranas por Provincias - Periodo {anio_seleccionado}")
            st.sidebar.header("🚨 Filtros de Territorio")
            
            col_provincia = None
            for col in df_quejas.columns:
                if 'prov' in col.lower() or 'terr' in col.lower() or 'regi' in col.lower() or 'zona' in col.lower():
                    col_provincia = col
                    break
            
            if col_provincia:
                lista_provincias = ["TODAS"] + list(df_quejas[col_provincia].dropna().unique())
                provincia_sel = st.sidebar.selectbox("Selecciona la Región/Provincia:", lista_provincias)
            
            st.success(f"¡Sincronización Exitosa! Conectado correctamente al archivo 'Control de Quejas' en Drive.")
            st.write("##### Vista previa del Consolidado General de Quejas:")
            st.dataframe(df_quejas.head(15), use_container_width=True)
            
        with tab_clima:
            st.markdown("### Análisis Predictivo de Demanda de Grúas vs Precipitación")
            st.sidebar.header("🌦️ Variables Meteorológicas")
            st.info("Este submódulo procesará las variables climáticas satelitales en vivo para anticipar picos operativos en grúas.")
    else:
        st.error(f"No se pudo encontrar o leer la pestaña correspondiente al año '{anio_seleccionado}' en el archivo 'Control de Quejas'.")
