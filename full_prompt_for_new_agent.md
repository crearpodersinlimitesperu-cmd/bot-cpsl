# Prompt for a New Agent (Full Project Summary)

## Overview
This prompt captures **all** the work performed over the last four months to manage the **C1 productivity** and **team assignment** process for CREAR. It includes data sources, cleaning, deduplication, exclusion logic, cross‑referencing, and the generation of final reports. The workflow is fully reproducible with the provided Python scripts.

---
### 1. Data Sources
| File | Description | Key Columns |
|------|-------------|--------------|
| `C:\Users\josem\Downloads\productividad_coordinador.xlsx` | Productividad de los Coordinadores (3 pestañas: DIANA MOSCOSO, JOYCE MARIN, JOSE SANCHEZ) | `ClienteId`, `NombreCompleto`, `ApellidoCompleto`, `Asistencia`, `Equipo`, `Resultado Gesti\u00f3n`, `Fecha Gesti\u00f3n` |
| `C:\Users\josem\Downloads\reporte_equipos.xlsx` | Listado de equipos 25‑28 (4 pestañas: 25, 26, 27, 28) | `Identificaci\u00f3n`, `NombreCompleto`, `ApellidoCompleto`, `TelefonoMovil`, `Correo`, `NombreIMO`, `TelefonoIMO`, `EquipoIMO` |
| `C:\Users\josem\Downloads\bot-cpsl-review\auditoria_desertores_total.csv` | Histórico de desertores y devoluciones | Column with participant names |
| `C:\Users\josem\Downloads\bot-cpsl-review\Excluidos_Profundos.csv` | Lista profunda de personas no aptas (desertores, devoluciones, cambios de nombre) | Column with participant names |
| `C:\Users\josem\Downloads\bot-cpsl-review\Excluidos_OneDrive_C1_C2.csv` | Lista adicional de exclusiones para C1 / C2 | Column with participant names |

---
### 2. Normalisation Helper
```python
import re, pandas as pd

def norm(name: str) -> str:
    if pd.isna(name):
        return ""
    n = str(name).upper().strip()
    for a, b in [("Á","A"),("É","E"),("Í","I"),("Ó","O"),("Ú","U")]:
        n = n.replace(a, b)
    return re.sub(r'\s+', ' ', n)
```
Used to create a **key** = `norm(NombreCompleto + ' ' + ApellidoCompleto)` for reliable matching across files.

