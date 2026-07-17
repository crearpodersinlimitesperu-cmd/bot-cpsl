import glob
import sys
sys.stdout.reconfigure(encoding='utf-8')

pattern = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\**\Asignacion_C1.xlsx"
files = glob.glob(pattern, recursive=True)
print("Files found:", files)
