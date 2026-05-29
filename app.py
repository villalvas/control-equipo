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

# Nueva función de extracción usando exportación directa (Inmune a celdas vacías)
def cargar_datos_pestana(url, nombre_pestana):
    try:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
        if match:
            doc_id = match.group(1)
            pestana_limpia = str(nombre_pestana).strip().replace(" ", "%20")
            # Método alternativo ultra-estable para Google Sheets
            csv_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&sheet={pestana_limpia}"
            
            # Forzamos la lectura ignorando líneas corruptas si las hay
            df = pd.read_csv(csv_url, on_bad_lines='skip')
            
            # Limpieza de nombres de columnas
            df.columns = [str(c).strip() for c in df.columns]
            # Eliminar columnas sin nombre
            df = df.loc[:, ~df.columns.str.contains('^Unnamed:')]
            # Conservar solo filas donde haya al menos algún dato operativo
            df = df.dropna(how='all')
            return df
        return None
    except Exception as e:
        # Retornamos el error textualmente para diagnóstico en la UI si falla
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
# 📊 MÓDULO 1: CONTROL DE BOLETINES (PROCESAMIENTO DINÁMICO FLEXIBLE)
# =========================================================================
elif st.session_state.modulo_activo == "📊 Control de Boletines":
    st.title("📊 Control de Boletines")
    st.markdown("---")
    
    st.sidebar.header("📅 Calendario Operativo")
    meses_anuales = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"] 
    mes_seleccionado = st.sidebar.selectbox("Selecciona el Mes a consultar:", meses_anuales, index=4)
    
    resultado = cargar_datos_pestana(URL_BOLETINES, mes_seleccionado)
    
    # Validamos si la respuesta es el DataFrame esperado o un string de error
    if isinstance(resultado, pd.DataFrame) and not resultado.empty:
        df_raw = resultado
        
        # Asignación segura de columnas mediante búsquedas parciales inteligentes
        def detectar_columna(keys, columnas_disponibles):
            for k in keys:
                for col in columnas_disponibles:
                    if k.lower() in col.lower():
                        return col
            return columnas_disponibles[0] if len(columnas_disponibles) > 0 else None

        col_grupo = detectar_columna(['grupo'], df_raw.columns)
        col_comercial = detectar_columna(['area comercial', 'comercial', 'vendedor'], df_raw.columns)
        col_cliente = detectar_columna(['te instituc', 'instituc', 'cliente', 'cuenta'], df_raw.columns)
        col_recurrencia = detectar_columna(['rencia', 'recurrencia', 'periodo'], df_raw.columns)
        col_entrega = detectar_columna(['fecha de entrega', 'entrega de boletin'], df_raw.columns)
        col_odoo = detectar_columna(['odoo', 'fecha de carga'], df_raw.columns)
        col_dias_max = detectar_columna(['dias max', 'maximas', 'maximo'], df_raw.columns)

        # Configuración automática del estatus operativo (SLA)
        if col_entrega and col_odoo in df_raw.columns:
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
            df_raw['Estatus de Entrega'] = "⏳ Pendiente de Carga"

        # Barra lateral de filtrado interactivo
        st.sidebar.markdown("---")
        filtro_estatus = st.sidebar.selectbox("Filtrar por Estatus SLA:", ["TODOS"] + list(df_raw['Estatus de Entrega'].unique()))
        
        filtro_comercial = "TODOS"
        if col_comercial and col_comercial in df_raw.columns:
            valores_comercial = ["TODOS"] + list(df_raw[col_comercial].dropna().unique())
            filtro_comercial = st.sidebar.selectbox("Filtrar por Área Comercial:", valores_comercial)

        # Aplicación efectiva de filtros sobre el set de datos
        df_filtrado = df_raw.copy()
        if filtro_estatus != "TODOS":
            df_filtrado = df_filtrado[df_filtrado['Estatus de Entrega'] == filtro_estatus]
        if col_comercial and filtro_comercial != "TODOS":
            df_filtrado = df_filtrado[df_filtrado[col_comercial] == filtro_comercial]

        # Componente de Métricas Generales (KPIs)
        total_casos = len(df_raw)
        casos_filtrados = len(df_filtrado)
        a_tiempo = len(df_raw[df_raw['Estatus de Entrega'] == "🚀 Entregado a Tiempo"])
        pct_cumplimiento = int((a_tiempo / total_casos) * 100) if total_casos > 0 else 0

        c1, c2, c3 = st.columns(3)
        with c1: st.metric(label="Universo Total de Cuentas", value=f"{total_casos} Registros")
        with c2: st.metric(label="Cumplimiento Global (SLA)", value=f"{pct_cumplimiento}% Eficiencia")
        with c3: st.metric(label="Registros en Vista Actual", value=f"{casos_filtrados} Filas")

        st.markdown("---")
        
        # Sección visual: Distribución Gráfica e Indicadores en Tabla
        col_graf, col_tab = st.columns([4, 6])
        
        with col_graf:
            st.write("### 📊 Proporción de Cumplimiento")
            conteo = df_filtrado['Estatus de Entrega'].value_counts().reset_index()
            conteo.columns = ['Estatus', 'Cantidad']
            fig = px.pie(conteo, values='Cantidad', names='Estatus', hole=0.4,
                         color_discrete_map={"🚀 Entregado a Tiempo": "#2ca02c", "⚠️ Entregado Atrasado": "#d62728", "⏳ Pendiente de Carga": "#ff7f0e", "✅ Entregado": "#1f77b4"})
            fig.update_layout(margin=dict(t=20, b=20, l=10, r=10), height=300)
            st.plotly_chart(fig, use_container_width=True)

        with col_tab:
            st.write("### 🗂️ Vista de Datos Estructurada")
            # Mapeamos columnas de manera segura verificando que existan en el set procesado
            cols_mostrar = {}
            if col_grupo: cols_mostrar['Grupo'] = df_filtrado[col_grupo]
            if col_comercial: cols_mostrar['Área Comercial'] = df_filtrado[col_comercial]
            if col_cliente: cols_mostrar['Cliente / Institución'] = df_filtrado[col_cliente]
            if col_entrega in df_filtrado.columns: cols_mostrar['F. Entrega'] = df_filtrado[col_entrega]
            if col_odoo in df_filtrado.columns: cols_mostrar['F. Odoo'] = df_filtrado[col_odoo]
            cols_mostrar['Estado SLA'] = df_filtrado['Estatus de Entrega']
            
            st.dataframe(pd.DataFrame(cols_mostrar).fillna("---"), use_container_width=True, hide_index=True)

    else:
        st.error("🚨 **Error de Interconexión con Google Sheets**")
        st.warning(f"Detalle técnico del error: {resultado}")
        st.info("💡 **Recomendación:** Verifica que el nombre de la pestaña en tu archivo de Drive se llame exactamente igual al mes seleccionado en el menú izquierdo (ej: **Mayo**, cuidando mayúsculas y minúsculas).")

# =========================================================================
# ⚠️ MÓDULO 2: GESTIÓN INTEGRAL DE QUEJAS
# =========================================================================
elif st.session_state.modulo_activo == "⚠️ Gestión de Quejas (Nacional)":
    st.title("⚠️ Gestión Integral de Quejas Nacionales")
    st.markdown("---")
    
    st.sidebar.header("📅 Historial Operativo")
    anio_seleccionado = st.sidebar.selectbox("Selecciona el Año de Auditoría:", ["2025", "2026"], index=0)
    
    df_quejas = cargar_datos_pestana(URL_QUEJAS, anio_seleccionado)
    if isinstance(df_quejas, str) or df_quejas is None or df_quejas.empty:
        df_quejas = cargar_datos_pestana(URL_QUEJAS, f"BBDD {anio_seleccionado}")
    
    if isinstance(df_quejas, pd.DataFrame) and not df_quejas.empty:
        st.success(f"¡Sincronización Exitosa! Conectado al módulo de Quejas.")
        st.write("##### Muestra de datos extraídos:")
        st.dataframe(df_quejas.head(15), use_container_width=True)
    else:
        st.error(f"No se pudo leer la pestaña correspondiente al año '{anio_seleccionado}' en el archivo de Quejas.")
