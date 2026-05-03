import pandas as pd
from datetime import datetime, timedelta, time
from ortools.sat.python import cp_model
import re
from model.config import NUM_ACCOUNTS, SOLVER_TIMEOUT, MAX_DAYS_AHEAD, LEXICOGRAPHIC_BASE

DAY_MAP = {
    'lun': 0, 'lunes': 0,
    'mar': 1, 'martes': 1,
    'mié': 2, 'mie': 2, 'miércoles': 2, 'miercoles': 2,
    'jue': 3, 'jueves': 3,
    'vie': 4, 'viernes': 4,
    'sáb': 5, 'sab': 5, 'sábado': 5, 'sabado': 5,
    'dom': 6, 'domingo': 6
}

PRIORITY_LEVELS_LIMIT = 9


def parse_time_24_simple(time_str):
    """Parses 'HH:MM' into time object."""
    return datetime.strptime(time_str.strip(), '%H:%M').time()


def parse_days_simple(days_str):
    """Parses 'Lunes, Martes y Viernes' into list of weekday integers."""
    days_str = days_str.lower()
    found_days = []
    for day_name, day_idx in DAY_MAP.items():
        if re.search(rf'\b{day_name}\b', days_str):
            found_days.append(day_idx)
    return sorted(list(set(found_days)))


def generate_sessions_for_group(rows):
    """
    Generates a list of (start_dt, end_dt) for a group of rows (same course).
    All rows share the same 'Horas' value (from the first row) and we accumulate
    sessions across all days/times defined in any row.
    """
    if rows.empty:
        return []

    hours_limit = float(rows.iloc[0]['Horas'])
    if hours_limit <= 0 or pd.isna(hours_limit):
        return []

    # Validar consistencia de horas dentro del grupo
    unique_hours = rows['Horas'].unique()
    if len(unique_hours) > 1:
        course_name = rows.iloc[0].get('Curso', 'desconocido')
        print(f"  Advertencia: Curso '{course_name}' tiene valores de Horas "
              f"inconsistentes: {unique_hours}. Usando el primero: {unique_hours[0]}")

    # Collect all day/time definitions
    schedules = []
    earliest_start = None

    for _, row in rows.iterrows():
        try:
            row_start_date = datetime.strptime(row['Inicio'].strip(), '%d/%m/%Y').date()
        except ValueError:
            try:
                row_start_date = datetime.strptime(row['Inicio'].strip(), '%Y-%m-%d').date()
            except ValueError:
                print(f"  Error: Formato de fecha no reconocido: '{row['Inicio']}'")
                continue

        if earliest_start is None or row_start_date < earliest_start:
            earliest_start = row_start_date

        days = parse_days_simple(row['Días'])
        if not days:
            print(f"  Advertencia: No se reconocieron días en '{row['Días']}' "
                  f"para curso '{rows.iloc[0].get('Curso', 'desconocido')}'")
            continue

        try:
            s_time = parse_time_24_simple(row['Hora inicio'])
            e_time = parse_time_24_simple(row['Hora fin'])
        except ValueError as e:
            print(f"  Error parseando hora para curso "
                  f"'{rows.iloc[0].get('Curso', 'desconocido')}': {e}")
            continue

        schedules.append({
            'days': days,
            'start': s_time,
            'end': e_time
        })

    if not schedules or earliest_start is None:
        return []

    sessions = []
    accumulated_hours = 0.0
    current_date = earliest_start
    max_date = earliest_start + timedelta(days=MAX_DAYS_AHEAD)

    while accumulated_hours < hours_limit and current_date < max_date:
        wd = current_date.weekday()
        for sch in schedules:
            if wd in sch['days']:
                s_start = datetime.combine(current_date, sch['start'])
                s_end = datetime.combine(current_date, sch['end'])

                duration = (s_end - s_start).total_seconds() / 3600.0
                if duration <= 0:
                    continue

                if accumulated_hours + duration > hours_limit:
                    remaining = hours_limit - accumulated_hours
                    s_end = s_start + timedelta(hours=remaining)
                    duration = remaining

                sessions.append((s_start, s_end))
                accumulated_hours += duration

                if accumulated_hours >= hours_limit:
                    break
        current_date += timedelta(days=1)

    return sessions


