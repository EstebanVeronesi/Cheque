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
    """Scrapea web alternativa para encontrar cheques RECIENTES (que la API oficial esconde)"""
    s_cuit = str(cuit_raw)
    # Formateamos a XX-XXXXXXXX-X
    if len(s_cuit) == 11:
        cuit_fmt = f"{s_cuit[:2]}-{s_cuit[2:-1]}-{s_cuit[-1]}"
    else:
        return [] # CUIT mal formado

    url = f"https://www.cuitonline.com/detalle/{cuit_fmt}/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Referer': 'https://www.google.com/'
    }
    
    lista_cheques = []
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            # Buscamos todas las tablas
            tablas = soup.find_all('table')
            for tabla in tablas:
                # Si la tabla habla de fondos o rechazos
                texto_tabla = tabla.text.upper()
                if "FONDOS" in texto_tabla or "RECHAZO" in texto_tabla:
                    filas = tabla.find_all('tr')
                    for fila in filas[1:]: # Saltamos encabezado
                        cols = fila.find_all('td')
                        if len(cols) >= 4:
                            # Extraemos datos sucios
                            fecha = cols[1].text.strip()
                            monto = cols[2].text.strip()
                            causa = cols[3].text.strip()
                            
                            if "FONDOS" in causa.upper() or "CUENTA" in causa.upper():
                                lista_cheques.append({
                                    'fecha': fecha,
                                    'monto': monto,
                                    'causa': causa
                                })
    except Exception as e:
        print(f"Error scraping: {e}")
        
    return lista_cheques

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

    # 2. Ejecución del análisis
    with st.spinner('Cruzando bases de datos (Bancos + Cheques)...'):
        
        # Llamamos a las funciones
        deudas = consultar_deuda_bancaria(cuit_input)
        cheques = espiar_cheques_web(cuit_input)
        
        # --- LÓGICA DEL SEMÁFORO ---
        
        # CASO ROJO: Cheques rechazados (Prioridad máxima)
        if len(cheques) > 0:
            st.error(f"🛑 ¡ALERTA MÁXIMA! {len(cheques)} CHEQUES RECHAZADOS")
            st.write("Datos encontrados en web alternativa:")
            for c in cheques:
                st.warning(f"💸 {c['monto']} - {c['causa']} ({c['fecha']})")
        
        # CASO AMARILLO: Deuda Bancaria
        elif len(deudas) > 0:
            # Buscamos la peor situación
            situaciones = []
            for d in deudas:
                if isinstance(d, dict):
                    situaciones.append(d.get('situacion', 1))
            
            max_sit = max(situaciones) if situaciones else 1
            
            if max_sit > 1:
                st.warning(f"⚠️ OJO: Situación {max_sit} en Bancos (BCRA)")
                st.json(deudas)
            else:
                # Situación 1 es normal, pero avisamos
                st.success("✅ Situación Bancaria Normal (1)")
                st.info("El cliente opera con bancos y está al día.")

        # CASO VERDE: Nada de nada
        else:
            st.success("✅ CLIENTE LIMPIO")
            st.write("No se encontraron deudas ni cheques en las fuentes consultadas.")
            st.balloons()

