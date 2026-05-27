import streamlit as st
import pandas as pd

st.set_page_config(page_title="Control Operativo - Mafer", layout="wide")

st.title("📊 Panel de Control Operativo Real (Data en Vivo de Drive)")
st.subheader("Herramienta de soporte basada en la gestión de boletines de Mayo 2026")
st.markdown("---")

# =========================================================================
# CONEXIÓN EN VIVO A GOOGLE DRIVE
# =========================================================================
# ⚠️ PEGA AQUÍ TU LINK REAL DE GOOGLE SHEETS EN MEDIO DE LAS COMILLAS:
URL_DRIVE = "https://docs.google.com/spreadsheets/d/1aGFtjIeJQ0ZyNCoTvJzfHtM3gQ6JdWKgiVHP5i-Pjj8/edit?usp=sharing"

def cargar_datos_drive(url):
    try:
        csv_url = url.replace('/edit?usp=sharing', '/gviz/tq?tqx=out:csv').replace('/edit', '/gviz/tq?tqx=out:csv')
        return pd.read_csv(csv_url)
    except Exception as e:
        st.error(f"Error al conectar con Google Drive. Detalle: {e}")
        return None

df_mafer_vivo = cargar_datos_drive(URL_DRIVE)

if df_mafer_vivo is not None:
    # Limpiamos los nombres de las columnas por si tienen espacios ocultos
    df_mafer_vivo.columns = df_mafer_vivo.columns.str.strip()
    
    st.write("### ✅ ¡Conexión Exitosa con Drive!")
    st.write("Estas son las columnas que encontramos en tu archivo actual:", list(df_mafer_vivo.columns))
    st.markdown("---")
    
    # Mostramos toda la tabla directo para que el líder la edite y busque libremente
    st.write("### 🔍 Buscador y Vista General de la Base de Datos")
    st.data_editor(df_mafer_vivo, use_container_width=True)

else:
    st.warning("Por favor ingresa un enlace válido de Google Sheets en el archivo de código.")