def has_conflict(sessions1, sessions2):
    """
    Detecta solapamiento entre dos listas de sesiones.
    Ordena ambas listas y usa two-pointer para O(n log n + m log m).
    """
    if not sessions1 or not sessions2:
        return False

    s1_sorted = sorted(sessions1, key=lambda x: x[0])
    s2_sorted = sorted(sessions2, key=lambda x: x[0])

    i, j = 0, 0
    while i < len(s1_sorted) and j < len(s2_sorted):
        s1_start, s1_end = s1_sorted[i]
        s2_start, s2_end = s2_sorted[j]

        if s1_start < s2_end and s2_start < s1_end:
            return True

        if s1_end <= s2_start:
            i += 1
        else:
            j += 1

    return False


def solve_schedule(df):
    """
    Main solver. Groups courses by ID first.
    """
    grouped = df.groupby(['ID Curso', 'Curso', 'Prioridad'])

    courses_to_solve = []
    for (cid, cname, prio), group_df in grouped:
        sessions = generate_sessions_for_group(group_df)
        courses_to_solve.append({
            'id': cid,
            'name': cname,
            'priority': int(prio),
            'sessions': sessions
        })

    num_courses = len(courses_to_solve)
    num_accounts = NUM_ACCOUNTS

    if not courses_to_solve:
        return {f'account{a+1}': [] for a in range(num_accounts)} | {'unassigned': [], 'conflicts': []}

    # Build model
    model = cp_model.CpModel()
    x = {}
    for i in range(num_courses):
        for a in range(num_accounts):
            x[i, a] = model.NewBoolVar(f'x_{i}_{a}')

    y = [model.NewBoolVar(f'y_{i}') for i in range(num_courses)]

    for i in range(num_courses):
        model.Add(sum(x[i, a] for a in range(num_accounts)) == y[i])

    # Build conflicts and add constraints
    conflicts_found = []
    for i in range(num_courses):
        for j in range(i + 1, num_courses):
            if has_conflict(courses_to_solve[i]['sessions'], courses_to_solve[j]['sessions']):
                conflicts_found.append((i, j))
                for a in range(num_accounts):
                    model.Add(x[i, a] + x[j, a] <= 1)

    # Maximize lexicographically by priority
    max_p = max(c['priority'] for c in courses_to_solve)

    if max_p > PRIORITY_LEVELS_LIMIT:
        print(f"Advertencia: {max_p} niveles de prioridad detectados. "
              f"Reduciendo base para evitar overflow.")
        base = max(2, num_courses + 1)
    else:
        base = LEXICOGRAPHIC_BASE

    objective_terms = []
    for i in range(num_courses):
        prio = courses_to_solve[i]['priority']
        weight = base ** (max_p - prio)
        objective_terms.append(y[i] * weight)

    model.Maximize(sum(objective_terms))

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVER_TIMEOUT
    solver.parameters.log_search_progress = False
    status = solver.Solve(model)

    if status == cp_model.INFEASIBLE:
        print("Error: El modelo es infactible. Revisa los datos de entrada.")
        return {f'account{a+1}': [] for a in range(num_accounts)} | {'unassigned': [], 'conflicts': []}

    if status == cp_model.MODEL_INVALID:
        print("Error: El modelo es inválido.")
        return {f'account{a+1}': [] for a in range(num_accounts)} | {'unassigned': [], 'conflicts': []}

    results = {f'account{a+1}': [] for a in range(num_accounts)} | {'unassigned': []}

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        for i in range(num_courses):
            info = {
                'id': courses_to_solve[i]['id'],
                'name': courses_to_solve[i]['name'],
                'priority': courses_to_solve[i]['priority']
            }
            assigned = False
            for a in range(num_accounts):
                if solver.Value(x[i, a]):
                    results[f'account{a+1}'].append(info)
                    assigned = True
                    break
            if not assigned:
                results['unassigned'].append(info)

    # Agregar conflictos al resultado
    results['conflicts'] = [
        {
            'course_a': courses_to_solve[i]['name'],
            'course_b': courses_to_solve[j]['name']
        }
        for i, j in conflicts_found
    ]

    return results