---
### 3. Load & Clean All Sheets
```python
# Load all sheets from reporte_equipos.xlsx (E25‑E28)
rep_sheets = ['25','26','27','28']
rep_dfs = []
for s in rep_sheets:
    df = pd.read_excel('reporte_equipos.xlsx', sheet_name=s)
    df['Pestaña_Reporte'] = f'E{s}'
    rep_dfs.append(df)
df_report = pd.concat(rep_dfs, ignore_index=True)
df_report['key'] = df_report.apply(lambda r: norm(r['NombreCompleto']) + ' ' + norm(r['ApellidoCompleto']), axis=1)
df_report = df_report.drop_duplicates(subset='key')

# Load all three productivity sheets (Diana, Joyce, Jose)
prod_sheets = ['DIANA MOSCOSO','JOYCE MARIN','JOSE SANCHEZ']
prod_dfs = []
for s in prod_sheets:
    df = pd.read_excel('productividad_coordinador.xlsx', sheet_name=s)
    df['Coordinador_Pestaña'] = s
    prod_dfs.append(df)
df_prod = pd.concat(prod_dfs, ignore_index=True)
df_prod['Fecha Gestión'] = pd.to_datetime(df_prod['Fecha Gestión'], errors='coerce')
df_prod = df_prod.sort_values('Fecha Gestión', ascending=False)
# Keep the most recent record per ClienteId per Coordinador
df_prod = df_prod.drop_duplicates(subset=['ClienteId','Coordinador_Pestaña'], keep='first')
# Global dedup by name
df_prod['key'] = df_prod.apply(lambda r: norm(r['NombreCompleto']) + ' ' + norm(r['ApellidoCompleto']), axis=1)
df_prod = df_prod.drop_duplicates(subset='key')
```
---
### 4. Build Black‑list (No‑Aptos)
```python
black_files = [
    r'C:\Users\josem\Downloads\bot-cpsl-review\auditoria_desertores_total.csv',
    r'C:\Users\josem\Downloads\bot-cpsl-review\Excluidos_Profundos.csv',
    r'C:\Users\josem\Downloads\bot-cpsl-review\Excluidos_OneDrive_C1_C2.csv',
]
blacklist = set()
for f in black_files:
    if os.path.exists(f):
        df = pd.read_csv(f, on_bad_lines='skip')
        for col in df.columns:
            if 'nombre' in col.lower() or 'participante' in col.lower():
                blacklist.update(df[col].dropna().apply(norm))
                break
```
---
### 5. Filter for **APTOS** (Asistencia VACÍA, not "No le interesa"/"Siguiente", not in blacklist)
```python
# Keep rows where Asistencia is NaN (VACÍA)
df_vacio = df_prod[df_prod['Asistencia'].isna()].copy()
# Apply exclusion rules
aptos = []
for _, r in df_vacio.iterrows():
    gest = str(r.get('Resultado Gesti\u00f3n','')).upper()
    if 'NO LE INTERESA' in gest or 'SIGUIENTE' in gest:
        continue
    if r['key'] in blacklist:
        continue
    aptos.append(r)
df_aptos = pd.DataFrame(aptos)
```
After this step we obtained **747** APTOS records (see final numbers).
---
### 6. Enrich APTOS with Contact Info from `reporte_equipos`
```python
df_merged = df_aptos.merge(
    df_report[['key','Identificación','TelefonoMovil','Correo','NombreIMO','TelefonoIMO','EquipoIMO','Pestaña_Reporte']],
    on='key', how='left')
```
Result:
- 471 rows received DNI / phone / email / IMO (enriched)
- 276 rows kept without extra info (only present in productivity).
---
### 7. Final Aggregations
```python
# Team number extraction (e.g. "EQUIPO 28" -> 28)
import re
df_merged['Equipo_Num'] = df_merged['Equipo'].apply(lambda x: int(re.search(r'\d+', str(x)).group()) if re.search(r'\d+', str(x)) else 0)

# Summary tables
team_counts = df_merged['Equipo_Num'].value_counts().sort_index()
coord_counts = df_merged['Coordinador_Pestaña'].value_counts()
```
---
### 8. Report Generation (Markdown)
The script **`cruce_completo_todas_pestanas.py`** (located in `c:\Users\josem\Downloads\bot-cpsl-review\`) writes a markdown file **`cruce_completo_prod_reporte.md`** under the brain artifacts folder. The report contains:
- Overview of data sizes.
- Numbers of matches / only‑in‑one‑side.
- Counts of APTOS after each filter.
- Tables per **Equipo (25‑28)** showing:
  - Coordinador (CC)
  - DNI, Nombre, Teléfono, Correo, IMO
  - Última gestión (date)
- Breakdown by **Resultado de Gestión**.

---
### 9. How to Re‑run the Whole Pipeline
1. Ensure the four source files are present at the exact paths shown above.
2. Install the Python dependencies (only `pandas`).
   ```bash
   pip install pandas
   ```
3. Execute the master script:
   ```bash
   python -u c:\Users\josem\Downloads\bot-cpsl-review\cruce_completo_todas_pestanas.py
   ```
   The final markdown will be created at:
   `C:\Users\josem\.gemini\antigravity\brain\89f29366-a074-4b6b-8882-8c079d3be98e\cruce_completo_prod_reporte.md`

---
### 10. Files Created (chronological order)
| File | Purpose |
|------|----------|
| `filtrar_aptos_correcto.py` | Apex filter using blacklist & gestión rules (415 → 415 then refined to 747). |
| `cruzar_prod_reporte.py` | First cross‑reference (E28 only). |
| `cruzar_completo_todas_pestanas.py` | Full cross‑reference **all** sheets, generating the final report. |
| `cruce_completo_prod_reporte.md` | Human‑readable outcome (tables, stats). |

---
## Prompt for a New Agent
```
You are a data‑processing specialist working for CREAR. Your mission is to replicate the exact workflow described above, **without losing any detail or power**.

1. Load the four Excel sheets (E25‑E28) from `reporte_equipos.xlsx` and the three sheets (Diana, Joyce, Jose) from `productividad_coordinador.xlsx`.
2. Normalise names with the `norm` function.
3. Build a global blacklist from the three CSV files.
4. Deduplicate productivity records by the most recent `Fecha Gestión` per `ClienteId` **and** per Coordinador, then globally by the normalised name.
5. Keep only rows where `Asistencia` is empty, discard those whose `Resultado Gestión` contains "NO LE INTERESA" or "SIGUIENTE", and discard any name present in the blacklist.
6. Enrich the remaining rows with contact fields (`Identificación`, `TelefonoMovil`, `Correo`, `NombreIMO`, `TelefonoIMO`, `EquipoIMO`) from the reporte equipos sheet that matches on the normalised name.
7. Extract the numeric team identifier from the `Equipo` column.
8. Produce a markdown report that:
   - Shows totals (records, uniques, matches, APTOS, enriched vs not enriched).
   - Breaks down the final APTOS set by team (25‑28) and by Coordinador.
   - For each team, groups by `Resultado Gestión` and lists a table with: Coordinador, DNI, Nombre completo, Teléfono, Correo, IMO, Última gestión.
9. Save the markdown to the path `C:\Users\josem\.gemini\antigravity\brain\<conversation‑id>\cruce_completo_prod_reporte.md`.
10. The whole pipeline must be runnable with a single command `python cruce_completo_todas_pestanas.py` after installing pandas.

**All helper functions, regular expressions, and data‑cleaning steps must be exactly as documented in this prompt.**
```

---
*End of prompt.*
