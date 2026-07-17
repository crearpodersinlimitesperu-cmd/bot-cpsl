import pandas as pd

excel_path = r'C:\Users\josem\Downloads\ASIGNACIONES 0526.xlsx'

print(f"Leyendo archivo: {excel_path}")
df = pd.read_excel(excel_path)

print("Columnas encontradas:")
print(df.columns.tolist())

print("\nEquipos presentes en el archivo:")
equipos = df.get('NombreEquipo')
if equipos is not None:
    print(equipos.unique())
    
    # Filtrar Equipo 28
    e28 = df[df['NombreEquipo'].str.contains('28', case=False, na=False)]
    print(f"\nTotal de participantes en EQUIPO 28: {len(e28)}")
    
    if len(e28) > 0:
        print("\nMuestra de participantes Equipo 28:")
        print(e28[['Usuario Actual', 'NombreEquipo', 'NombreCompleto', 'Correo']].head(10))
        
        # Check coordinates in E28
        print("\nCoordinadores asignados en EQUIPO 28:")
        print(e28['Usuario Actual'].value_counts())
else:
    print("No se encontró la columna 'NombreEquipo'.")
