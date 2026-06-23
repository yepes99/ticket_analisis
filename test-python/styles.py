"""
Estilos CSS de la aplicación.
"""

APP_CSS = """
<style>
:root {
    --app-bg: #080d14;
    --surface: #101823;
    --surface-soft: #151f2c;
    --surface-muted: #1d2a3a;
    --ink: #f3f7fb;
    --ink-soft: #c7d2df;
    --muted: #8ea0b5;
    --line: #253449;
    --brand: #46a6ff;
    --brand-strong: #78bdff;
    --success: #42d392;
    --warning: #f5b84b;
    --danger: #ff6b6b;
    --shadow: 0 22px 52px rgba(0, 0, 0, 0.34);
}

html, body, [data-testid="stAppViewContainer"] {
    background:
        radial-gradient(circle at 15% 0%, rgba(70, 166, 255, 0.12), transparent 32rem),
        linear-gradient(180deg, #080d14 0%, #0b111a 42%, #080d14 100%);
    color: var(--ink);
    font-family: Inter, "Segoe UI", Arial, sans-serif;
}

[data-testid="stHeader"] {
    background: rgba(8, 13, 20, 0.86);
    backdrop-filter: blur(10px);
}

[data-testid="block-container"] {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1440px;
}

[data-testid="stSidebar"] {
    background: #0b1522;
    border-right: 1px solid rgba(255,255,255,0.08);
}

[data-testid="stSidebar"] * {
    color: #e8eef6;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] .stCaptionContainer {
    color: rgba(232,238,246,0.72);
}

[data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.12);
}

/* Estilos robustos para botones en todos los navegadores */
.stButton > button,
button[data-testid="baseButton-primary"],
button[data-testid="baseButton-secondary"],
.stButton button,
[data-testid="stButton"] button {
    border-radius: 8px !important;
    border: 1px solid var(--brand) !important;
    background: linear-gradient(180deg, var(--brand) 0%, #227bd0 100%) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    min-height: 2.75rem !important;
    transition: all 160ms ease !important;
    text-shadow: none !important;
}

.stButton > button:hover,
button[data-testid="baseButton-primary"]:hover,
button[data-testid="baseButton-secondary"]:hover,
.stButton button:hover,
[data-testid="stButton"] button:hover {
    border-color: var(--brand-strong) !important;
    background: linear-gradient(180deg, var(--brand-strong) 0%, #3490e6 100%) !important;
    color: #ffffff !important;
    box-shadow: 0 12px 28px rgba(70, 166, 255, 0.24) !important;
}

/* Asegurar que el texto del botón sea siempre blanco */
.stButton > button span,
button[data-testid="baseButton-primary"] span,
button[data-testid="baseButton-secondary"] span,
.stButton button span,
[data-testid="stButton"] button span {
    color: #ffffff !important;
}

/* Reset de botones para asegurar consistencia */
button {
    color: inherit !important;
}

.stButton > button,
button[data-testid="baseButton-primary"],
button[data-testid="baseButton-secondary"],
.stButton button,
[data-testid="stButton"] button {
    color: #ffffff !important;
}

.stTextInput input,
[data-baseweb="select"] > div,
[data-testid="stFileUploader"] section {
    background: #0c141f;
    border-radius: 8px;
    border-color: var(--line);
    color: var(--ink);
}

.stTextInput input::placeholder {
    color: #6f8195;
}

label,
[data-testid="stWidgetLabel"],
[data-testid="stMarkdownContainer"] p {
    color: var(--ink-soft);
}

[data-testid="stMetric"] {
    background: linear-gradient(180deg, #121d2a 0%, #0f1723 100%);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 1.1rem 1.2rem;
    box-shadow: var(--shadow);
}

[data-testid="stMetricLabel"] {
    color: var(--muted);
}

[data-testid="stMetricValue"] {
    color: var(--ink);
}

.app-shell {
    display: flex;
    flex-direction: column;
    gap: 1.2rem;
}

.hero {
    background:
        linear-gradient(135deg, rgba(24, 36, 52, 0.98) 0%, rgba(16, 24, 35, 0.98) 56%, rgba(13, 36, 56, 0.96) 100%);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 1.35rem 1.5rem;
    box-shadow: var(--shadow);
    margin-bottom: 20px;
}

.hero-topline {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.55rem;
}

.eyebrow {
    color: var(--brand);
    font-size: 0.78rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.timestamp {
    color: var(--muted);
    font-size: 0.88rem;
    white-space: nowrap;
}

.hero h1 {
    color: var(--ink);
    font-size: 2.15rem;
    font-weight: 800;
    line-height: 1.08;
    margin: 0;
}

.hero p {
    color: var(--ink-soft);
    max-width: 840px;
    margin: 0.65rem 0 0;
    line-height: 1.55;
}

.login-wrap {
    max-width: 760px;
    margin: 7vh auto 1.2rem;
    background: linear-gradient(135deg, rgba(18, 29, 42, 0.98), rgba(12, 20, 31, 0.98));
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 2.3rem 2.5rem;
    box-shadow: var(--shadow);
}

.login-wrap h1 {
    color: var(--ink);
    margin: 0 0 0.45rem;
    font-size: 2rem;
}

.login-wrap p {
    color: var(--ink-soft);
    margin: 0 0 1.5rem;
    line-height: 1.5;
}

.section-title {
    display: flex;
    align-items: end;
    justify-content: space-between;
    gap: 1rem;
    margin: 1.35rem 0 0.7rem;
}

.section-title h2 {
    color: var(--ink);
    font-size: 1.12rem;
    margin: 0;
}

.section-title span {
    color: var(--muted);
    font-size: 0.88rem;
}

.empty-state {
    background: var(--surface);
    border: 1px dashed var(--line);
    border-radius: 8px;
    padding: 1.4rem;
    color: var(--ink-soft);
}

.stDataFrame {
    border: 1px solid var(--line);
    border-radius: 8px;
    overflow: hidden;
    box-shadow: var(--shadow);
    background: var(--surface) !important;
}

.stDataFrame td,
.stDataFrame th {
    background: var(--surface) !important;
    color: var(--ink) !important;
}

.stDataFrame tr {
    background: var(--surface) !important;
}

.stDataFrame tr:hover {
    background: var(--surface-soft) !important;
}

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.9rem;
    margin: 1rem 0 0.35rem;
}

.kpi-grid.secondary {
    grid-template-columns: repeat(3, minmax(0, 1fr));
    margin-top: 0.75rem;
}

.kpi-card {
    position: relative;
    overflow: hidden;
    min-height: 108px;
    background: linear-gradient(180deg, #121d2a 0%, #0f1723 100%);
    border: 1px solid var(--line);
    border-radius: 10px;
    padding: 1rem;
    box-shadow: var(--shadow);
}

.kpi-card::before {
    content: "";
    position: absolute;
    inset: 0 0 auto 0;
    height: 3px;
    background: linear-gradient(90deg, var(--brand), var(--success));
}

.kpi-card.success::before {
    background: linear-gradient(90deg, var(--success), #8cf0bd);
}

.kpi-card.warning::before {
    background: linear-gradient(90deg, var(--warning), #ffe08a);
}

.kpi-card.danger::before {
    background: linear-gradient(90deg, var(--danger), #ff9a9a);
}

.kpi-label {
    color: var(--muted);
    font-size: 0.82rem;
    font-weight: 700;
    line-height: 1.25;
    margin: 0 0 0.65rem;
}

.kpi-value {
    color: var(--ink);
    font-size: 2rem;
    font-weight: 850;
    line-height: 1;
    margin: 0;
}

.kpi-sub {
    color: var(--ink-soft);
    font-size: 0.78rem;
    margin-top: 0.65rem;
}

.chart-wrap {
    border: 1px solid var(--line);
    border-radius: 10px;
    overflow: hidden;
    background: var(--surface);
    box-shadow: var(--shadow);
}

div[data-testid="stAlert"] {
    background: #101823;
    border: 1px solid var(--line);
    color: var(--ink-soft);
}

/* Mejorar compatibilidad con tablas en diferentes navegadores */
table {
    background: var(--surface) !important;
    color: var(--ink) !important;
}

table thead {
    background: var(--surface-soft) !important;
}

table thead th {
    background: var(--surface-soft) !important;
    color: var(--ink) !important;
    border-color: var(--line) !important;
}

table tbody tr {
    background: var(--surface) !important;
}

table tbody td {
    background: var(--surface) !important;
    color: var(--ink) !important;
    border-color: var(--line) !important;
}

table tbody tr:hover {
    background: var(--surface-muted) !important;
}

/* Compatibilidad con modo oscuro del navegador */
@media (prefers-color-scheme: dark) {
    .stButton > button,
    button[data-testid="baseButton-primary"],
    button[data-testid="baseButton-secondary"],
    .stButton button,
    [data-testid="stButton"] button {
        color: #ffffff !important;
        background: linear-gradient(180deg, var(--brand) 0%, #227bd0 100%) !important;
    }
    
    .stButton > button span,
    button[data-testid="baseButton-primary"] span,
    button[data-testid="baseButton-secondary"] span,
    .stButton button span,
    [data-testid="stButton"] button span {
        color: #ffffff !important;
    }
    
    .stDataFrame,
    table {
        background: var(--surface) !important;
        color: var(--ink) !important;
    }
}

@media (max-width: 900px) {
    [data-testid="block-container"] {
        padding-left: 1rem;
        padding-right: 1rem;
        padding-top: 1.1rem;
        padding-bottom: 2rem;
    }

    .hero h1 {
        font-size: 1.65rem;
    }

    .hero-topline,
    .section-title {
        align-items: flex-start;
        flex-direction: column;
    }

    .timestamp {
        white-space: normal;
    }

    .login-wrap {
        max-width: 100%;
        margin-top: 2rem;
        padding: 1.65rem;
    }

    .kpi-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    .kpi-grid.secondary {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
}

@media (max-width: 640px) {
    [data-testid="block-container"] {
        padding-left: 0.75rem;
        padding-right: 0.75rem;
    }

    .hero {
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 0.85rem;
    }

    .hero h1 {
        font-size: 1.42rem;
        line-height: 1.15;
    }

    .hero p,
    .login-wrap p {
        font-size: 0.94rem;
    }

    .login-wrap {
        margin-top: 0.75rem;
        padding: 1.2rem;
    }

    .login-wrap h1 {
        font-size: 1.55rem;
    }

    .section-title {
        gap: 0.3rem;
        margin-top: 1rem;
    }

    .section-title h2 {
        font-size: 1rem;
    }

    .section-title span {
        font-size: 0.78rem;
    }

    [data-testid="stMetric"] {
        padding: 0.9rem 1rem;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.55rem;
    }

    .stButton > button {
        min-height: 2.9rem;
        color: #ffffff !important;
    }

    .stButton > button span {
        color: #ffffff !important;
    }

    .kpi-grid,
    .kpi-grid.secondary {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.65rem;
        margin-top: 0.75rem;
    }

    .kpi-card {
        min-height: 96px;
        border-radius: 12px;
        padding: 0.85rem;
    }

    .kpi-label {
        font-size: 0.74rem;
        margin-bottom: 0.5rem;
    }

    .kpi-value {
        font-size: 1.55rem;
    }

    .kpi-sub {
        font-size: 0.72rem;
        margin-top: 0.5rem;
    }

    .chart-wrap {
        border-radius: 12px;
    }

    div[data-testid="stDataFrame"] {
        font-size: 0.78rem;
    }
}

@media (max-width: 390px) {
    .kpi-grid,
    .kpi-grid.secondary {
        grid-template-columns: 1fr;
    }
}
</style>
"""


def apply_styles():
    """Aplica los estilos CSS a la aplicación."""
    import streamlit as st
    st.markdown(APP_CSS, unsafe_allow_html=True)
