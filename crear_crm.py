import sys
import os
import time

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    print("=" * 60)
    print("                CREAR GLOBAL® ENTERPRISE CRM")
    print("                Operational Hub - v1.0.0")
    print("=" * 60)
    print()

def run_hygiene_module():
    print_header()
    print("[MÓDULO DE HIGIENE Y REPUTACIÓN]")
    print("Analizando base de datos en busca de errores tipográficos y correos inválidos...")
    try:
        from crear_hygiene_core import EmailHygiene
        hygiene = EmailHygiene()
        fixed, invalid = hygiene.sanitize_database()
        print("\n--- RESULTADOS ---")
        print(f"Correos corregidos (Typos): {fixed}")
        print(f"Correos en cuarentena (Inválidos): {invalid}")
    except Exception as e:
        print(f"\n[ERROR] Fallo al ejecutar el módulo: {e}")
    input("\nPresione ENTER para continuar...")

def run_watchtower_module():
    print_header()
    print("[EXPERIENCE WATCHTOWER]")
    print("Escaneando base de datos en busca de participantes en riesgo...")
    try:
        from crear_alert_system import ExperienceWatchtower
        watchtower = ExperienceWatchtower()
        alerts = watchtower.scan_for_risks()
        watchtower.trigger_coordinator_notifications(alerts)
    except Exception as e:
        print(f"\n[ERROR] Fallo al ejecutar el módulo: {e}")
    input("\nPresione ENTER para continuar...")

def run_pilot_dispatch():
    print_header()
    print("[MÓDULO DE DESPACHO - LOTE PILOTO]")
    print("Iniciando envío escalonado para validación de experiencia...")
    print("ADVERTENCIA: Esto enviará correos reales usando Gmail SMTP.")
    confirm = input("¿Desea continuar? (S/N): ")
    if confirm.lower() == 's':
        try:
            # Import dynamically to avoid loading everything on startup
            import ejecutar_piloto_vuelo
            ejecutar_piloto_vuelo.execute_pilot_batch(limit=15)
        except Exception as e:
            print(f"\n[ERROR] Fallo al ejecutar el módulo: {e}")
    else:
        print("Operación cancelada.")
    input("\nPresione ENTER para continuar...")

def run_logistics_module():
    print_header()
    print("[CREAR LOGISTICS CLOUD]")
    print("Opciones disponibles:")
    print("1. Ejecutar simulación de vuelo (Recordatorio & Retraso)")
    print("2. Volver al menú principal")
    opc = input("\nSeleccione una opción: ")
    if opc == '1':
        try:
            import test_logistics
            test_logistics.test_logistics_flight_tracking()
        except Exception as e:
            print(f"\n[ERROR] Fallo al ejecutar el módulo: {e}")
    input("\nPresione ENTER para continuar...")

def run_analytics_module():
    print_header()
    print("[ANALÍTICA ESTRATÉGICA Y SALUD OPERATIVA]")
    print("Ejecutando diagnóstico de Fase 1...")
    try:
        import check_health
        check_health.check_phase1_health()
        
        print("\nGenerando Dashboard Estratégico (HTML)...")
        # Run dashboard generation as a subprocess or import main
        os.system("python crear_dashboard_engine.py")
        print("El dashboard ha sido generado exitosamente.")
    except Exception as e:
        print(f"\n[ERROR] Fallo al ejecutar el módulo: {e}")
    input("\nPresione ENTER para continuar...")

def main_menu():
    while True:
        print_header()
        print("1. Módulo de Higiene y Reputación (Limpiar Base de Datos)")
        print("2. Experience Watchtower (Alertas de Riesgo de Deserción)")
        print("3. Despacho Institucional (Ejecutar Lote Piloto de Admisión)")
        print("4. Logística de Entrenadores (Seguimiento de Vuelos)")
        print("5. Analítica y Dashboard (Salud Operacional)")
        print("0. Salir")
        print("\n" + "-" * 60)
        
        choice = input("Seleccione una operación (0-5): ")
        
        if choice == '1':
            run_hygiene_module()
        elif choice == '2':
            run_watchtower_module()
        elif choice == '3':
            run_pilot_dispatch()
        elif choice == '4':
            run_logistics_module()
        elif choice == '5':
            run_analytics_module()
        elif choice == '0':
            print("\nCerrando CREAR GLOBAL Enterprise CRM... ¡Hasta pronto!")
            time.sleep(1)
            break
        else:
            print("\nOpción inválida. Intente nuevamente.")
            time.sleep(1)

if __name__ == "__main__":
    # Ensure correct working directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\n\nCierre forzado. Saliendo de CREAR GLOBAL Enterprise CRM...")
        sys.exit(0)
