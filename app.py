import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time
import math

# 1. Configuración de pantalla ultra ancha para el monitor de control
st.set_page_config(
    layout="wide", 
    page_title="Monitor de Proyecciones 2026 - Control de Flota",
    initial_sidebar_state="collapsed"
)

# Estilos CSS corporativos y tamaño de letra optimizado para pantallas de control
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDataFrame [data-testid="stDataFrameDownloadButton"] {display: none;}
    button[title="View fullscreen"] {display: none;}
    
    /* 🚀 Tamaño de texto optimizado en celdas y encabezados */
    [data-testid="stTable"] td, [data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] [role="gridcell"] {
        font-size: 16px !important;
        font-weight: 500 !important;
    }
    [data-testid="stTable"] th, [data-testid="stDataFrame"] th, div[data-testid="stDataFrame"] [role="columnheader"] {
        font-size: 17px !important;
        font-weight: bold !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 🔄 Mecanismo de auto-refresco automático (Cada 5 minutos)
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# Definimos la zona horaria de Ecuador de forma explícita
zona_ecuador = ZoneInfo("America/Guayaquil")
hora_ecuador_actual = datetime.now(zona_ecuador)

st.title("🔮 Monitor de Proyección Horaria y Alerta Temprana de Flota")

# Indicador de sincronización en vivo
st.caption(f"Centro de Control Geoanalítico con Monitoreo de Clima Online | 🔄 Auto-refresco activo cada 5 min (Último: {hora_ecuador_actual.strftime('%I:%M:%S %p')})")

coordenadas_provincias = {
    'PICHINCHA': [-0.2298, -78.5249], 'GUAYAS': [-2.1894, -79.8890], 'AZUAY': [-2.9001, -79.0059],
    'MANABI': [-1.0543, -80.4544], 'MANABÍ': [-1.0543, -80.4544], 'EL ORO': [-3.2581, -79.9553], 
    'LOJA': [-3.9931, -79.2042], 'TUNGURAHUA': [-1.2491, -78.6168], 'CHIMBORAZO': [-1.6743, -78.6483], 
    'ESMERALDAS': [0.9682, -79.6517], 'LOS RIOS': [-1.4558, -79.4622], 'LOS RÍOS': [-1.4558, -79.4622],
    'SANTO DOMINGO DE LOS TSÁCHILAS': [-0.2530, -79.1754], 'SANTO DOMINGO DE LOS TSACHILAS': [-0.2530, -79.1754], 
    'SANTA ELENA': [-2.2262, -80.8584], 'IMBABURA': [0.3517, -78.1223], 'COTOPAXI': [-0.9352, -78.6155], 
    'CARCHI': [0.7384, -77.7289], 'SUCUMBIOS': [0.0847, -76.8828], 'SUCUMBÍOS': [0.0847, -76.8828],
    'ORELLANA': [-0.5665, -76.9872], 'NAPO': [-0.9902, -77.8129], 'PASTAZA': [-1.4870, -77.9954], 
    'MORONA SANTIAGO': [-2.3087, -78.1114], 'ZAMORA CHINCHIPE': [-4.0692, -78.9566],
    'GALAPAGOS': [-0.7402, -90.3119], 'GALÁPAGOS': [-0.7402, -90.3119], 'BOLIVAR': [-1.5910, -79.0022], 
    'BOLÍVAR': [-1.5910, -79.0022], 'CAÑAR': [-2.5518, -78.9392]
}

diccionario_dias = {
    "LUNES": 0, "MARTES": 1, "MIÉRCOLES": 2, "MIERCOLES": 2, 
    "JUEVES": 3, "VIERNES": 4, "SÁBADO": 5, "SABADO": 5, "DOMINGO": 6
}

# 🚀 CONSULTA DE CLIMA EN VIVO DESDE LA API ONLINE
@st.cache_data(ttl=300)
def obtener_clima_horario_futuro(lat, lon, fecha_objetivo_str):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,weathercode&timezone=auto&forecast_days=7"
        respuesta = requests.get(url).json()
        horas_raw = respuesta['hourly']['time']
        temperaturas = respuesta['hourly']['temperature_2m']
        codigos_clima = respuesta['hourly']['weathercode']
        
        datos_clima = {}
        for h, temp, codigo in zip(horas_raw, temperaturas, codigos_clima):
            fecha_part, hora_part = h.split("T")
            if fecha_part == fecha_objetivo_str:
                hora_int = int(hora_part.split(":")[0])
                if codigo == 0: estado, icono = "Despejado", "☀️"
                elif codigo in [1, 2, 3]: estado, icono = "Nublado", "☁️"
                elif codigo in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99]: estado, icono = "Lluvia", "🌧️"
                else: estado, icono = "Nublado", "☁️"
                datos_clima[hora_int] = {"Detalle": f"{icono} {estado} ({temp}°C)", "Icono": icono, "Estado": estado}
        
        return datos_clima if datos_clima else {i: {"Detalle": "⚪ Sin Predicción", "Icono": "⚪", "Estado": "Normal"} for i in range(24)}
    except:
        return {i: {"Detalle": "⚪ Sin Conexión", "Icono": "⚪", "Estado": "Normal"} for i in range(24)}

