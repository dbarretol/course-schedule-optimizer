import pandas as pd
from model.scheduler import generate_sessions

def test_inference_sessions():
    row = {
        'Curso': 'Inferencia Estadística con Python 8va Edic.',
        'Inicio': '2026-02-10',
        'Horario': 'Mar 12:00–15:00, Jue 12:00–17:00',
        'Horas': 16
    }
    
    sessions = generate_sessions(row)
    print(f"--- Tests for {row['Curso']} ---")
    total_duration = 0
    for i, (start, end) in enumerate(sessions):
        duration = (end - start).total_seconds() / 3600
        total_duration += duration
        print(f"Session {i+1}: {start.strftime('%a %Y-%m-%d %H:%M')} to {end.strftime('%H:%M')} ({duration}h)")
    
    print(f"Total Duration: {total_duration}h")

if __name__ == "__main__":
    test_inference_sessions()
