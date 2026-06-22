"""
Configuración central de la aplicación.
"""

# Constantes de autenticación
REQUIRED_COLUMNS = ["cliente", "asignado_a", "size"]

# Colores y tema
PLOT_TEMPLATE = "plotly_dark"
PLOT_COLORS = ["#46a6ff", "#42d392", "#f5b84b", "#ff6b6b", "#9aa9bc", "#b491ff"]

# Paleta de colores CSS
COLOR_VARS = {
    "--app-bg": "#080d14",
    "--surface": "#101823",
    "--surface-soft": "#151f2c",
    "--surface-muted": "#1d2a3a",
    "--ink": "#f3f7fb",
    "--ink-soft": "#c7d2df",
    "--muted": "#8ea0b5",
    "--line": "#253449",
    "--brand": "#46a6ff",
    "--brand-strong": "#78bdff",
    "--success": "#42d392",
    "--warning": "#f5b84b",
    "--danger": "#ff6b6b",
    "--shadow": "0 22px 52px rgba(0, 0, 0, 0.34)",
}

# Página config
PAGE_CONFIG = {
    "page_title": "Dashboard Jira",
    "page_icon": "J",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}

# Filtros
FILTER_COLUMNS = {
    "cliente": "Cliente",
    "asignado_a": "Tecnico asignado",
    "size": "Size",
}

# Top N para ranking
TOP_CLIENTES = 20

# Formato de horas/fechas
DATE_FORMAT = "%d/%m/%Y %H:%M"
