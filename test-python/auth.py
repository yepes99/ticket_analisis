"""
Autenticacion de la aplicacion.

Hay dos roles:
- admin: acceso completo (Dashboard + Clientes).
- clientes: acceso solo a la pagina de Clientes, con contrasena propia.
"""

import streamlit as st
from ui_components import render_login_form


def _resolve_role(username, password):
    if username == st.secrets.get("APP_USER") and password == st.secrets.get("APP_PASSWORD"):
        return "admin"
    if username == st.secrets.get("CLIENTES_USER") and password == st.secrets.get("CLIENTES_PASSWORD"):
        return "clientes"
    return None


def _login(allowed_roles):
    """
    Renderiza el formulario de login y maneja la autenticacion.
    """
    username, password, col1, col2 = render_login_form()

    if col1.button("Entrar", width="stretch"):
        role = _resolve_role(username, password)
        if role in allowed_roles:
            st.session_state["role"] = role
            st.session_state["username"] = username
            st.rerun()
        else:
            st.error("Usuario o contrasena incorrectos")

    if col2.button("Limpiar", width="stretch"):
        st.rerun()


def check_authentication():
    """
    Acceso al dashboard principal. Solo administradores.
    """
    if st.session_state.get("role") != "admin":
        _login(allowed_roles={"admin"})
        st.stop()


def check_clientes_authentication():
    """
    Acceso a la pagina de clientes. Administradores o usuarios de clientes.
    """
    if st.session_state.get("role") not in {"admin", "clientes"}:
        _login(allowed_roles={"admin", "clientes"})
        st.stop()
