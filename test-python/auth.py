"""
Autenticacion y enrutado de la aplicacion.

Un unico login (en el punto de entrada, app.py) resuelve el rol; a partir
de ahi, st.navigation() solo enseña en la barra lateral las paginas a las
que ese rol tiene acceso. Antes de iniciar sesion no se enseña ninguna
pagina en la barra lateral.

Roles:
- admin (Web Admin): Dashboard + Clientes. Unico que aprueba solicitudes.
- soporte: Dashboard + Clientes. Puede solicitar cambios de horas/limite.
- cs, lector: solo Clientes.
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

DASHBOARD_ROLES = {"admin", "soporte"}
CLIENTES_ROLES = {"admin", "soporte", "cs", "lector"}


def _resolve_role(username, password):
    for role, (user_key, password_key) in ROLE_CREDENTIALS.items():
        if username == st.secrets.get(user_key) and password == st.secrets.get(password_key):
            return role
    return None


def _paginas_por_rol():
    """
    Crea los st.Page de la app. Se recrean en cada ejecucion del script de
    entrada (asi lo espera st.navigation), no se guardan como constantes.
    """
    dashboard = st.Page("dashboard_page.py", title="Dashboard", icon="📊")
    clientes = st.Page("clientes_page.py", title="Clientes", icon="🧾")
    return {
        "admin": [dashboard, clientes],
        "soporte": [dashboard, clientes],
        "cs": [clientes],
        "lector": [clientes],
    }


def login_gate():
    """
    Si ya hay una sesion iniciada, devuelve el rol sin dibujar nada.
    Si no, muestra el formulario de login (sin ninguna pagina en la barra
    lateral todavia) y devuelve None.
    """
    role = st.session_state.get("role")
    if role:
        return role

    username, password, col1, col2 = render_login_form(
        subtitulo="Introduce tus credenciales para acceder al dashboard de soporte web.",
    )

    if col1.button("Entrar", width="stretch", key="login_entrar"):
        resolved = _resolve_role(username, password)
        if resolved is None:
            st.error("Usuario o contrasena incorrectos.")
        else:
            st.session_state["role"] = resolved
            st.session_state["username"] = username
            st.rerun()

    if col2.button("Limpiar", width="stretch", key="login_limpiar"):
        st.session_state.pop("login_username", None)
        st.session_state.pop("login_password", None)
        st.rerun()

    return None


def obtener_paginas(role):
    """Lista de st.Page visibles en la barra lateral para este rol."""
    return _paginas_por_rol().get(role, [])


def check_authentication():
    """
    Guarda de seguridad dentro de dashboard_page.py. El acceso ya se
    decidio en el router (app.py); esto es solo defensa en profundidad.
    """
    if st.session_state.get("role") not in DASHBOARD_ROLES:
        st.stop()


def check_clientes_authentication():
    """
    Guarda de seguridad dentro de clientes_page.py (ver check_authentication).
    """
    if st.session_state.get("role") not in CLIENTES_ROLES:
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
