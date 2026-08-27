# Arquitectura Actual

La aplicacion usa Jira como unica fuente de datos. El flujo antiguo basado en archivos locales se retiro para evitar calculos divergentes entre muestras, snapshots y exportaciones manuales.

## Flujo

```text
app.py
  -> data.py
  -> process.py
  -> cliente.py / categorias.py / sla.py
  -> metrics.py / charts.py / report.py
```

## Responsabilidades

- `app.py`: interfaz Streamlit, controles de consulta y visualizacion.
- `data.py`: validacion y filtros del DataFrame consultado.
- `process.py`: consulta paginada a Jira, resolucion de campos personalizados y normalizacion inicial.
- `sla.py`: reglas de tiempo, riesgo e incumplimiento.
- `metrics.py`: KPIs y tablas agregadas.
- `charts.py`: visualizaciones Plotly.
- `report.py`: exportes Excel y PDF.

## Consulta Jira

La barra lateral permite indicar:

- cantidad maxima de tickets
- ultima semana
- ultimo mes
- ultimo ano
- rango personalizado
- sin limite de fecha

Los filtros de fecha se aplican en JQL sobre `created` antes de descargar los tickets.
