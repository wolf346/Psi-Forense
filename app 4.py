# -----------------------------------------------------------------------------
# OCULTAR MENÚ, FOOTER, CABECERA Y BARRA FLOTANTE DE STREAMLIT CLOUD
# -----------------------------------------------------------------------------
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stDecoration"] {display: none;}
    
    /* Ocultar contenedor flotante inferior derecho (Manage app / Viewer Badge) */
    div.stAppToolbar, 
    div[data-testid="stToolbar"],
    .viewerBadge_container__1QSob,
    div[class*="viewerBadge"],
    #manage-app-button,
    button[kind="manageApp"],
    .stAppDeployButton {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
    
    /* Selector genérico por posición fija inferior derecha para asegurar su desaparición */
    body > div:last-child > div:last-child > iframe {
        display: none !important;
    }
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
