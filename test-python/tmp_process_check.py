from process import cargar_tickets

df = cargar_tickets(None)
print(df.head(2).to_string())
print('columns', list(df.columns))
print('rows', len(df))
