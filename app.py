import streamlit as st
import requests
import urllib3

# Deshabilitamos las advertencias de SSL (común en webs del gobierno)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Verificador BCRA", page_icon="🥩")

st.title("🥩 Semáforo de Crédito")
st.write("Consulta directa a base oficial BCRA")

# Input gigante para dedos grandes en celular
cuit_input = st.number_input("Ingresá CUIT/CUIL (solo números)", min_value=0, format="%d")

def consultar_api(cuit):
    # Endpoints Oficiales
    url_deudas = f"https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/{cuit}"
    url_cheques = f"https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/ChequesRechazados/{cuit}"
    
    try:
        # verify=False es clave porque los certificados del gobierno a veces fallan
        r_deudas = requests.get(url_deudas, verify=False, timeout=5)
        r_cheques = requests.get(url_cheques, verify=False, timeout=5)
        
        return {
            "deudas": r_deudas.json().get('results', []),
            "cheques": r_cheques.json().get('results', []),
            "status": r_deudas.status_code
        }
    except Exception as e:
        return {"error": str(e)}

if st.button("🔍 ANALIZAR CLIENTE", type="primary", use_container_width=True):
    if cuit_input > 20000000000: # Validación básica de longitud
        with st.spinner('Consultando BCRA...'):
            data = consultar_api(cuit_input)
            
            if "error" in data:
                st.error(f"Error de conexión: {data['error']}")
            elif not data['deudas'] and not data['cheques']:
                st.warning("No se encontraron datos. ¿El CUIT es correcto?")
            else:
                # Lógica del Semáforo
                cant_cheques = len(data['cheques'])
                peor_situacion = 1
                
                if data['deudas']:
                    situaciones = [d.get('situacion', 1) for d in data['deudas']]
                    peor_situacion = max(situaciones)

                # VISUALIZACIÓN
                if cant_cheques > 0:
                    st.error(f"⛔ PELIGRO: {cant_cheques} CHEQUES RECHAZADOS")
                    for c in data['cheques']:
                        st.write(f"📅 {c.get('fechaRechazo')} - 💰 ${c.get('monto')}")
                
                elif peor_situacion > 1:
                    st.warning(f"⚠️ CUIDADO: Situación {peor_situacion} en Central de Deudores")
                    st.json(data['deudas']) # Muestra detalle si hay deuda
                
                else:
                    st.success("✅ CLIENTE LIMPIO (Sin cheques rechazados y Situación 1)")
                    st.balloons()
    else:
        st.info("Por favor ingresa un CUIT válido.")
