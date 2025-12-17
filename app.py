import streamlit as st
import requests
import urllib3

# --- CONFIGURACIÓN ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="Verificador Frigorífico", page_icon="🥩")

# --- FUNCIONES DEL MOTOR ---

def consultar_deuda_bancaria(cuit):
    """Consulta la API oficial para Deudas Bancarias (Situación 1-5)"""
    url = f"https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/{cuit}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=5)
        if r.status_code == 200:
            datos = r.json().get('results', [])
            return datos if isinstance(datos, list) else []
    except:
        pass
    return []

def espiar_cheques_web(cuit_raw):
    """
    MODO PARANOICO:
    Busca palabras clave de riesgo (SIN FONDOS) en una web espejo
    para detectar lo que la API oficial oculta.
    """
    s_cuit = str(cuit_raw)
    if len(s_cuit) == 11:
        cuit_fmt = f"{s_cuit[:2]}-{s_cuit[2:-1]}-{s_cuit[-1]}"
    else:
        return {"riesgo": False, "msg": "CUIT inválido"}

    # Usamos CuitOnline como espejo
    url = f"https://www.cuitonline.com/detalle/{cuit_fmt}/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Referer': 'https://www.google.com/'
    }
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        
        # BUSQUEDA DE TEXTO BRUTA (Más segura que buscar tablas)
        texto_entero = r.text.upper()
        palabras_peligrosas = ["SIN FONDOS", "CUENTA CERRADA", "CHEQUE RECHAZADO", "RECHAZOS:"]
        
        encontradas = [p for p in palabras_peligrosas if p in texto_entero]
        
        if encontradas:
            cantidad = texto_entero.count("SIN FONDOS")
            if cantidad == 0: cantidad = len(encontradas)
            
            return {
                "riesgo": True, 
                "cantidad": cantidad,
                "link": url
            }
            
    except Exception as e:
        print(f"Error scraping: {e}")
        
    return {"riesgo": False, "msg": "Limpio"}

# --- INTERFAZ (FRONTEND) ---

st.title("🥩 Detector de Cheques")
st.info("Sistema Híbrido: API BCRA + Escaneo Web")

cuit_input = st.number_input("Ingresá CUIT sin guiones", min_value=0, format="%d")

if st.button("🔍 INVESTIGAR A FONDO", type="primary", use_container_width=True):
    
    if cuit_input < 20000000000:
        st.warning("⚠️ CUIT inválido")
        st.stop()

    with st.spinner('Auditando cliente...'):
        # 1. Ejecutar las dos búsquedas
        deudas = consultar_deuda_bancaria(cuit_input)
        resultado_web = espiar_cheques_web(cuit_input)
        
        # 2. Calcular situación bancaria de forma segura
        hay_deuda_bancos = False
        max_sit = 1
        
        if deudas:
             # ESTA ES LA LÍNEA QUE SE ROMPÍA. AHORA TIENE 'default=1'
             situaciones = [d.get('situacion', 1) for d in deudas if isinstance(d, dict)]
             max_sit = max(situaciones, default=1) 
             
             if max_sit > 1: 
                 hay_deuda_bancos = True

        # --- SEMÁFORO DE RESULTADOS ---
        
        # PRIORIDAD 1 (ROJO): ALERTA WEB (Cheques rechazados detectados)
        if resultado_web["riesgo"]:
            st.error(f"🚨 ALERTA DE RIESGO: Posibles cheques rechazados")
            st.write(f"El escáner detectó la palabra **'SIN FONDOS'** (o similar) {resultado_web['cantidad']} veces en la web externa.")
            st.warning("La API oficial no reporta esto todavía, pero el riesgo es ALTO.")
            st.link_button("Ver reporte externo completo", resultado_web['link'])

        # PRIORIDAD 2 (AMARILLO): DEUDA BANCARIA
        elif hay_deuda_bancos:
            st.warning(f"⚠️ CUIDADO: El cliente tiene deudas bancarias (Situación {max_sit})")
            st.json(deudas)

        # PRIORIDAD 3 (VERDE): LIMPIO
        else:
            st.success("✅ CLIENTE LIMPIO")
            st.write("No se encontraron deudas bancarias ni palabras de riesgo en la web.")
            st.caption("Fuente: API BCRA + Escaneo de Texto en CuitOnline")
