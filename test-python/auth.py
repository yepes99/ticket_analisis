"""
Autenticacion de la aplicacion.

Roles:
- admin (Web Admin): acceso completo, Dashboard + Clientes, unico que puede
  corregir horas o configurar limites.
- soporte, cs, lector: acceso solo a la pagina de Clientes, en modo consulta.
"""

import streamlit as st
from ui_components import render_login_form


ROLE_CREDENTIALS = {
    "admin": ("APP_USER", "APP_PASSWORD"),
    "soporte": ("SOPORTE_USER", "SOPORTE_PASSWORD"),
    "cs": ("CS_USER", "CS_PASSWORD"),
    "lector": ("LECTOR_USER", "LECTOR_PASSWORD"),
}

ROLE_LABELS = {
    "admin": "Web Admin",
    "soporte": "Soporte",
    "cs": "CS",
    "lector": "Lector",
}

CLIENTES_ROLES = {"admin", "soporte", "cs", "lector"}


def _resolve_role(username, password):
    for role, (user_key, password_key) in ROLE_CREDENTIALS.items():
        if username == st.secrets.get(user_key) and password == st.secrets.get(password_key):
            return role
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


DASHBOARD_ROLES = {"admin", "soporte"}


def check_authentication():
    """
    Acceso al dashboard principal. Web Admin y Soporte (gestion de tickets).
    """
    if st.session_state.get("role") not in DASHBOARD_ROLES:
        _login(allowed_roles=DASHBOARD_ROLES)
        st.stop()


def check_clientes_authentication():
    """
    Acceso a la pagina de clientes. Web Admin, Soporte, CS o Lector.
    """
    if st.session_state.get("role") not in CLIENTES_ROLES:
        _login(allowed_roles=CLIENTES_ROLES)
        st.stop()


def render_logout_button():
    """
    Muestra en la barra lateral el usuario conectado y un boton para cerrar sesion.
    """
    role = st.session_state.get("role")
    if not role:
        return

    username = st.session_state.get("username") or role
    st.sidebar.caption(f"Sesion: {username} ({ROLE_LABELS.get(role, role)})")
    if st.sidebar.button("Cerrar sesion", key="logout_button", width="stretch"):
        st.session_state.pop("role", None)
        st.session_state.pop("username", None)
        st.rerun()
