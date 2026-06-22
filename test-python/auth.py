"""
Autenticación de la aplicación.
"""

import streamlit as st
from ui_components import render_login_form


def check_authentication():
    """
    Verifica si el usuario está autenticado.
    
    Si no está autenticado, muestra el formulario de login y detiene la ejecución.
    """
    if "auth" not in st.session_state:
        login()
        st.stop()


def login():
    """
    Renderiza el formulario de login y maneja la autenticación.
    """
    username, password, col1, col2 = render_login_form()

    if col1.button("Entrar", use_container_width=True):
        if username == st.secrets.get("APP_USER") and password == st.secrets.get("APP_PASSWORD"):
            st.session_state["auth"] = True
            st.rerun()
        else:
            st.error("Usuario o contrasena incorrectos")

    if col2.button("Limpiar", use_container_width=True):
        st.rerun()
