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
- app.py              # login y enrutado por rol
- auth.py             # roles y permisos
- config.py           # colores, constantes y config de pagina
- styles.py           # CSS de la app
- ui_components.py    # cabecera, tarjetas KPI, titulos de seccion

- process.py          # consulta a Jira y transformacion de los tickets
- cliente.py          # a que cliente pertenece cada ticket
- categorias.py       # clasificacion de categorias
- sla.py              # tiempos, SLA y presupuesto
- bono.py             # bonos de horas y semaforo de saldo
- limites.py          # limite de horas contratadas por cliente
- presupuesto.py      # presupuesto de cliente vs. tiempo de desarrollo
- solicitudes.py      # solicitudes de cambio de horas/limite
- historial.py        # ultimas busquedas y ultimos cambios
- busqueda.py         # panel de busqueda de ticket y cliente
- metrics.py          # KPIs y agregados
- data.py             # filtros de la barra lateral
- periodos.py         # rangos de fecha
- charts.py           # graficos
- backlog_metrics.py  # metricas de backlog
- report.py           # exportes a Excel y PDF

- dashboard_page.py   # pagina Dashboard (Web Admin y Soporte)
- clientes_page.py    # pagina Clientes (todos los roles)
- clientes_ui.py      # bloques de UI de clientes, compartidos por las dos
```

## Instalacion

Linux / macOS:

```bash
cd test-python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
cd test-python
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecutar en local

```bash
cd test-python
source venv/bin/activate      # Windows: venv\Scripts\activate
streamlit run app.py
```

Se abre en <http://localhost:8501>. Si el puerto esta ocupado: `streamlit run app.py --server.port 8502`.

Hace falta el fichero `.streamlit/secrets.toml` con los usuarios de la app y las credenciales de Jira (no esta en git).

Al entrar, inicia sesion con tu usuario; segun el rol veras el Dashboard, la pagina de Clientes o ambas. Elige el periodo en la barra lateral y pulsa "Consultar Jira" para cargar los datos.

## Buscar un ticket o un cliente

Arriba del Dashboard y de la pagina de Clientes hay un desplegable **"🔎 Buscar ticket o cliente"** con dos buscadores independientes, que se pueden usar a la vez:

- **Ticket**: lista los tickets del periodo cargado y deja escribir cualquier clave (`WP-30966`, `wp30966` o solo `30966`). Al elegir uno se enseña su ficha completa (cliente, estado, horas vs. presupuesto, SLA, tecnico, fechas) y la pagina queda filtrada por ese ticket.
- **Cliente**: deja toda la pagina filtrada por ese cliente.

Si el ticket que buscas no esta en el periodo cargado, no hace falta cambiar el periodo: se consulta a Jira por su clave y se enseña su ficha, avisando de que viene de Jira. El resto de la pagina se queda como estaba.

## Bono de horas, limite contratado y colores del ranking

El **limite de horas contratadas** de un cliente es la suma de los bonos que ha comprado (tickets cuya descripcion lleva un texto tipo "10h web changes bundle"). Mientras un cliente no tenga ningun bono en Jira se usa el valor que se ponga a mano (ver abajo); la tabla marca cada limite con `(auto)` o `(manual)` para que se sepa de donde sale.

Las **horas disponibles** son siempre `limite contratado - horas consumidas`. Con bonos eso es exactamente el saldo del bono, y con un limite manual es lo mismo, asi que el semaforo funciona igual en los dos casos:

| Horas disponibles | Color |
| --- | --- |
| 10 h o mas | verde |
| menos de 10 h (aviso claro por debajo de 2 h) | naranja |
| 0 h o negativo | rojo |
| sin limite contratado definido | gris (`—`) |

En la tabla del ranking de clientes se pintan con ese semaforo las columnas **Limite contratado** y **Horas disponibles**. Las **Horas consumidas** se pintan aparte en naranja/rojo cuando se pasan del limite (mas de 8 h y mas de 10 h por encima). Las tres columnas van justo despues de "Tickets Bug" para que el estado se vea sin hacer scroll.

