import pandas as pd
from model.scheduler import generate_sessions_for_group, has_conflict
from datetime import datetime


def test_inference_group():
    """Test principal: curso con múltiples días y verificaciones automáticas."""
    data = [
        {'ID Curso': 319, 'Curso': 'Inferencia Estadística con Python',
         'Inicio': '10/02/2026', 'Días': 'Martes',
         'Hora inicio': '12:00', 'Hora fin': '15:00',
         'Horas': 16, 'Prioridad': 1},
        {'ID Curso': 319, 'Curso': 'Inferencia Estadística con Python',
         'Inicio': '10/02/2026', 'Días': 'Jueves',
         'Hora inicio': '12:00', 'Hora fin': '17:00',
         'Horas': 16, 'Prioridad': 1}
    ]
    df = pd.DataFrame(data)
    sessions = generate_sessions_for_group(df)

    # Verificaciones
    assert len(sessions) > 0, "Debe generar al menos una sesión"

    total_duration = sum(
        (end - start).total_seconds() / 3600
        for start, end in sessions
    )
    assert abs(total_duration - 16.0) < 0.01, (
        f"Duración total debe ser 16h, fue {total_duration}h"
    )

    # Verificar que todas las sesiones son martes (1) o jueves (3)
    for start, end in sessions:
        assert start.weekday() in [1, 3], (
            f"Sesión en día incorrecto: {start.strftime('%A %Y-%m-%d')}"
        )

    # Verificar que no hay sesiones con duración negativa o cero
    for start, end in sessions:
        assert end > start, f"Sesión inválida: {start} → {end}"

    # Verificar orden cronológico
    for i in range(1, len(sessions)):
        assert sessions[i][0] >= sessions[i-1][1], (
            "Las sesiones deben estar en orden cronológico sin solaparse"
        )

    print("✅ test_inference_group pasó")

    # Imprimir detalle
    print(f"\n--- Detalle para ID 319 ---")
    for i, (start, end) in enumerate(sessions):
        duration = (end - start).total_seconds() / 3600
        print(f"Sesión {i+1}: {start.strftime('%a %Y-%m-%d %H:%M')} → "
              f"{end.strftime('%H:%M')} ({duration}h)")
    print(f"Total: {total_duration}h")


def test_single_day_course():
    """Curso que solo tiene un día a la semana."""
    data = [
        {'ID Curso': 100, 'Curso': 'Test Simple',
         'Inicio': '10/02/2026', 'Días': 'Lunes',
         'Hora inicio': '09:00', 'Hora fin': '12:00',
         'Horas': 9, 'Prioridad': 1}
    ]
    df = pd.DataFrame(data)
    sessions = generate_sessions_for_group(df)

    total = sum((e - s).total_seconds() / 3600 for s, e in sessions)
    assert abs(total - 9.0) < 0.01
    assert len(sessions) == 3  # 3 lunes × 3h = 9h
    print("✅ test_single_day_course pasó")


def test_empty_dataframe():
    """DataFrame vacío no debe crashear."""
    df = pd.DataFrame()
    sessions = generate_sessions_for_group(df)
    assert sessions == []
    print("✅ test_empty_dataframe pasó")


def test_conflict_detection():
    """Dos cursos en el mismo horario deben detectarse como conflicto."""
    sessions_a = [
        (datetime(2026, 2, 10, 12, 0), datetime(2026, 2, 10, 15, 0))
    ]
    sessions_b = [
        (datetime(2026, 2, 10, 14, 0), datetime(2026, 2, 10, 17, 0))
    ]
    sessions_c = [
        (datetime(2026, 2, 10, 15, 0), datetime(2026, 2, 10, 18, 0))
    ]

    assert has_conflict(sessions_a, sessions_b) == True, "Deben chocar"
    assert has_conflict(sessions_a, sessions_c) == False, "No deben chocar (borde)"
    print("✅ test_conflict_detection pasó")


def test_truncated_last_session():
    """La última sesión debe cortarse para no exceder las horas totales."""
    data = [
        {'ID Curso': 200, 'Curso': 'Test Corte',
         'Inicio': '10/02/2026', 'Días': 'Martes',
         'Hora inicio': '10:00', 'Hora fin': '15:00',
         'Horas': 7, 'Prioridad': 1}
    ]
    df = pd.DataFrame(data)
    sessions = generate_sessions_for_group(df)

    total = sum((e - s).total_seconds() / 3600 for s, e in sessions)
    assert abs(total - 7.0) < 0.01

    # Primera sesión: 5h, segunda sesión: 2h (cortada)
    assert len(sessions) == 2
    second_duration = (sessions[1][1] - sessions[1][0]).total_seconds() / 3600
    assert abs(second_duration - 2.0) < 0.01
    print("✅ test_truncated_last_session pasó")


if __name__ == "__main__":
    test_inference_group()
    test_single_day_course()
    test_empty_dataframe()
    test_conflict_detection()
    test_truncated_last_session()
    print("\n🎉 Todos los tests pasaron")