# 🚀 CÁLCULO CIENTÍFICO DEL MULTIPLICADOR HISTÓRICO DE LLUVIA
@st.cache_data(ttl=3600)
def calcular_factor_lluvia_en_vivo(df_historico, lat, lon):
    try:
        df_quick = df_historico.dropna(subset=["FECHA CREACIÓN DE ASISTENCIA", "HORA CREACIÓN DE ASISTENCIA"]).tail(60)
        if df_quick.empty:
            return 1.35
        
        fechas_unicas = df_quick["FECHA CREACIÓN DE ASISTENCIA"].astype(str).str.split().str[0].unique()
        lluvias_detectadas = 0
        total_evaluado = 0
        
        for fecha in fechas_unicas[:4]:
            url_historial = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={fecha}&end_date={fecha}&hourly=weathercode&timezone=auto"
            res = requests.get(url_historial).json()
            if 'hourly' in res:
                codigos = res['hourly']['weathercode']
                lluvias_detectadas += sum(1 for c in codigos if c in [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99])
                total_evaluado += len(codigos)
        
        if total_evaluado > 0 and lluvias_detectadas > 0:
            ratio = lluvias_detectadas / total_evaluado
            return round(1.2 + (ratio * 1.5), 2)
        return 1.35
    except:
        return 1.35

@st.cache_data(ttl=60)
def cargar_datos_vía_gviz():
    try:
        url_base = "https://docs.google.com/spreadsheets/d/1UWQy9XJy8UOdef1IcXWDt2Nmn7hTnsQLHby_3BhpJnc/edit"
        pestana = "Consolidado"
        csv_url = url_base.replace('/edit', f'/gviz/tq?tqx=out:csv&sheet={pestana}')
        df = pd.read_csv(csv_url)
        return df
    except Exception as e:
        st.error(f"❌ Error al conectar con Google Drive: {e}")
        return None

df_raw = cargar_datos_vía_gviz()

