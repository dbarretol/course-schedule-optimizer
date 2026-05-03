import pandas as pd
import sys
import os
from model.scheduler import solve_schedule


def main():
    csv_path = os.path.join('data', 'input-courses.csv')
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} no encontrado.")
        return

    try:
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, sep=';', encoding='latin-1')

    # Validar columnas requeridas
    REQUIRED_COLUMNS = ['ID Curso', 'Curso', 'Inicio', 'Días',
                        'Hora inicio', 'Hora fin', 'Horas', 'Prioridad']
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        print(f"Error: Faltan columnas requeridas: {missing}")
        print(f"Columnas encontradas: {list(df.columns)}")
        return

    if df.empty:
        print("Error: El archivo CSV está vacío.")
        return

    # Data cleaning
    df['Horas'] = pd.to_numeric(df['Horas'], errors='coerce')
    df['Prioridad'] = pd.to_numeric(df['Prioridad'], errors='coerce')
    df = df.dropna(subset=['Curso', 'Horas', 'Prioridad'])
    if df.empty:
        print("Error: No quedaron datos válidos después de limpiar.")
        return

    print("--- Optimizador de Horarios v3 ---")
    print(f"Cargadas {len(df)} filas de datos.")

    results = solve_schedule(df)

    # Prepare Output String
    output_lines = []
    output_lines.append("=" * 30)
    output_lines.append("RESULTADO DE LA OPTIMIZACIÓN")
    output_lines.append("=" * 30)

    for account in ['account1', 'account2']:
        acc_name = "CUENTA 1" if account == 'account1' else "CUENTA 2"
        items = results[account]
        output_lines.append(f"\n{acc_name} ({len(items)} cursos):")
        items.sort(key=lambda x: (x['priority'], x['name']))
        for item in items:
            output_lines.append(
                f"  [{item['id']}] {item['name']} (Prioridad {item['priority']})"
            )

    if results['unassigned']:
        output_lines.append(
            f"\nCURSOS NO ASIGNADOS ({len(results['unassigned'])} cursos):"
        )
        items = results['unassigned']
        items.sort(key=lambda x: (x['priority'], x['name']))
        for item in items:
            output_lines.append(
                f"  [{item['id']}] {item['name']} (Prioridad {item['priority']})"
            )
    else:
        output_lines.append("\n¡Todos los cursos han sido asignados!")

    # Mostrar conflictos detectados
    if results.get('conflicts'):
        output_lines.append(
            f"\nCONFLICTOS DETECTADOS ({len(results['conflicts'])} cruces):"
        )
        for conflict in results['conflicts']:
            output_lines.append(
                f"  ⚠ {conflict['course_a']}  ↔  {conflict['course_b']}"
            )

    # Reporte detallado (opcional con -v o --verbose)
    if '--verbose' in sys.argv or '-v' in sys.argv:
        output_lines.append("\nDETALLE DE SESIONES:")
        for account in ['account1', 'account2']:
            for item in results[account]:
                sessions = item.get('sessions', [])
                if sessions:
                    first = sessions[0][0].strftime('%d/%m/%Y')
                    last = sessions[-1][0].strftime('%d/%m/%Y')
                    output_lines.append(
                        f"  [{item['id']}] {item['name']}: "
                        f"{len(sessions)} sesiones ({first} → {last})"
                    )

    output_lines.append("\n" + "=" * 30)

    report = "\n".join(output_lines)
    print(report)

    # Save to data directory
    output_path = os.path.join('data', 'optimization_result.txt')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\nResultado guardado en: {output_path}")


if __name__ == "__main__":
    main()