import pandas as pd
from model.scheduler import generate_sessions_for_group

def test_inference_group():
    data = [
        {'ID Curso': 319, 'Curso': 'Inferencia Estadística con Python', 'Inicio': '10/02/2026', 'Días': 'Martes', 'Hora inicio': '12:00', 'Hora fin': '15:00', 'Horas': 16, 'Prioridad': 1},
        {'ID Curso': 319, 'Curso': 'Inferencia Estadística con Python', 'Inicio': '10/02/2026', 'Días': 'Jueves', 'Hora inicio': '12:00', 'Hora fin': '17:00', 'Horas': 16, 'Prioridad': 1}
    ]
    df = pd.DataFrame(data)
    
    sessions = generate_sessions_for_group(df)
    print(f"--- Tests for ID 319 (Grouped) ---")
    total_duration = 0
    for i, (start, end) in enumerate(sessions):
        duration = (end - start).total_seconds() / 3600
        total_duration += duration
        print(f"Session {i+1}: {start.strftime('%a %Y-%m-%d %H:%M')} to {end.strftime('%H:%M')} ({duration}h)")
    
    print(f"Total Duration: {total_duration}h")

if __name__ == "__main__":
    test_inference_group()
