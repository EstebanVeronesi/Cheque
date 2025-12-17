import streamlit as st
import requests
import urllib3
from bs4 import BeautifulSoup

# Deshabilitar advertencias SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Verificador Frigorífico", page_icon="🥩")
st.title("🥩 Detector de Cheques")

# --- FUNCIÓN 1: API OFICIAL (Solo para Deudas Bancarias) ---
def consultar_deuda_bancaria(cuit):
    url = f"https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/{cuit}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=5)
        if r.status_code == 200:
            return r.json().get('results', [])
    except:
        pass
    return []

# --- FUNCIÓN 2: SCRAPING WEB (Para Cheques - La verdad de la milanesa) ---
def espiar_cheques_web(cuit_raw):
    # Formatear CUIT para la URL (ej: 30-71807930-2)
    s_cuit = str(cuit_raw)
    cuit_fmt = f"{s_cuit[:2]}-{s_cuit[2:-1]}-{s_cuit[-1]}"
    
    # Usamos un mirror confiable porque BCRA oficial tiene Captcha
    url = f"https://www.cuitonline.com/detalle/{cuit_fmt}/"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Referer': 'https://www.google.com/'
    }
    
    lista_cheques = []
    try:
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Buscamos si hay texto de cheques rechazados
            # La estructura de estas webs suele tener tablas
            tablas = soup.find_all('table')
            
            for tabla in tablas:
                if "FONDOS" in tabla.text or "Rechazo" in tabla.text:
                    filas = tabla.find_all('tr')
                    for fila in filas[1:]: # Saltamos el encabezado
                        cols = fila.find_all('td')
                        if len(cols) > 3:
                            # Intentamos extraer datos clave
                            monto = cols[2].text.strip() if len(cols) > 2 else "?"
                            causa = cols[3].text.strip() if len(cols) > 3 else "?"
                            fecha = cols[1].text.strip() if len(cols) > 1 else "?"
                            
                            # Filtramos solo si dice SIN FONDOS o similar
                            if "FONDOS" in causa.upper() or "CUENTA" in causa.upper():
                                lista_cheques.append({
                                    'fecha': fecha,
                                    'monto': monto,
                                    'causa': causa
                                })
    except Exception as e:
        print(f"Error scraping: {e}")
        
    return lista_cheques

# --- INTERFAZ ---
cuit_input = st.number_input("Ingresá CUIT sin guiones", min_value=0, format="%d")

if st.button("🔍 INVESTIGAR A FONDO", type="primary"):
    if cuit_input > 20000000000:
        
        with st.spinner('Cruzando bases de datos...'):
            # 1. Buscamos Deuda en API
            deudas = consultar_deuda_bancaria(cuit_input)
            
            # 2. Buscamos Cheques "por izquierda" (Scraping)
            cheques = espiar_cheques_web(cuit_input)
            
            # --- SEMÁFORO DE RESULTADOS ---
            
            # PRIORIDAD 1: CHEQUES (Lo más grave)
            if len(cheques) > 0:
                st.error(f"🛑 ¡ALERTA MÁXIMA! {len(cheques)} CHEQUES RECHAZADOS ENCONTRADOS")
                st.write("La API oficial los ocultaba, pero el escáner web los detectó:")
                
                for c in cheques:
                    st.warning(f"💸 {c['monto']} - {c['causa']} ({c['fecha']})")
                    
            # PRIORIDAD 2: DEUDA BANCARIA
            elif deudas:
                situaciones = [d.get('situacion', 1) for d in deudas if isinstance(d, dict)]
                max_sit = max(situaciones) if situaciones else 1
                
                if max_sit > 1:
                    st.warning(f"⚠️ OJO: Situación {max_sit} en Bancos")
                    st.json(deudas)
                else:
                    st.success("✅ Situación Bancaria Normal (1)")
                    st.info("Sin cheques rechazados detectados en web alternativa.")
            
            # PRIORIDAD 3: LIMPIO
            else:
                st.success("✅ CLIENTE LIMPIO")
                st.write("No se encontraron deudas bancarias ni cheques rechazados en las fuentes consultadas.")
                st.caption("Fuente: API BCRA + CuitOnline Mirror")

    else:
        st.warning("CUIT inválido")
                    
    else:
        st.warning("El CUIT parece incorrecto (muy corto).")


