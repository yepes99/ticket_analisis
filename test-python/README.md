# Dashboard Jira

Dashboard profesional en Streamlit para consultar tickets directamente desde Jira, calcular SLAs y analizar rendimiento operativo por tecnico, cliente, prioridad y size.

## Caracteristicas

- Consulta directa a Jira mediante token configurado en `.streamlit/secrets.toml`
- Selector de cantidad de tickets a mostrar
- Rangos rapidos de fecha: ultima semana, ultimo mes y ultimo ano
- Rango personalizado de fecha de creacion
- Limpieza y transformacion de datos de tickets
- Calculo de tiempos de resolucion
- Evaluacion precisa de SLA por prioridad, size y global
- Clasificacion automatica de categorias

## Estructura

```text
test-python/
- app.py
- config.py
- styles.py
- ui_components.py
- auth.py
- data.py
- process.py
- sla.py
- metrics.py
- charts.py
- report.py
```

## Instalacion

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecutar

```powershell
streamlit run app.py
```

Al abrir la aplicacion, elige en la barra lateral cuantos tickets quieres consultar y el periodo de creacion. Los datos se consultan directamente desde Jira.
