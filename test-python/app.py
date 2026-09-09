"""
Punto de entrada: login unico y enrutado por rol.

Antes de iniciar sesion no se enseña ninguna pagina en la barra lateral.
Una vez autenticado, st.navigation() solo enseña las paginas a las que ese
rol tiene acceso (Web Admin/Soporte ven Dashboard + Clientes; CS/Lector solo
Clientes).
"""

import streamlit as st

import config
from styles import apply_styles
from auth import login_gate, obtener_paginas

st.set_page_config(**config.PAGE_CONFIG)
apply_styles()

role = login_gate()
if not role:
    st.stop()

paginas = obtener_paginas(role)
if not paginas:
    st.stop()

nav = st.navigation(paginas)
nav.run()
