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

## Tests

```bash
cd test-python
source venv/bin/activate
python -m unittest discover -p "test_*.py"
```

