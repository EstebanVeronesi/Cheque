import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

st.set_page_config(page_title="Scanner Frigorífico", page_icon="🥩")

def espiar_con_selenium(cuit_raw):
    # Formateo de CUIT
    s_cuit = str(cuit_raw)
    cuit_fmt = f"{s_cuit[:2]}-{s_cuit[2:-1]}-{s_cuit[-1]}"
    
    # URL del objetivo (Usamos CuitOnline porque BCRA tiene Captcha que bloquea a Selenium)
    url = f"https://www.cuitonline.com/detalle/{cuit_fmt}/"
    
    # --- CONFIGURACIÓN DE CHROME HEADLESS (Para Nube) ---
    options = Options()
    options.add_argument("--headless")  # No abrir ventana gráfica
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    status = "Limpio"
    evidencia = []
    
    try:
        # Iniciamos el navegador
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        
        # Esperamos a que cargue (JavaScript, Tablas, Publicidad)
        time.sleep(3) 
        
        # Leemos TODO el texto visible de la página
        body = driver.find_element(By.TAG_NAME, "body").text.upper()
        
        # Palabras clave de terror para un vendedor
        palabras_clave = [
            "SIN FONDOS", 
            "CHEQUE RECHAZADO", 
            "CUENTA CERRADA", 
            "INHABILITADO",
            "DEUDA IRRECUPERABLE",
            "SITUACIÓN 4",
            "SITUACIÓN 5"
        ]
        
        # Buscamos coincidencias
        for palabra in palabras_clave:
            if palabra in body:
                evidencia.append(palabra)
        
        # Si encontramos algo, capturamos el contexto
        if evidencia:
            status = "PELIGRO"
            
    except Exception as e:
        return {"status": "ERROR", "msg": str(e)}
    
    finally:
        # Importante: Cerrar el navegador para no saturar la memoria
        try:
            driver.quit()
        except:
            pass
            
    return {"status": status, "evidencia": evidencia, "link": url}

# --- FRONTEND ---
st.title("🥩 Scanner Profundo (Selenium)")
st.caption("Este método usa un navegador real. Es más lento pero más preciso.")

cuit_input = st.number_input("CUIT del Cliente", min_value=0, format="%d")

if st.button("🕵️‍♂️ ESCANEAR AHORA", type="primary"):
    if cuit_input < 20000000000:
        st.error("CUIT muy corto.")
        st.stop()
        
    with st.spinner('Iniciando navegador virtual y analizando... (Paciencia, tarda unos segundos)'):
        resultado = espiar_con_selenium(cuit_input)
        
        if resultado["status"] == "PELIGRO":
            st.error("🚨 ALERTA: SE DETECTARON PROBLEMAS")
            st.write("El navegador encontró las siguientes palabras clave en la ficha del cliente:")
            
            # Mostramos las palabras encontradas en rojo
            for e in resultado["evidencia"]:
                st.markdown(f"- 🔴 **{e}**")
            
            st.warning("Recomendación: NO aceptar cheques sin revisar manualmente.")
            st.link_button("Ver Ficha Original", resultado["link"])
            
        elif resultado["status"] == "ERROR":
            st.error("Error al intentar abrir el navegador.")
            st.code(resultado["msg"])
            
        else:
            st.success("✅ NO SE ENCONTRARON PALABRAS DE RIESGO")
            st.write("El escaneo de texto completo no arrojó resultados como 'Sin Fondos' o 'Rechazado'.")
            st.info("De todos modos, verifica referencias.")
