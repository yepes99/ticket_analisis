import pandas as pd
from io import StringIO
from process import cargar_tickets
from data import apply_filters

csv = '''Clave de incidencia,Resumen,Tipo de Incidencia,Estado,Categoría de estado,Prioridad,Resolución,Clave del proyecto,Nombre del proyecto,Persona asignada,Informador,Creada,Actualizada,Resuelta,Descripción,Campo personalizado (Web del Cliente / Empresa),Campo personalizado (Domain),Campo personalizado (Dominio),Campo personalizado (Cliente / Empresa),Campo personalizado (Size)
INC-1,Test 1,Bug,Backlog,To Do,Highest,Unresolved,PROJ,Project,Leslie Jara,User,01/Jan/25 10:00 AM,01/Jan/25 10:00 AM,,Desc,Client A,clienta.com,Client A,S
INC-2,Test 2,Tarea,In Progress,In Progress,High,Resolved,PROJ,Project,Carmen Yepes,User,15/Jan/25 10:00 AM,15/Jan/25 10:00 AM,16/Jan/25 10:00 AM,Desc,Client B,clientb.com,Client B,M
'''

df = cargar_tickets(StringIO(csv))
filtered = apply_filters(df, tipos=['Bug'], date_range=(pd.Timestamp('2025-01-01').date(), pd.Timestamp('2025-01-10').date()))
print('rows', len(filtered))
print(filtered[['tipo','fecha_creacion','cliente','asignado_a']].to_string(index=False))
