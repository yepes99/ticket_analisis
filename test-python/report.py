"""
Generación de reportes exportables.
"""

from io import BytesIO
from datetime import datetime
import pandas as pd
from fpdf import FPDF


def generate_excel_report(kpis, trend_df, sla_size_df, ranking_df, clientes_df, tech_sla_df):
    """Genera un reporte Excel en memoria."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(
            {
                "KPI": [
                    "Tickets filtrados",
                    "Tickets resueltos",
                    "Tickets abiertos",
                    "Tickets incumplidos",
                    "En riesgo SLA",
                    "SLA prioridad",
                    "SLA size",
                    "SLA global",
                    "Clientes",
                    "Tecnicos",
                    "Promedio resolución (días)",
                ],
                "Valor": [
                    kpis["total_tickets"],
                    kpis["tickets_resueltos"],
                    kpis["tickets_abiertos"],
                    kpis["tickets_incumplidos"],
                    kpis["tickets_en_riesgo"],
                    f"{kpis['sla_prioridad']}%",
                    f"{kpis['sla_size']}%",
                    f"{kpis['sla_global']}%",
                    kpis["total_clientes"],
                    kpis["total_tecnicos"],
                    f"{kpis['dias_resolucion_promedio']}",
                ],
            }
        ).to_excel(writer, sheet_name="Resumen", index=False)

        if not trend_df.empty:
            trend_df.to_excel(writer, sheet_name="Tendencia", index=False)

        if not sla_size_df.empty:
            sla_size_df.to_excel(writer, sheet_name="SLA Size", index=False)

        if not ranking_df.empty:
            ranking_df.to_excel(writer, sheet_name="Ranking Tecnicos", index=False)

        if not clientes_df.empty:
            clientes_df.to_excel(writer, sheet_name="Top Clientes", index=False)

        if not tech_sla_df.empty:
            tech_sla_df.to_excel(writer, sheet_name="SLA Tecnicos", index=False)

        pass
    output.seek(0)
    return output.getvalue()


def generate_pdf_report(kpis, top_clients, top_tech):
    """Genera un reporte PDF simple con los KPIs y tablas principales."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Informe Jira Dashboard", ln=True, align="C")

    pdf.set_font("Arial", "", 11)
    pdf.ln(4)
    pdf.cell(0, 8, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True)
    pdf.ln(3)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "KPIs principales", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.ln(1)

    kpi_lines = [
        ("Tickets filtrados", kpis["total_tickets"]),
        ("Tickets resueltos", kpis["tickets_resueltos"]),
        ("Tickets abiertos", kpis["tickets_abiertos"]),
        ("Tickets incumplidos", kpis["tickets_incumplidos"]),
        ("En riesgo SLA", kpis["tickets_en_riesgo"]),
        ("SLA prioridad", f"{kpis['sla_prioridad']}%"),
        ("SLA size", f"{kpis['sla_size']}%"),
        ("SLA global", f"{kpis['sla_global']}%"),
        ("Promedio resolución", f"{kpis['dias_resolucion_promedio']} días"),
    ]

    for label, value in kpi_lines:
        pdf.cell(70, 7, f"{label}:", border=0)
        pdf.cell(0, 7, str(value), ln=True, border=0)

    def add_table(title, df, columns, max_rows=8):
        pdf.ln(4)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, title, ln=True)
        pdf.set_font("Arial", "", 10)
        pdf.ln(1)

        row_height = 6
        col_widths = [70, 40, 40, 40]
        pdf.set_font("Arial", "B", 10)
        for i, col in enumerate(columns):
            pdf.cell(col_widths[i], row_height, col, border=1)
        pdf.ln(row_height)
        pdf.set_font("Arial", "", 10)

        for idx, row in df.head(max_rows).iterrows():
            pdf.cell(col_widths[0], row_height, str(row[columns[0]]), border=1)
            pdf.cell(col_widths[1], row_height, str(row[columns[1]]), border=1)
            pdf.cell(col_widths[2], row_height, str(row[columns[2]]), border=1)
            pdf.cell(col_widths[3], row_height, str(row[columns[3]]), border=1)
            pdf.ln(row_height)

    if not top_clients.empty:
        add_table(
            "Top clientes",
            top_clients,
            ["cliente", "tickets", "sla", "tiempo"],
        )

    if not top_tech.empty:
        add_table(
            "Top técnicos",
            top_tech,
            ["asignado_a", "tickets", "sla_global", "tiempo"],
        )

    output_data = pdf.output(dest="S")
    if isinstance(output_data, str):
        return output_data.encode("latin-1")
    return output_data
