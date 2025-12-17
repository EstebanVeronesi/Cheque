import streamlit as st
import requests
import urllib3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

# --- CONFIGURACIÓN ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="Scanner Frigorífico", page_icon="🥩")

# --- MOTOR 1: API OFICIAL (Bancos) ---
def consultar_deuda_bancaria(cuit):
    url = f"https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/{cuit}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0'}
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=5)
        if r.status_code == 200:
            return r.json().get('results', [])
    except:
        pass
    return []

# --- MOTOR 2: BÚSQUEDA WEB (DuckDuckGo via Selenium) ---
def buscar_rastro_web(cuit_raw):
    s_cuit = str(cuit_raw)
    
    # Buscamos en la versión HTML de DuckDuckGo (más ligera y sin tanto bloqueo)
    # Query: CUIT + palabras clave
    query = f'"{s_cuit}" (cheque rechazado OR sin fondos OR deudor OR central deudores)'
    url_busqueda = f"https://html.duckduckgo.com/html/?q={query}"
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    reporte = {"riesgo": False, "hallazgos": [], "link": url_busqueda}
    
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(url_busqueda)
        time.sleep(2) # Esperar carga
        
        # Analizamos los resultados de búsqueda (Snippets)
        resultados = driver.find_elements(By.CLASS_NAME, "result__body")
        
        palabras_gatillo = ["SIN FONDOS", "RECHAZADO", "IMPAGA", "DEUDA", "SITUACION 4", "SITUACION 5"]
        
        for res in resultados:
            texto = res.text.upper()
            # Si el snippet contiene el CUIT y alguna palabra peligrosa
            if s_cuit in texto:
                for p in palabras_gatillo:
                    if p in texto:
                        # Encontramos un resultado sospechoso
                        reporte["riesgo"] = True
                        # Guardamos un fragmento del texto encontrado (limpiando un poco)
                        fragmento = texto.replace("\n", " ")[:150] + "..."
                        if fragmento not in reporte["hallazgos"]:
                            reporte["hallazgos"].append(fragmento)
                        break
    except Exception as e:
        print(f"Error DuckDuckGo: {e}")
    finally:
        try:
            driver.quit()
        except:
            pass
            
    return reporte

# --- FRONTEND ---
st.title("🥩 Semáforo de Crédito")
st.info("Consulta API Bancaria + Rastreo en la Web")

cuit_input = st.number_input("Ingresá CUIT (Solo números)", min_value=0, format="%d")

# Columnas para los botones
col1, col2 = st.columns([1, 1])

with col1:
    btn_scan = st.button("🕵️‍♂️ ESCANEAR AUTOMÁTICO", type="primary", use_container_width=True)

with col2:
    # Link directo a la consulta por CUIT del BCRA (La que tiene Captcha pero es infalible)
    url_bcra_directa = "https://www.bcra.gob.ar/BCRAyVos/Situacion_Crediticia.asp"
    st.link_button("🏛️ ABRIR BCRA OFICIAL", url_bcra_directa, use_container_width=True)

if btn_scan:
    if cuit_input < 20000000000:
        st.error("CUIT Inválido")
        st.stop()
        
    with st.spinner('Analizando historial bancario y buscando referencias web...'):
        
        # 1. API Bancos
        deudas = consultar_deuda_bancaria(cuit_input)
        
        # 2. Búsqueda Web
        web_check = buscar_rastro_web(cuit_input)
        
        # --- LÓGICA DE SEMÁFORO ---
        hay_riesgo = False
        
        # CASO 1: RASTRO EN LA WEB (Prioridad Alta)
        if web_check["riesgo"]:
            hay_riesgo = True
            st.error("🚨 ALERTA: SE ENCONTRARON REFERENCIAS NEGATIVAS EN LA WEB")
            st.write("El buscador encontró menciones de este CUIT asociadas a deudas o rechazos:")
            for hallazgo in web_check["hallazgos"]:
                st.warning(f"🔎 ...{hallazgo}")
            st.markdown(f"[Ver resultados de búsqueda completos]({web_check['link']})")
            
        # CASO 2: DEUDA BANCARIA (API Oficial)
        if deudas:
            situaciones = [d.get('situacion', 1) for d in deudas if isinstance(d, dict)]
            max_sit = max(situaciones, default=1)
            
            if max_sit > 1:
                hay_riesgo = True
                st.warning(f"⚠️ CUIDADO: Situación Bancaria {max_sit} (BCRA)")
                st.json(deudas)
            elif not hay_riesgo:
                st.success("✅ Situación Bancaria 1 (Normal)")
                st.info("Tiene cuentas bancarias al día.")

        # CASO 3: LIMPIO (Aparentemente)
        if not hay_riesgo and not deudas:
            st.success("✅ SIN RASTROS DETECTADOS")
            st.write("No aparecen deudas bancarias en la API ni menciones de 'Sin Fondos' en los primeros resultados de búsqueda.")
            st.info("💡 Consejo: Si la operación es muy grande, usá el botón 'ABRIR BCRA OFICIAL' para confirmar manualmente los últimos 5 días.")

