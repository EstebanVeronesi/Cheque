import streamlit as st
import requests
import urllib3

# --- CONFIGURACIÓN ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="Verificador Frigorífico", page_icon="🥩")

# --- MOTOR DE BÚSQUEDA ---

def consultar_api_oficial(cuit):
    """
    Consulta los DOS endpoints oficiales del BCRA:
    1. Deudas (Situación bancaria)
    2. Cheques Rechazados (La que mencionaste)
    """
    base_url = "https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'}
    
    resultados = {
        "deudas": [],
        "cheques_api": []
    }

    try:
        # 1. Consultar Situación
        r_deudas = requests.get(f"{base_url}/{cuit}", headers=headers, verify=False, timeout=5)
        if r_deudas.status_code == 200:
            data = r_deudas.json().get('results', [])
            resultados["deudas"] = data if isinstance(data, list) else []

        # 2. Consultar Cheques (Tu hallazgo)
        r_cheques = requests.get(f"{base_url}/ChequesRechazados/{cuit}", headers=headers, verify=False, timeout=5)
        if r_cheques.status_code == 200:
            data_cheques = r_cheques.json().get('results', [])
            resultados["cheques_api"] = data_cheques if isinstance(data_cheques, list) else []
            
    except Exception as e:
        print(f"Error API: {e}")
    
    return resultados

def espiar_web_alternativa(cuit_raw):
    """
    MODO RESPALDO: Busca en web externa por si la API Oficial tiene demora en la carga.
    """
    s_cuit = str(cuit_raw)
    if len(s_cuit) != 11: return {"riesgo": False}

    cuit_fmt = f"{s_cuit[:2]}-{s_cuit[2:-1]}-{s_cuit[-1]}"
    url = f"https://www.cuitonline.com/detalle/{cuit_fmt}/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/115.0.0.0 Safari/537.36', 'Referer': 'https://google.com'}
    
    try:
        r = requests.get(url, headers=headers, timeout=8)
        texto = r.text.upper()
        palabras = ["SIN FONDOS", "CHEQUE RECHAZADO", "CUENTA CERRADA"]
        encontradas = [p for p in palabras if p in texto]
        
        if encontradas:
            return {"riesgo": True, "fuente": url, "detalle": encontradas[0]}
            
    except:
        pass
    
    return {"riesgo": False}

# --- FRONTEND ---

st.title("🥩 Semáforo de Crédito")
st.caption("Consulta: API Deudas + API Cheques + Web Externa")

cuit_input = st.number_input("Ingresá CUIT sin guiones", min_value=0, format="%d")

if st.button("🔍 ANALIZAR AHORA", type="primary", use_container_width=True):
    
    if cuit_input < 20000000000:
        st.warning("CUIT Inválido")
        st.stop()

    with st.spinner('Consultando BCRA Oficial y Bases Alternativas...'):
        
        # 1. Llamamos a TODO
        datos_oficiales = consultar_api_oficial(cuit_input)
        datos_web = espiar_web_alternativa(cuit_input)
        
        cheques_api = datos_oficiales["cheques_api"]
        deudas_api = datos_oficiales["deudas"]
        
        # Cálculo de situación máxima
        max_sit = 1
        if deudas_api:
            sits = [d.get('situacion', 1) for d in deudas_api if isinstance(d, dict)]
            max_sit = max(sits, default=1)

        # --- LÓGICA DE PRIORIDADES ---

        # CASO 1: La API Oficial confirma cheques (La fuente más fidedigna)
        if len(cheques_api) > 0:
            st.error(f"🛑 RECHAZADO: API OFICIAL DETECTÓ {len(cheques_api)} CHEQUES")
            for c in cheques_api:
                monto = c.get('monto', '?')
                fecha = c.get('fechaRechazo', '?')
                causa = c.get('causal', 'Sin Fondos')
                st.warning(f"💸 ${monto} - {fecha} ({causa})")

        # CASO 2: La API calla, pero la Web grita (El caso de tu CUIT problemático)
        elif datos_web["riesgo"]:
            st.error("🛑 RIESGO ALTO (DETECTADO POR WEB)")
            st.write("La API oficial no muestra cheques aún, pero el escáner web encontró palabras clave:")
            st.warning(f"⚠️ Se detectó mención de '{datos_web['detalle']}'")
            st.markdown(f"[Ver reporte externo]({datos_web['fuente']})")

        # CASO 3: Deuda Bancaria sin cheques
        elif max_sit > 1:
            st.warning(f"⚠️ PRECAUCIÓN: Situación {max_sit} en Bancos")
            st.json(deudas_api)

        # CASO 4: Limpio total
        else:
            st.success("✅ APROBADO / LIMPIO")
            st.write("No se encontraron cheques en API ni en Web, y la situación bancaria es 1.")
            st.balloons()
