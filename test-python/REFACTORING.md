# Estructura Modular - Dashboard Jira Pro

## Descripción

El proyecto ha sido refactorizado en módulos temáticos para mejorar la escalabilidad, mantenibilidad y reutilización de código.

## Estructura de Archivos

```
test-python/
├── app.py                 # Orquestador principal
├── config.py              # Configuración central (constantes, colores)
├── styles.py              # CSS y estilos de la aplicación
├── ui_components.py       # Componentes reutilizables de UI
├── auth.py                # Lógica de autenticación
├── data.py                # Carga, validación y filtrado de datos
├── metrics.py             # Cálculo de KPIs y métricas
├── charts.py              # Generación de gráficos
├── process.py             # Procesamiento general (existente)
├── cliente.py             # Lógica de clientes (existente)
├── categorias.py          # Lógica de categorías (existente)
├── sla.py                 # Lógica de SLA (existente)
├── requirements.txt       # Dependencias Python
└── README.md              # Este archivo
```

## Módulos

### `config.py` 🔧
Centraliza toda la configuración de la aplicación:
- Constantes (columnas requeridas, top N, etc.)
- Paleta de colores CSS
- Configuración de página Streamlit
- Formato de fechas

**Uso:** Importar `config` y acceder a variables como `config.PLOT_COLORS`, `config.TOP_CLIENTES`, etc.

### `styles.py` 🎨
Contiene todos los estilos CSS de la aplicación:
- Tema oscuro personalizado
- Variables CSS del color scheme
- Media queries para responsividad
- Función `apply_styles()` para aplicar estilos globales

**Uso:** `from styles import apply_styles` y llamar `apply_styles()` en app.py

### `ui_components.py` 🖼️
Componentes reutilizables de interfaz:
- `section_title()` - Títulos de sección
- `empty_state()` - Estado vacío
- `kpi_grid()` - Grilla de KPI cards
- `render_hero_header()` - Header principal
- `render_login_form()` - Formulario de login
- `render_chart_wrapper()` - Wrapper para gráficos

**Uso:** Importar funciones específicas y usarlas donde sea necesario

### `auth.py` 🔐
Maneja la autenticación:
- `check_authentication()` - Verifica autenticación y detiene si falta
- `login()` - Renderiza formulario y valida credenciales

**Uso:** `from auth import check_authentication` y llamar al inicio de app.py

### `data.py` 📊
Gestiona datos:
- `load_data()` - Carga CSV con caché
- `validate_columns()` - Valida columnas requeridas
- `load_and_validate_data()` - Orquestador de carga y validación
- `render_filters()` - Renderiza controles de filtro
- `apply_filters()` - Aplica filtros al DataFrame

**Uso:** Importar funciones para cargar, validar y filtrar datos

### `metrics.py` 📈
Cálculo de KPIs y métricas:
- `pct()` - Calcula porcentajes
- `calculate_sla_kpis()` - KPIs principales
- `calculate_sla_size_comparison()` - SLA vs real por size
- `calculate_technician_ranking()` - Ranking de técnicos
- `calculate_top_clients()` - Top clientes

**Uso:** Importar funciones para calcular métricas específicas

### `charts.py` 📉
Generación de gráficos:
- `apply_chart_layout()` - Aplica estilos a gráficos Plotly
- `create_sla_comparison_chart()` - Gráfico SLA vs real
- `create_top_clients_chart()` - Gráfico de top clientes

**Uso:** Importar y llamar funciones para crear visualizaciones

### `app.py` 🎯
**Orquestador principal** que integra todos los módulos:
1. Configuración inicial y estilos
2. Autenticación
3. Carga de archivo CSV en sidebar
4. Carga y validación de datos
5. Filtros
6. Renderizado de visualizaciones
7. Presentación de métricas

El archivo ahora es mucho más legible y sus ~170 líneas son principalmente lógica de flujo.

## Beneficios de la Refactorización

✅ **Escalabilidad**: Agregar nuevas métricas, gráficos o componentes es más fácil
✅ **Mantenibilidad**: Cambios en estilos o lógica están centralizados
✅ **Reutilización**: Componentes y funciones pueden usarse en múltiples lugares
✅ **Testabilidad**: Módulos independientes son más fáciles de testear
✅ **Legibilidad**: Código organizado y con responsabilidades claras
✅ **Modularidad**: Cada módulo tiene una responsabilidad específica

## Cómo Agregar Nuevas Funcionalidades

### Agregar un nuevo gráfico:
1. Crear función en `charts.py`
2. Importarla en `app.py`
3. Usarla en el flujo principal

### Agregar una nueva métrica:
1. Crear función en `metrics.py`
2. Importarla donde sea necesaria
3. Usar en `app.py` para mostrarla

### Agregar un nuevo componente UI:
1. Crear función en `ui_components.py`
2. Importarla donde sea necesaria
3. Integrarla en el flujo

### Cambiar constantes globales:
1. Editar `config.py`
2. Los cambios aplican a toda la app automáticamente

## Dependencias

Ver `requirements.txt` para la lista completa. Principales:
- `streamlit` - Framework web
- `pandas` - Análisis de datos
- `plotly` - Visualizaciones interactivas

## Ejecución

```bash
streamlit run app.py
```

## Notas Futuras

Este código está preparado para:
- Agregar más tipos de reportes
- Implementar caché a nivel de base de datos
- Exportar reportes a PDF/Excel
- Integración con APIs externas
- Múltiples vistas/dashboards
