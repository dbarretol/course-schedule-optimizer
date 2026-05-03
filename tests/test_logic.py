import pandas as pd
import os
import sys
from datetime import datetime

# Añadir el directorio raíz al path para poder importar el modelo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from model.scheduler import (
    generate_sessions_for_group, has_conflict, solve_schedule,
    parse_days_simple, parse_time_24_simple
)


def test_parsing_helpers():
    """Prueba las funciones auxiliares de parseo."""
    # Días
    assert parse_days_simple("Lunes y Miércoles") == [0, 2]
    assert parse_days_simple("mar, JUE, vie") == [1, 3, 4]
    assert parse_days_simple("día desconocido") == []

    # Horas
    from datetime import time
    assert parse_time_24_simple("09:00") == time(9, 0)
    assert parse_time_24_simple(" 23:59 ") == time(23, 59)
    print("✅ test_parsing_helpers pasó")


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


def test_solver_priority_and_conflict():
    """Prueba el solver: prioridad, múltiples cuentas y conflictos."""
    data = [
        # Curso A y B chocan. A tiene más prioridad.
        {'ID Curso': 1, 'Curso': 'Curso A (Alta Prio)',
         'Inicio': '10/02/2026', 'Días': 'Lunes',
         'Hora inicio': '09:00', 'Hora fin': '12:00',
         'Horas': 3, 'Prioridad': 1},
        {'ID Curso': 2, 'Curso': 'Curso B (Baja Prio)',
         'Inicio': '10/02/2026', 'Días': 'Lunes',
         'Hora inicio': '10:00', 'Hora fin': '13:00',
         'Horas': 3, 'Prioridad': 2},
        # Curso C no choca con nadie.
        {'ID Curso': 3, 'Curso': 'Curso C',
         'Inicio': '10/02/2026', 'Días': 'Martes',
         'Hora inicio': '09:00', 'Hora fin': '12:00',
         'Horas': 3, 'Prioridad': 1},
    ]
    df = pd.DataFrame(data)
    results = solve_schedule(df)

    # Verificaciones básicas
    assigned_ids = []
    for acc in ['account1', 'account2']:
        assigned_ids.extend([c['id'] for c in results[acc]])

    # El Curso A (Prio 1) DEBE estar asignado.
    assert 1 in assigned_ids, "Curso A debe estar asignado por su alta prioridad"
    # El Curso C (Prio 1) DEBE estar asignado.
    assert 3 in assigned_ids, "Curso C debe estar asignado (no tiene conflictos)"

    # Verificar que A y B no están en la misma cuenta si ambos se asignaron
    acc1_ids = [c['id'] for c in results['account1']]
    acc2_ids = [c['id'] for c in results['account2']]

    if 1 in acc1_ids and 2 in acc1_ids:
        assert False, "Curso A y B chocan y no pueden estar en la misma cuenta"
    if 1 in acc2_ids and 2 in acc2_ids:
        assert False, "Curso A y B chocan y no pueden estar en la misma cuenta"

    # Con 2 cuentas, A, B y C deberían caber (A y C en una, B en otra)
    assert len(assigned_ids) == 3, f"Se esperaban 3 cursos asignados, hay {len(assigned_ids)}"

    print("✅ test_solver_priority_and_conflict pasó")


def test_priority_overflow():
    """Prueba que el solver maneje niveles de prioridad > 9 sin explotar."""
    data = [
        {'ID Curso': 1, 'Curso': 'P1', 'Inicio': '10/02/2026', 'Días': 'Lunes',
         'Hora inicio': '09:00', 'Hora fin': '10:00', 'Horas': 1, 'Prioridad': 1},
        {'ID Curso': 2, 'Curso': 'P15', 'Inicio': '10/02/2026', 'Días': 'Lunes',
         'Hora inicio': '10:00', 'Hora fin': '11:00', 'Horas': 1, 'Prioridad': 15},
    ]
    df = pd.DataFrame(data)
    # No debería lanzar excepción de overflow (potencia demasiado grande)
    results = solve_schedule(df)
    assert len(results['account1']) + len(results['account2']) > 0
    print("✅ test_priority_overflow pasó")


if __name__ == "__main__":
    test_parsing_helpers()
    test_inference_group()
    test_single_day_course()
    test_empty_dataframe()
    test_conflict_detection()
    test_truncated_last_session()
    test_solver_priority_and_conflict()
    test_priority_overflow()
    print("\n🎉 Todos los tests pasaron")