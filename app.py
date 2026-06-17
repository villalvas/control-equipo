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
    page_title="Monitor de Control Logístico y Climatológico v2.0",
    initial_sidebar_state="collapsed"
)

# Estilos CSS corporativos y tamaño de letra en tablas
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDataFrame [data-testid="stDataFrameDownloadButton"] {display: none;}
    button[title="View fullscreen"] {display: none;}
    
    /* Modificación de tamaño de texto en tablas para legibilidad en pantallas grandes */
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

# 🔄 Mecanismo de auto-refresco automatizado (Cada 5 minutos)
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

# Definimos la zona horaria de Ecuador de forma explícita
zona_ecuador = ZoneInfo("America/Guayaquil")
hora_ecuador_actual = datetime.now(zona_ecuador)

st.title("🔮 Sistema de Proyección Horaria, Alerta Temprana y Gestión de Flota")

# Indicador de sincronización en vivo
st.caption(f"Centro de Control Geoanalítico con Monitoreo de Clima Online | 🔄 Auto-refresco activo cada 5 min (Último: {hora_ecuador_actual.strftime('%I:%M:%S %p')})")

# Diccionarios geográficos y de tiempo
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
    col_cobertura = "TIPO COBERTURA"  # Nueva columna leída desde tu base de datos actualizada

    df_raw[col_provincia] = df_raw[col_provincia].astype(str).str.strip().str.upper()
    if col_ciudad in df_raw.columns:
        df_raw[col_ciudad] = df_raw[col_ciudad].astype(str).str.strip()

    # Si la columna cobertura existe, la limpiamos. Si no, la creamos vacía preventivamente
    if col_cobertura in df_raw.columns:
        df_raw[col_cobertura] = df_raw[col_cobertura].astype(str).str.strip().str.upper()
    else:
        df_raw[col_cobertura] = "LOCAL"

    # 🗂️ CREACIÓN DEL SISTEMA DE PESTAÑAS (TABS) SUPERIORES
    tab_monitor, tab_mapa = st.tabs(["📊 Monitor Operativo y Flota", "🗺️ Mapa de Calor Regional"])

    with tab_monitor:
        st.write("### 🎛️ Panel de Filtros de Operación")
        f1, f2, f3, f4, f5 = st.columns([2, 2, 2, 3, 2])
        
        with f1:
            dias_en_orden = ["LUNES", "MARTES", "MIÉRCOLES", "MIERCOLES", "JUEVES", "VIERNES", "SÁBADO", "SABADO", "DOMINGO"]
            dias_existentes = df_raw[col_dia].dropna().unique()
            dias_disponibles = [d for d in dias_en_orden if d in list(df_raw[col_dia].str.upper().unique())]
            extras = [d for d in dias_existentes if d.upper() not in dias_en_orden]
            dia_sel = st.selectbox("📅 Seleccionar Día Tipo:", dias_disponibles + extras, key="dia_mon")
        
        with f2:
            lista_servicios = ["Todos"] + list(df_raw[col_servicio].dropna().unique())
            servicio_sel = st.selectbox("🎯 Seleccionar Servicio:", lista_servicios, key="serv_mon")

        with f3:
            lista_provincias = ["Todas"] + df_raw[col_provincia].value_counts().index.tolist()
            provincia_sel = st.selectbox("📍 Seleccionar Provincia:", lista_provincias, key="prov_mon")

        with f4:
            if provincia_sel != "Todas":
                ciudades_disponibles = df_raw[df_raw[col_provincia] == provincia_sel][col_ciudad].dropna().unique().tolist()
                ciudades_disponibles = sorted(ciudades_disponibles)
                ciudad_sel = st.multiselect("🏙️ Filtrar Ciudades (Una o Varias):", options=ciudades_disponibles, default=[], placeholder="Todas las ciudades", key="ciudad_mon")
            else:
                ciudad_sel = st.multiselect("🏙️ Filtrar Ciudades (Una o Varias):", options=[], disabled=True, placeholder="Filtre por Provincia primero", key="ciudad_mon_dis")

        with f5:
            estado_sel = st.selectbox("📌 Filtrar por Estado:", ["Todos"] + list(df_raw[col_estado].dropna().unique()), key="estado_mon") if col_estado in df_raw.columns else "Todos"

        # Lógica de detección de fecha futura respetando zona horaria local
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

        # Hora actual calculada con base en Ecuador
        hora_actual = hora_ecuador_actual.hour

        # Clima e impactos meteorológicos
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
                    st.dataframe(df_tabla_prov.sort_values(by='Casos Históricos', ascending=False), use_container_width=True, hide_index=True)
                else:
                    st.write(f"### 📋 Demanda: Cantones de {provincia_sel}")
                    if col_ciudad in df_filtrado.columns:
                        df_tabla_ciud = df_filtrado.groupby(col_ciudad).size().reset_index(name='Casos Históricos')
                        df_tabla_ciud['Promedio Diario Proyectado'] = (df_tabla_ciud['Casos Históricos'] / num_fechas_reales).round(0).astype(int)
                        st.dataframe(df_tabla_ciud.sort_values(by='Casos Históricos', ascending=False), use_container_width=True, hide_index=True)
            else:
                st.info("Sin registros para estructurar la tabla geográfica.")

        with col_tabla_der:
            if total_casos_historicos > 0:
                if servicio_sel == "Todos":
                    st.write("### 📋 Ranking de Servicios con Mayor Demanda")
                    df_tabla_serv = df_filtrado.groupby(col_servicio).size().reset_index(name='Casos Históricos')
                    df_tabla_serv['Promedio Diario Proyectado'] = (df_tabla_serv['Casos Históricos'] / num_fechas_reales).round(0).astype(int)
                    st.dataframe(df_tabla_serv.sort_values(by='Casos Históricos', ascending=False), use_container_width=True, hide_index=True)
                else:
                    st.write(f"### ⏰ Matriz Horaria Avanzada y Distribución de Recursos para el {dia_sel.title()}")
                    
                    if col_hora_agrupada in df_filtrado.columns:
                        # Estructuramos la matriz base de 24 horas para que el algoritmo de arrastre analice bloques continuos vacíos o llenos
                        df_horas_raw = df_filtrado.copy()
                        df_horas_raw[col_hora_agrupada] = pd.to_numeric(df_horas_raw[col_hora_agrupada], errors='coerce').fillna(-1).astype(int)
                        df_horas_raw = df_horas_raw[df_horas_raw[col_hora_agrupada] >= 0]

                        # Inicializamos vectores para las 24 horas del día tipo
                        casos_locales_por_hora = [0] * 24
                        casos_foraneos_por_hora = [0] * 24

                        # Clasificamos y cargamos los totales históricos de cobertura por bloque horario
                        for hr in range(24):
                            df_bloque = df_horas_raw[df_horas_raw[col_hora_agrupada] == hr]
                            if not df_bloque.empty:
                                for _, fila in df_bloque.iterrows():
                                    tipo = str(fila[col_cobertura]).upper()
                                    if "FOR" in tipo: # Cobertura Foránea (3 horas)
                                        casos_foraneos_por_hora[hr] += 1
                                    else: # Cobertura Local por defecto (1.5 horas)
                                        casos_locales_por_hora[hr] += 1

                        # Convertimos a promedios por día tipo reales
                        promedios_locales = [c / num_fechas_reales for c in casos_locales_por_hora]
                        promedios_foraneos = [c / num_fechas_reales for c in casos_foraneos_por_hora]

                        registros_tabla = []
                        alertas_activas = []

                        # Ejecución del Algoritmo de Arrastre Dinámico (Ecuación Logística de Disponibilidad Flota)
                        for hr in range(24):
                            base_local = promedios_locales[hr]
                            base_foraneo = promedios_foraneos[hr]
                            base_total_combinado = int(round(base_local + base_foraneo, 0))

                            # Mapeo del clima online
                            if provincia_sel != "Todas":
                                clima_info = diccionario_clima.get(hr, {"Detalle": "⚪ N/A", "Estado": "Normal"})
                                detalle_clima = clima_info["Detalle"]
                                estado_c = clima_info["Estado"]
                            else:
                                detalle_clima = "🌍 Nacional (Filtre Provincia)"
                                estado_c = "Normal"

                            # Aplicación de impacto por Alerta Meteorológica en Vivo si hay lluvia
                            if estado_c == "Lluvia" and provincia_sel != "Todas":
                                local_ajustado = base_local * factor_ajuste
                                foraneo_ajustado = base_foraneo * factor_ajuste
                                total_proyectado_int = int(round(local_ajustado + foraneo_ajustado, 0))
                                string_proyeccion = f"🔥 {total_proyectado_int} (Alerta)"
                                
                                # Activador de alertas tempranas push en el Centro de Control
                                if dias_diferencia == 0 and hr > hora_actual and hr <= (hora_actual + 3):
                                    alertas_activas.append(f"🚨 **Alerta Meteorológica [{hr}:00]:** Lluvia inminente en {provincia_sel}. Demanda estimada subirá a {total_proyectado_int} casos.")
                            else:
                                local_ajustado = base_local
                                foraneo_ajustado = base_foraneo
                                string_proyeccion = f"{base_total_combinado} (Normal)"

                            # ALGORITMO OPERATIVO DE ARRASTRE DE FLOTA LOGÍSTICA (Ecuación Temporal)
                            # Grúas_Activas = [Local_Actual + 0.5 * Local_Anterior] + [Foráneo_Actual + Foráneo_Anterior(h-1) + Foráneo_Anterior(h-2)]
                            local_h_ant = local_ajustado if hr == 0 else promedios_locales[hr-1]
                            foraneo_h_ant1 = local_ajustado if hr == 0 else promedios_foraneos[hr-1]
                            foraneo_h_ant2 = local_ajustado if hr <= 1 else promedios_foraneos[hr-2]

                            # Evaluación matemática del solapamiento logístico
                            gruas_netas = (local_ajustado + (0.5 * local_h_ant)) + (foraneo_ajustado + foraneo_h_ant1 + foraneo_h_ant2)
                            gruas_necesarias_enteras = math.ceil(gruas_netas) # Redondeo entero operativo hacia arriba

                            # Filtro Candado: Activado únicamente si se selecciona el Servicio específico de Grúas
                            es_servicio_remolque = "REMOLQUE" in str(servicio_sel).upper() or "GRÚA" in str(servicio_sel).upper() or "GRUA" in str(servicio_sel).upper()
                            string_gruas_celda = f"🚛 {gruas_necesarias_enteras} Unidades" if es_servicio_remolque else "-"

                            # Agregamos los resultados calculados a la matriz de datos de la interfaz
                            if base_total_combinado > 0 or es_servicio_remolque:
                                registros_tabla.append({
                                    "BLOQUE HORARIO": hr,
                                    "🌤️ Clima Online": detalle_clima,
                                    "Promedio Base": base_total_combinado,
                                    "Proyección Ajustada": string_proyeccion,
                                    "Grúas Necesarias (Arrastre)": string_gruas_celda
                                })

                        df_tabla_final = pd.DataFrame(registros_tabla)

                        # Renderizado de Alertas en pantalla
                        if provincia_sel != "Todas":
                            if alertas_activas:
                                for alerta in alertas_activas: st.error(alerta)
                            else:
                                if dias_diferencia == 0: st.success(f"✅ Reporte Online: Clima estable para las próximas horas en {provincia_sel}.")
                        else:
                            st.info("ℹ️ Selecciona una Provincia específica para activar el análisis meteorológico y cálculo de unidades logísticas.")

                        # Pintar tabla interactiva
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
                            st.info("Sin registros horarios para compilar la matriz.")
            else:
                st.info("Sin registros históricos mapeados con los filtros seleccionados.")

    # 🗺️ PESTAÑA 2: MAPA DE CALOR GEOESTADÍSTICO INTERACTIVO NATIVO EN STREAMLIT
    with tab_mapa:
        st.write("### 🗺️ Distribución de Densidad Operativa en Vivo y Capas de Clima")
        
        # Filtros replicados rápidos para control de visualización del mapa
        m1, m2, m3 = st.columns([4, 4, 4])
        with m1:
            dia_mapa = st.selectbox("📅 Día de Análisis (Mapa):", dias_disponibles + extras, key="dia_map")
        with m2:
            serv_mapa = st.selectbox("🎯 Servicio (Mapa):", lista_servicios, key="serv_map")
        with m3:
            prov_mapa = st.selectbox("📍 Provincia (Mapa):", lista_provincias, key="prov_map")

        # Filtrado específico para coordenadas del mapa
        df_mapa_filtrado = df_raw[df_raw[col_dia].str.upper() == dia_mapa.upper()].copy()
        if serv_mapa != "Todos":
            df_mapa_filtrado = df_mapa_filtrado[df_mapa_filtrado[col_servicio] == serv_mapa]
        if prov_mapa != "Todas":
            df_mapa_filtrado = df_mapa_filtrado[df_mapa_filtrado[col_provincia] == prov_mapa]

        # Inyectar Centroides lat/lon aproximados basados en la Ciudad/Cantón para armar el mapa nativo
        # Esto elimina la dependencia de APIs externas lentas de cobro
        def asignar_coordenadas(row):
            ciudad_text = str(row[col_ciudad]).upper().strip()
            prov_text = str(row[col_provincia]).upper().strip()
            # Mapeo base por capitales de provincia
            if "QUITO" in ciudad_text or "PICHINCHA" in prov_text: return -0.1807, -78.4678
            elif "GUAYAQUIL" in ciudad_text or "GUAYAS" in prov_text: return -2.1709, -79.9224
            elif "CUENCA" in ciudad_text or "AZUAY" in prov_text: return -2.9005, -79.0045
            elif "MANABI" in prov_text or "MANABÍ" in prov_text or "PORTOVIEJO" in ciudad_text or "MANTA" in ciudad_text: return -0.9500, -80.5000
            elif "MACHALA" in ciudad_text or "EL ORO" in prov_text: return -3.2581, -79.9553
            elif "LOJA" in prov_text: return -3.9931, -79.2042
            elif "AMBATO" in ciudad_text or "TUNGURAHUA" in prov_text: return -1.2491, -78.6168
            elif "RIOBAMBA" in ciudad_text or "CHIMBORAZO" in prov_text: return -1.6743, -78.6483
            else:
                return -1.8312, -78.1834 # Centroide geométrico neutro de Ecuador

        if not df_mapa_filtrado.empty and col_ciudad in df_mapa_filtrado.columns:
            # Generación masiva de coordenadas por centroides estandarizados
            coordenadas = df_mapa_filtrado.apply(asignar_coordenadas, axis=1)
            df_mapa_filtrado['latitude'] = [c[0] for c in coordenadas]
            df_mapa_filtrado['longitude'] = [c[1] for c in coordenadas]

            # Seleccionamos las coordenadas centrales para enfocar la cámara del mapa
            if prov_mapa != "Todas":
                lat_enfoque, lon_enfoque = coordenadas_provincias.get(prov_mapa, [-1.8312, -78.1834])
            else:
                lat_enfoque, lon_enfoque = -1.8312, -78.1834

            st.write(f"ℹ️ Visualizando mapa de calor estocástico para el día **{dia_mapa.title()}** en base a **{len(df_mapa_filtrado)} asistencias registradas**.")
            
            # 🗺️ RENDERIZADO DEL MAPA NATIVO CON CAPA DE CALOR INCORPORADA POR DENSIDAD DE CASOS
            st.map(df_mapa_filtrado[['latitude', 'longitude']], size=40, zoom=7 if prov_mapa != "Todas" else 6)

            # Tarjetas informativas de Clima Online acopladas a la vista del mapa
            st.write("#### 🌤️ Condiciones Meteorológicas de Control Satelital (API Abierta)")
            c_m1, c_m2, c_m3 = st.columns(3)
            with c_m1:
                clima_q = obtener_clima_horario_futuro(-0.1807, -78.4678, hora_ecuador_actual.strftime("%Y-%m-%d")).get(hora_actual, {"Detalle": "⚪ N/A"})
                st.metric("Zona Norte (Pichincha / Quito)", clima_q["Detalle"])
            with c_m2:
                clima_g = obtener_clima_horario_futuro(-2.1709, -79.9224, hora_ecuador_actual.strftime("%Y-%m-%d")).get(hora_actual, {"Detalle": "⚪ N/A"})
                st.metric("Zona Costa (Guayas / Guayaquil)", clima_g["Detalle"])
            with c_m3:
                clima_a = obtener_clima_horario_futuro(-2.9005, -79.0045, hora_ecuador_actual.strftime("%Y-%m-%d")).get(hora_actual, {"Detalle": "⚪ N/A"})
                st.metric("Zona Austro (Azuay / Cuenca)", clima_a["Detalle"])
        else:
            st.info("No hay suficientes datos espaciales consolidados para renderizar el mapa con estos filtros.")

    # ⏱️ Hilo de espera en segundo plano para el bucle de refresco continuo de 5 minutos (300 segundos)
    st.markdown("---")
    time.sleep(300)
    st.rerun()

else:
    st.warning("⚠️ Esperando conexión con el archivo consolidado de Google Drive...")
