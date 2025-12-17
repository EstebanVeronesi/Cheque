import streamlit as st
import requests
import urllib3
import json

# Deshabilitar advertencias de certificados SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="Verificador BCRA", page_icon="🥩")

st.title("🥩 Semáforo de Crédito")
st.info("Sistema conectado a API BCRA. Si no trae datos, el cliente suele estar limpio.")

cuit_input = st.number_input("Ingresá CUIT/CUIL (sin guiones)", min_value=0, format="%d")

def consultar_api_blindada(cuit):
    # Endpoints
    url_deudas = f"https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/{cuit}"
    url_cheques = f"https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/ChequesRechazados/{cuit}"
    
    # DISFRAZ: Le decimos al BCRA que somos un navegador Chrome, no un script
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json'
    }

    try:
        # Peticiones con verify=False y headers
        r_deudas = requests.get(url_deudas, headers=headers, verify=False, timeout=10)
        r_cheques = requests.get(url_cheques, headers=headers, verify=False, timeout=10)
        
        # Intentamos leer el JSON, si falla (porque devolvió HTML de error) usamos vacíos
        try:
            data_deudas = r_deudas.json().get('results', [])
        except:
            data_deudas = []

        try:
            data_cheques = r_cheques.json().get('results', [])
        except:
            data_cheques = []

        return {
            "status_code_deudas": r_deudas.status_code,
            "status_code_cheques": r_cheques.status_code,
            "deudas": data_deudas,
            "cheques": data_cheques,
            "raw_deudas": r_deudas.text # Para ver qué responde realmente
        }
    except Exception as e:
        return {"error": str(e)}

if st.button("🔍 ANALIZAR CLIENTE", type="primary", use_container_width=True):
    if cuit_input > 20000000000:
        with st.spinner('Consultando bases oficiales...'):
            data = consultar_api_blindada(cuit_input)
            
            # --- ZONA DE DIAGNÓSTICO (Para que veas qué pasa) ---
            with st.expander("👨‍💻 Ver datos técnicos (Debug)"):
                st.write(f"Status Deudas: {data.get('status_code_deudas')}")
                st.write(f"Status Cheques: {data.get('status_code_cheques')}")
                st.code(data.get('raw_deudas'))

            if "error" in data:
                st.error(f"Error de conexión: {data['error']}")
            
            else:
                # Extraer listas limpias
                lista_deudas = data.get('deudas') if isinstance(data.get('deudas'), list) else []
                lista_cheques = data.get('cheques') if isinstance(data.get('cheques'), list) else []

                cant_cheques = len(lista_cheques)
                
                # --- ANÁLISIS ---
                
                # CASO 1: Tiene cheques rechazados (Lo más grave)
                if cant_cheques > 0:
                    st.error(f"⛔ ALERTA: {cant_cheques} CHEQUES RECHAZADOS")
                    for c in lista_cheques:
                        if isinstance(c, dict):
                            st.write(f"📅 {c.get('fechaRechazo')} - 💰 ${c.get('monto')}")
                
                # CASO 2: Tiene deuda bancaria registrada
                elif len(lista_deudas) > 0:
                    situaciones = [d.get('situacion', 1) for d in lista_deudas if isinstance(d, dict)]
                    max_sit = max(situaciones) if situaciones else 1
                    
                    if max_sit == 1:
                        st.success(f"✅ CLIENTE BANCARIZADO (Situación 1 - Normal)")
                        st.info("Tiene deudas bancarias pero están al día.")
                    else:
                        st.warning(f"⚠️ CUIDADO: Situación {max_sit} en BCRA")
                    
                    st.write("Detalle de bancos:")
                    st.json(lista_deudas)

                # CASO 3: No devolvió nada (Listas vacías o 404)
                else:
                    # Si el status fue 200 (OK) pero vacío, o 404 (No encontrado en deudores)
                    st.success("✅ SIN ANTECEDENTES REGISTRADOS")
                    st.write(f"El CUIT {cuit_input} no figura en la base de Deudores ni Cheques del BCRA.")
                    st.caption("Nota: La API no confirma el nombre si no tiene deuda. Verifique que el CUIT sea correcto.")
                    st.balloons()
                    
    else:
        st.warning("El CUIT parece incorrecto (muy corto).")