### Poner el limite a mano (mientras no haya bonos)

`Clientes` → pestaña **Detalle por cliente** → elegir el cliente → desplegable **⚙️ Gestionar horas y limite** → pestaña **Cambiar limite del cliente** → escribir las horas y guardar.

Guardar el limite crea una **solicitud** que un Web Admin tiene que aprobar desde el Dashboard (tambien las que crea el propio Web Admin: toda solicitud se aprueba a mano). Una vez aprobada, la fila del cliente ya sale con color en el ranking.

## Estimacion vs. tiempo de desarrollo real

Jira tiene un campo **"Presupuesto cliente (en horas)"** (`customfield_17136`): lo rellena el propio desarrollador con las horas que cree que le va a costar el ticket. Se compara con el **tiempo de desarrollo real**, para ver como de bien se estima.

Los tiempos que calcula la app a partir del historial de estados de Jira son tres, y no significan lo mismo:

| Columna | Que mide | Desde | Hasta |
| --- | --- | --- | --- |
| `horas_transcurridas` | Tiempo total de vida del ticket | Creacion | Resolucion (o ahora) |
| `horas_resolucion` | Tiempo de respuesta al cliente | Creacion | Finalizada |
| `horas_trabajo_real` | **Tiempo de desarrollo** | Sale de Backlog (un tecnico lo coge) | Finalizada (o ahora) |

Las tres descuentan el tiempo que el ticket estuvo en *Pending Info* (esperar respuesta del cliente no es trabajo del equipo).

La estimacion se compara con **`horas_trabajo_real`**, no con las otras dos: `horas_transcurridas` y `horas_resolucion` cuentan desde que se creo el ticket, asi que incluyen todo el rato que estuvo en Backlog sin que nadie lo tocara. Un ticket que espera dos semanas en cola y luego se hace en 3 h no se ha pasado de una estimacion de 4 h, pero con esas columnas lo pareceria.

`desviacion_presupuesto = horas_trabajo_real - presupuesto_cliente`, con este semaforo:

| Desarrollo real | Color |
| --- | --- |
| dentro de lo estimado | verde |
| hasta un 25% por encima | naranja |
| mas de un 25% por encima | rojo |

Los umbrales estan en `sla.PRESUPUESTO_AVISO_RATIO` y `sla.PRESUPUESTO_GRAVE_RATIO`.

Donde se ve:

- **Dashboard** → seccion *"💶 Estimacion vs. tiempo de desarrollo real"*, con los totales del periodo y la lista de tickets estimados.
- **Clientes** → *Detalle por cliente* → pestaña *💶 Presupuesto*, lo mismo pero de ese cliente.
- **Clientes** → *Detalle por cliente* → pestaña *📋 Tickets*: columnas `Presupuesto cliente` y `Desviacion`, con la fila pintada cuando se ha pasado.

> El campo antiguo **"Budget"** (`customfield_16862`) se sigue calculando (columnas `presupuesto` y `diferencia_horas`) pero ya no se enseña en la tabla: **no lo rellena nadie**, en los ultimos dos meses no habia ni un solo ticket con ese campo puesto. Para volver a verlo basta con añadir `"presupuesto"` y `"diferencia_horas"` a `clientes_ui.TICKETS_COLUMN_ORDER`.

## Historial

- **Ultimas busquedas**: al buscar un ticket o un cliente, el desplegable de busqueda guarda las ultimas 6 de cada tipo como botones. Un clic las repite. Son de la sesion de cada persona y no se guardan en disco.
- **Ultimos cambios**: linea de tiempo con los ultimos cambios de horas y de limite, con su estado (pendiente / aprobado / rechazado), quien lo pidio o reviso y cuando. Esta en la pestaña *📜 Historial de cambios* de la pagina Clientes (global) y en *Detalle por cliente → 🎟️ Bono y cambios* (solo de ese cliente). El Web Admin la ve tambien arriba del Dashboard, junto a la tabla completa con descarga en Excel.

## Tests

```bash
cd test-python
source venv/bin/activate
python -m unittest discover -p "test_*.py"
```

