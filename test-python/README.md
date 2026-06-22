# Proyecto Python - Dashboard de Tickets

Este proyecto procesa y analiza tickets a partir de un archivo CSV subido desde la aplicacion Streamlit. Aplica limpieza de datos, normalizacion de clientes, calculo de SLAs y metricas analiticas.

## Caracteristicas

- Carga de CSV mediante file uploader en Streamlit
- Limpieza y transformacion de datos de tickets
- Normalizacion de clientes, dominios y URLs
- Calculo de tiempos de resolucion
- Evaluacion de SLA por prioridad y size
- Clasificacion automatica de categorias

## Estructura del proyecto

```text
test-python/
- app.py (orquestador principal)
- config.py (configuración, constantes y colores)
- styles.py (CSS)
- ui_components.py (funciones de UI reutilizables)
- auth.py (autenticación)
- data.py (carga y validación de datos)
- metrics.py (cálculo de KPIs)
- charts.py (visualizaciones)

## Instalacion

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

En Linux o macOS:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Ejecutar

```bash
streamlit run app.py
```

Al abrir la aplicacion, sube el CSV desde la barra lateral. El archivo se procesa en memoria y no se guarda en el repositorio.

Los archivos CSV estan ignorados por Git mediante `.gitignore` para evitar subir datos sensibles por accidente.
