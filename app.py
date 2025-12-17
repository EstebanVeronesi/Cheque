import streamlit as st
import requests
import urllib3
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="Verificador Frigorífico", page_icon="🥩")

# --- FUNCIONES (MOTOR) ---

def consultar_deuda_bancaria(cuit):
    """Consulta la API oficial del BCRA para ver situación 1-5"""
    url = f"https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/{cuit}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=5)
        if r.status_code == 200:
            return r.json().get('results', [])
    except:
        pass
    return []

def espiar_cheques_web(cuit_raw):
    """
    Versión PARANOICA: Busca en múltiples fuentes y usa búsqueda de texto bruta
    para no fallar si cambia el diseño de la tabla.
    """
    s_cuit = str(cuit_raw)
    if len(s_cuit) == 11:
        cuit_fmt = f"{s_cuit[:2]}-{s_cuit[2:-1]}-{s_cuit[-1]}"
    else:
        return {"riesgo": False, "msg": "CUIT inválido"}

    # Fuente 1: CuitOnline (Suele ser la mejor, pero a veces falla)
    url = f"https://www.cuitonline.com/detalle/{cuit_fmt}/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Referer': 'https://www.google.com/'
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        
        # --- LÓGICA DE FUERZA BRUTA ---
        texto_entero = r.text.upper()
        
        # Palabras gatillo que indican problemas
        palabras_peligrosas = ["SIN FONDOS", "CUENTA CERRADA", "CHEQUE RECHAZADO", "RECHAZOS:"]
        
        encontradas = [p for p in palabras_peligrosas if p in texto_entero]
        
        if encontradas:
            # Si encontramos palabras peligrosas, intentamos ver cuántas veces aparecen
            cantidad = texto_entero.count("SIN FONDOS")
            if cantidad == 0: cantidad = len(encontradas) # Por si fue otra palabra
            
            return {
                "riesgo": True, 
                "fuente": "CuitOnline", 
                "cantidad_estimada": cantidad,
                "link": url
            }
            
    except Exception as e:
        print(f"Error scraping: {e}")
        
    return {"riesgo": False, "msg": "No se detectaron palabras clave"}
    
# --- INTERFAZ DE USUARIO (FRONTEND) ---

st.title("🥩 Detector de Cheques")
st.write("Consulta combinada: API Oficial + Web Scraping")

cuit_input = st.number_input("Ingresá CUIT sin guiones", min_value=0, format="%d")

# BOTÓN DE ACCIÓN
if st.button("🔍 INVESTIGAR A FONDO", type="primary", use_container_width=True):
    
    # 1. Validación temprana (Evita errores de indentación)
    if cuit_input < 20000000000:
        st.warning("⚠️ El CUIT parece incompleto o inválido.")
        st.stop() # Detiene la ejecución aquí. No necesitamos 'else'.

    with st.spinner('Auditando cliente...'):
        deudas = consultar_deuda_bancaria(cuit_input)
        
        # Usamos la nueva función paranoica
        resultado_web = espiar_cheques_web(cuit_input)
        
        hay_deuda_bancos = False
        if deudas:
             # Chequeamos si hay situación > 1
             sits = [d.get('situacion', 1) for d in deudas if isinstance(d, dict)]
             if max(sits) > 1: hay_deuda_bancos = True

        # --- SEMÁFORO PRIORITARIO ---
        
        # 1. ROJO: La web detectó palabras clave de cheques (Aunque la API diga que no)
        if resultado_web["riesgo"]:
            st.error(f"🚨 ALERTA DE RIESGO: Posibles cheques rechazados")
            st.write(f"El sistema detectó menciones de **'SIN FONDOS'** o similares {resultado_web['cantidad_estimada']} veces en la web externa.")
            st.warning("La API oficial no los muestra, pero la web sí. Se recomienda revisar manualmente.")
            st.link_button("Ver reporte completo en Web Externa", resultado_web['link'])

        # 2. AMARILLO: Deuda Bancaria
        elif hay_deuda_bancos:
            st.warning("⚠️ El cliente tiene deudas bancarias (Situación > 1)")
            st.json(deudas)

        # 3. VERDE: Limpio
        else:
            st.success("✅ Aparentemente Limpio")
            st.write("No se encontraron deudas bancarias ni palabras clave de rechazo en la web.")
            st.caption("Recuerda: Ningún sistema es infalible. Ante la duda, pedir referencias.")

