import numpy as np


CATEGORY_RULES = [
    (r"instagram|facebook|social", "Redes Sociales"),
    (r"seo", "SEO"),
    (r"payment|pago|paypal|stripe", "Pagos"),
    (r"booking|reserva", "Reservas"),
    (r"design|font|logo|web", "Diseño Web"),
    (r"email|mail", "Email"),
    (r"dominio|dns", "Dominios"),
]


def completar_titulo_ticket(df):
    df = df.copy()

    df["titulo_ticket"] = (
        df["resumen"].astype(str).str.extract(r"^[^-–]+[-–]\s*(.+)$", expand=False)
    )
    df["titulo_ticket"] = df["titulo_ticket"].fillna(df["resumen"])
    return df


def completar_categoria_auto(df):
    df = df.copy()

    condiciones = [
        df["titulo_ticket"].str.contains(regex, case=False, na=False)
        for regex, _ in CATEGORY_RULES
    ]
    categorias = [categoria for _, categoria in CATEGORY_RULES]

    df["categoria_auto"] = np.select(condiciones, categorias, default="Otros")
    return df


def completar_categorias(df):
    df = completar_titulo_ticket(df)
    return completar_categoria_auto(df)