if df_raw is not None and not df_raw.empty:
    df_raw.columns = df_raw.columns.str.strip().str.upper()

    col_provincia = "PROVINCIA"
    col_ciudad = "CIUDAD" if "CIUDAD" in df_raw.columns else ("CANTON" if "CANTON" in df_raw.columns else "CANTÓN")
    col_servicio = "SERVICIO"
    col_dia = "DIA NOMBRE"
    col_estado = "ESTADO DE ASISTENCIA"
    col_hora_agrupada = "HORA AGRUPADA"
    col_fecha = "FECHA CREACIÓN DE ASISTENCIA" if "FECHA CREACIÓN DE ASISTENCIA" in df_raw.columns else "FECHA CREACION DE ASISTENCIA"
    col_cobertura = "TIPO COBERTURA"  # Mapeo de la columna en Google Drive

    df_raw[col_provincia] = df_raw[col_provincia].astype(str).str.strip().str.upper()
    if col_ciudad in df_raw.columns:
        df_raw[col_ciudad] = df_raw[col_ciudad].astype(str).str.strip()

    # Estandarización de la columna de cobertura de manera preventiva
    if col_cobertura in df_raw.columns:
        df_raw[col_cobertura] = df_raw[col_cobertura].astype(str).str.strip().str.upper()
    else:
        df_raw[col_cobertura] = "LOCAL"

    # Panel de Filtros de Operación
    st.write("### 🎛️ Panel de Filtros de Operación")
    f1, f2, f3, f4, f5 = st.columns([2, 2, 2, 3, 2])
    
    with f1:
        dias_en_orden = ["LUNES", "MARTES", "MIÉRCOLES", "MIERCOLES", "JUEVES", "VIERNES", "SÁBADO", "SABADO", "DOMINGO"]
        dias_existentes = df_raw[col_dia].dropna().unique()
        dias_disponibles = [d for d in dias_en_orden if d in list(df_raw[col_dia].str.upper().unique())]
        extras = [d for d in dias_existentes if d.upper() not in dias_en_orden]
        dia_sel = st.selectbox("📅 Seleccionar Día Tipo:", dias_disponibles + extras)
    
    with f2:
        lista_servicios = ["Todos"] + list(df_raw[col_servicio].dropna().unique())
        servicio_sel = st.selectbox("🎯 Seleccionar Servicio:", lista_servicios)

    with f3:
        lista_provincias = ["Todas"] + df_raw[col_provincia].value_counts().index.tolist()
        provincia_sel = st.selectbox("📍 Seleccionar Provincia:", lista_provincias)

    with f4:
        if provincia_sel != "Todas":
            ciudades_disponibles = df_raw[df_raw[col_provincia] == provincia_sel][col_ciudad].dropna().unique().tolist()
            ciudades_disponibles = sorted(ciudades_disponibles)
            
            ciudad_sel = st.multiselect(
                "🏙️ Filtrar Ciudades (Una o Varias):",
                options=ciudades_disponibles,
                default=[],
                placeholder="Todas las ciudades"
            )
        else:
            ciudad_sel = st.multiselect(
                "🏙️ Filtrar Ciudades (Una o Varias):",
                options=[],
                disabled=True,
                placeholder="Filtre por Provincia primero"
            )

    with f5:
        estado_sel = st.selectbox("📌 Filtrar por Estado:", ["Todos"] + list(df_raw[col_estado].dropna().unique())) if col_estado in df_raw.columns else "Todos"

    # Lógica de detección de fecha futura respetando zona horaria local de Ecuador
    dia_actual_num = hora_ecuador_actual.weekday() 
    dia_destino_num = diccionario_dias.get(dia_sel.upper(), dia_actual_num)
    
    dias_diferencia = (dia_destino_num - dia_actual_num) % 7
    fecha_target = hora_ecuador_actual + timedelta(days=dias_diferencia)
    fecha_target_str = fecha_target.strftime("%Y-%m-%d")

    # Filtrado de Data Histórica
    df_dia_especifico = df_raw[df_raw[col_dia].str.upper() == dia_sel.upper()]
    num_fechas_reales = df_dia_especifico[col_fecha].nunique() if col_fecha in df_dia_especifico.columns else 1
    if num_fechas_reales == 0: num_fechas_reales = 1

    df_base_dia_estado = df_dia_especifico.copy()
    if estado_sel != "Todos" and col_estado in df_raw.columns:
        df_base_dia_estado = df_base_dia_estado[df_base_dia_estado[col_estado] == estado_sel]

    df_base_filtros = df_base_dia_estado.copy()
    if servicio_sel != "Todos":
        df_base_filtros = df_base_filtros[df_base_filtros[col_servicio] == servicio_sel]

    df_filtrado = df_base_filtros.copy()
    if provincia_sel != "Todas":
        df_filtrado = df_filtrado[df_filtrado[col_provincia] == provincia_sel]
        if ciudad_sel:
            df_filtrado = df_filtrado[df_filtrado[col_ciudad].isin(ciudad_sel)]

    # Hora actual calculada en base a Ecuador
    hora_actual = hora_ecuador_actual.hour

    # Lógica de Clima condicionada al Filtro de Provincia y Fecha Objetivo
    if provincia_sel != "Todas":
        lat_c, lon_c = coordenadas_provincias.get(provincia_sel, [-0.2298, -78.5249])
        diccionario_clima = obtener_clima_horario_futuro(lat_c, lon_c, fecha_target_str)
        factor_ajuste = calcular_factor_lluvia_en_vivo(df_filtrado, lat_c, lon_c)
    else:
        diccionario_clima = {}
        factor_ajuste = 1.0

    st.markdown("---")

    total_casos_historicos = len(df_filtrado)
    promedio_asistencias_dia = int(round(total_casos_historicos / num_fechas_reales, 0))
    st.metric(label=f"📊 Casos Promedio Esperados (Día {dia_sel})", value=f"{promedio_asistencias_dia} Asistencias")

    st.markdown("---")
    col_tabla_izq, col_tabla_der = st.columns([4, 6])

    with col_tabla_izq:
        if total_casos_historicos > 0:
            if provincia_sel == "Todas":
                st.write("### 📋 Demanda General por Provincias")
                df_tabla_prov = df_base_filtros.groupby(col_provincia).size().reset_index(name='Casos Históricos')
                df_tabla_prov['Promedio Diario Proyectado'] = (df_tabla_prov['Casos Históricos'] / num_fechas_reales).round(0).astype(int)
                
                st.dataframe(
                    df_tabla_prov.sort_values(by='Casos Históricos', ascending=False), 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        col_provincia: st.column_config.TextColumn(alignment="left"),
                        "Casos Históricos": st.column_config.NumberColumn(alignment="center"),
                        "Promedio Diario Proyectado": st.column_config.NumberColumn(alignment="center", format="%d")
                    }
                )
            else:
                if ciudad_sel:
                    st.write(f"### 📋 Demanda: Ciudades Seleccionadas de {provincia_sel}")
                else:
                    st.write(f"### 📋 Demanda: Ciudades de {provincia_sel}")
                    
                if col_ciudad in df_filtrado.columns:
                    df_tabla_ciud = df_filtrado.groupby(col_ciudad).size().reset_index(name='Casos Históricos')
                    df_tabla_ciud['Promedio Diario Proyectado'] = (df_tabla_ciud['Casos Históricos'] / num_fechas_reales).round(0).astype(int)
                    
                    st.dataframe(
                        df_tabla_ciud.sort_values(by='Casos Históricos', ascending=False), 
                        use_container_width=True, 
                        hide_index=True,
                        column_config={
                            col_ciudad: st.column_config.TextColumn(alignment="left"),
                            "Casos Históricos": st.column_config.NumberColumn(alignment="center"),
                            "Promedio Diario Proyectado": st.column_config.NumberColumn(alignment="center", format="%d")
                        }
                    )
        else:
            st.info("Sin registros para estructurar la tabla geográfica.")

    with col_tabla_der:
        if total_casos_historicos > 0:
            if servicio_sel == "Todos":
                st.write("### 📋 Ranking de Servicios con Mayor Demanda")
                df_tabla_serv = df_filtrado.groupby(col_servicio).size().reset_index(name='Casos Históricos')
                df_tabla_serv['Promedio Diario Proyectado'] = (df_tabla_serv['Casos Históricos'] / num_fechas_reales).round(0).astype(int)
                
                st.dataframe(
                    df_tabla_serv.sort_values(by='Casos Históricos', ascending=False), 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        col_servicio: st.column_config.TextColumn(alignment="left"),
                        "Casos Históricos": st.column_config.NumberColumn(alignment="center"),
                        "Promedio Diario Proyectado": st.column_config.NumberColumn(alignment="center", format="%d")
                    }
                )
            else:
                st.write(f"### ⏰ Matriz Horaria Avanzada y Necesidad de Flota para el {dia_sel.title()}")
                if col_hora_agrupada in df_filtrado.columns:
                    # Preparación de la matriz base horaria
                    df_horas_raw = df_filtrado.copy()
                    df_horas_raw[col_hora_agrupada] = pd.to_numeric(df_horas_raw[col_hora_agrupada], errors='coerce').fillna(-1).astype(int)
                    df_horas_raw = df_horas_raw[df_horas_raw[col_hora_agrupada] >= 0]

                    # Vectores para procesar las 24 horas del día tipo por separado
                    casos_locales_por_hora = [0] * 24
                    casos_foraneos_por_hora = [0] * 24

                    # Clasificamos la volumetría histórica real por hora y tipo de cobertura
                    for hr in range(24):
                        df_bloque = df_horas_raw[df_horas_raw[col_hora_agrupada] == hr]
                        if not df_bloque.empty:
                            for _, fila in df_bloque.iterrows():
                                tipo = str(fila[col_cobertura]).upper()
                                if "FOR" in tipo:  # Servicio Foráneo
                                    casos_foraneos_por_hora[hr] += 1
                                else:             # Servicio Local o vacío por defecto
                                    casos_locales_por_hora[hr] += 1

                    # Convertimos los acumulados históricos en promedios diarios reales
                    promedios_locales = [c / num_fechas_reales for c in casos_locales_por_hora]
                    promedios_foraneos = [c / num_fechas_reales for c in casos_foraneos_por_hora]

                    registros_tabla = []
                    alertas_activas = []
                    
                    # Ejecución del Algoritmo Matemático de Arrastre Dinámico (Ecuación Temporal)
                    for hr in range(24):
                        base_local = promedios_locales[hr]
                        base_foraneo = promedios_foraneos[hr]
                        base_total_combinado = int(round(base_local + base_foraneo, 0))
                        
                        if provincia_sel != "Todas":
                            clima_info = diccionario_clima.get(hr, {"Detalle": "⚪ N/A", "Estado": "Normal"})
                            detalle_clima = clima_info["Detalle"]
                            estado_c = clima_info["Estado"]
                            
                            # Ajuste dinámico si el pronóstico detecta lluvia
                            if estado_c == "Lluvia":
                                local_ajustado = base_local * factor_ajuste
                                foraneo_ajustado = base_foraneo * factor_ajuste
                                total_proyectado_int = int(round(local_ajustado + foraneo_ajustado, 0))
                                string_proyeccion = f"🔥 {total_proyectado_int} (Alerta)"
                                if dias_diferencia == 0 and hr > hora_actual and hr <= (hora_actual + 3):
                                    alertas_activas.append(f"🚨 **Alerta Meteorológica [{hr}:00]:** Lluvia entrante en {provincia_sel}. Demanda estimada subirá a {total_proyectado_int} casos.")
                            else:
                                local_ajustado = base_local
                                foraneo_ajustado = base_foraneo
                                string_proyeccion = f"{base_total_combinado} (Normal)"
                        else:
                            detalle_clima = "🌍 Nacional (Filtre Provincia)"
                            local_ajustado = base_local
                            foraneo_ajustado = base_foraneo
                            string_proyeccion = f"{base_total_combinado} (Normal)"

                        # ALGORITMO OPERATIVO DE ARRASTRE DE FLOTA LOGÍSTICA
                        # Grúas_Activas = [Local_Actual + 0.5 * Local_Anterior] + [Foráneo_Actual + Foráneo_Anterior(h-1) + Foráneo_Anterior(h-2)]
                        local_h_ant = local_ajustado if hr == 0 else promedios_locales[hr-1]
                        foraneo_h_ant1 = foraneo_ajustado if hr == 0 else promedios_foraneos[hr-1]
                        foraneo_h_ant2 = foraneo_ajustado if hr <= 1 else promedios_foraneos[hr-2]

                        # Sumatoria de solapamiento de tiempos en calle
                        gruas_netas = (local_ajustado + (0.5 * local_h_ant)) + (foraneo_ajustado + foraneo_h_ant1 + foraneo_h_ant2)
                        gruas_necesarias_enteras = math.ceil(gruas_netas) # Redondeo entero operativo hacia arriba

                        # Filtro Candado: Columna exclusiva para el servicio de grúas/remolques
                        servicio_str_upper = str(servicio_sel).upper()
                        es_servicio_remolque = "REMOLQUE" in servicio_str_upper or "GRÚA" in servicio_str_upper or "GRUA" in servicio_str_upper
                        string_gruas_celda = f"🚛 {gruas_necesarias_enteras} Unidades" if es_servicio_remolque else "-"

                        if base_total_combinado > 0 or es_servicio_remolque:
                            registros_tabla.append({
                                "BLOQUE HORARIO": hr,
                                "🌤️ Clima Online": detalle_clima,
                                "Promedio Base": base_total_combinado,
                                "Proyección Ajustada": string_proyeccion,
                                "Grúas Necesarias (Arrastre)": string_gruas_celda
                            })
                    
                    df_tabla_final = pd.DataFrame(registros_tabla)
                    
                    if provincia_sel != "Todas":
                        if alertas_activas:
                            for alerta in alertas_activas: st.error(alerta)
                        else:
                            if dias_diferencia == 0:
                                st.success(f"✅ Reporte Online: Clima estable para las próximas horas en {provincia_sel}.")
                    else:
                        st.info("ℹ️ Para activar el análisis meteorológico en vivo y las alertas de flota, selecciona una Provincia.")
                    
                    if not df_tabla_final.empty:
                        st.dataframe(
                            df_tabla_final, 
                            use_container_width=True, 
                            hide_index=True,
                            column_config={
                                "BLOQUE HORARIO": st.column_config.NumberColumn(alignment="center", format="%02d:00"),
                                "🌤️ Clima Online": st.column_config.TextColumn(alignment="left"),
                                "Promedio Base": st.column_config.NumberColumn(alignment="center"),
                                "Proyección Ajustada": st.column_config.TextColumn(alignment="center"),
                                "Grúas Necesarias (Arrastre)": st.column_config.TextColumn(alignment="center")
                            }
                        )
                    else:
                        st.info("No se consolidaron registros horarios para el filtro actual.")
                else:
                    st.info("No se localizó la columna de Bloques Horarios en la fuente de datos.")
        else:
            st.info("Sin registros para estructurar el análisis analítico derecho.")

    st.markdown("---")
    
    # ⏱️ Hilo de espera en segundo plano (300 segundos = 5 minutos)
    time.sleep(300)
    st.rerun()
else:
    st.warning("⚠️ Esperando conexión con el archivo de Google Drive...")
