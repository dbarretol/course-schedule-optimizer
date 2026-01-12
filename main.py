import pandas as pd
from model.scheduler import solve_schedule
import os

def main():
    csv_path = os.path.join('data', 'INPUT.csv')
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} no encontrado.")
        return

    # Read CSV with semicolon separator
    try:
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, sep=';', encoding='latin-1')

    # Data cleaning
    df = df.dropna(subset=['CURSO'])
    
    print("--- Optimizador de Horarios ---")
    print(f"Cargados {len(df)} cursos.")
    
    results = solve_schedule(df)
    
    print("\n" + "="*30)
    print("RESULTADO DE LA OPTIMIZACIÓN")
    print("="*30)
    
    for account in ['account1', 'account2']:
        acc_name = "CUENTA 1" if account == 'account1' else "CUENTA 2"
        items = results[account]
        print(f"\n{acc_name} ({len(items)} cursos):")
        # Sort by priority, then by name
        items.sort(key=lambda x: (x['priority'], x['name']))
        for item in items:
            print(f"  [P{item['priority']}] {item['name']}")
        
    if results['unassigned']:
        print(f"\nCURSOS NO ASIGNADOS ({len(results['unassigned'])} cursos):")
        items = results['unassigned']
        items.sort(key=lambda x: (x['priority'], x['name']))
        for item in items:
            print(f"  [P{item['priority']}] {item['name']}")
    else:
        print("\n¡Todos los cursos han sido asignados!")

    print("\n" + "="*30)

if __name__ == "__main__":
    main()
