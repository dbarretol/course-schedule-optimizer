import pandas as pd
from model.scheduler import solve_schedule
import os

def main():
    csv_path = os.path.join('data', 'input-courses.csv')
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} no encontrado.")
        return

    try:
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, sep=';', encoding='latin-1')

    if df.empty:
        print("Error: El archivo CSV está vacío.")
        return

    # Data cleaning
    df['Horas'] = pd.to_numeric(df['Horas'], errors='coerce')
    df['Prioridad'] = pd.to_numeric(df['Prioridad'], errors='coerce')
    df = df.dropna(subset=['Curso', 'Horas', 'Prioridad'])
    
    print("--- Optimizador de Horarios v3 ---")
    print(f"Cargadas {len(df)} filas de datos.")
    
    results = solve_schedule(df)
    
    # Prepare Output String
    output_lines = []
    output_lines.append("="*30)
    output_lines.append("RESULTADO DE LA OPTIMIZACIÓN")
    output_lines.append("="*30)
    
    for account in ['account1', 'account2']:
        acc_name = "CUENTA 1" if account == 'account1' else "CUENTA 2"
        items = results[account]
        output_lines.append(f"\n{acc_name} ({len(items)} cursos):")
        items.sort(key=lambda x: (x['priority'], x['name']))
        for item in items:
            output_lines.append(f"  [{item['id']}] {item['name']} (Prioridad {item['priority']})")
        
    if results['unassigned']:
        output_lines.append(f"\nCURSOS NO ASIGNADOS ({len(results['unassigned'])} cursos):")
        items = results['unassigned']
        items.sort(key=lambda x: (x['priority'], x['name']))
        for item in items:
            output_lines.append(f"  [{item['id']}] {item['name']} (Prioridad {item['priority']})")
    else:
        output_lines.append("\n¡Todos los cursos han sido asignados!")

    output_lines.append("\n" + "="*30)
    
    report = "\n".join(output_lines)
    print(report)
    
    # Save to data directory
    output_path = os.path.join('data', 'optimization_result.txt')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\nResultado guardado en: {output_path}")

if __name__ == "__main__":
    main()
