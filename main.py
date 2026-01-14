import pandas as pd
from model.scheduler import solve_schedule
import os

def parse_markdown_table(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Filter out separator lines and empty lines
    table_lines = [l.strip() for l in lines if '|' in l and '---' not in l]
    if not table_lines:
        return pd.DataFrame()
    
    # Header
    header = [c.strip() for c in table_lines[0].split('|') if c.strip()]
    data = []
    for line in table_lines[1:]:
        cols = [c.strip() for c in line.split('|') if c.strip()]
        if len(cols) == len(header):
            data.append(cols)
            
    return pd.DataFrame(data, columns=header)

def main():
    txt_path = os.path.join('data', 'cursos.txt')
    if not os.path.exists(txt_path):
        print(f"Error: {txt_path} no encontrado.")
        return

    df = parse_markdown_table(txt_path)
    if df.empty:
        print("Error: No se pudo parsear la tabla de cursos.")
        return

    # Data cleaning
    df['Horas'] = pd.to_numeric(df['Horas'], errors='coerce')
    df['Prioridad'] = pd.to_numeric(df['Prioridad'], errors='coerce')
    df = df.dropna(subset=['Curso', 'Horas', 'Prioridad'])
    
    # Map 'Prioridad' column to 'PRIORIDAD' for the solver
    df['PRIORIDAD'] = df['Prioridad'].astype(int)

    print("--- Optimizador de Horarios v2.1 ---")
    print(f"Cargados {len(df)} cursos.")
    
    results = solve_schedule(df)
    
    print("\n" + "="*30)
    print("RESULTADO DE LA OPTIMIZACIÓN")
    print("="*30)
    
    for account in ['account1', 'account2']:
        acc_name = "CUENTA 1" if account == 'account1' else "CUENTA 2"
        items = results[account]
        print(f"\n{acc_name} ({len(items)} cursos):")
        items.sort(key=lambda x: (x['priority'], x['name']))
        for item in items:
            print(f"  [{item['id']}] {item['name']}")
        
    if results['unassigned']:
        print(f"\nCURSOS NO ASIGNADOS ({len(results['unassigned'])} cursos):")
        items = results['unassigned']
        items.sort(key=lambda x: (x['priority'], x['name']))
        for item in items:
            print(f"  [{item['id']}] {item['name']}")
    else:
        print("\n¡Todos los cursos han sido asignados!")

    print("\n" + "="*30)

if __name__ == "__main__":
    main()
