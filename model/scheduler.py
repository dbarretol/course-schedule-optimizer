import pandas as pd
from datetime import datetime, timedelta, time
from ortools.sat.python import cp_model
import re

DAY_MAP = {
    'lun': 0, 'lunes': 0,
    'mar': 1, 'martes': 1,
    'mié': 2, 'mie': 2, 'miércoles': 2, 'miercoles': 2,
    'jue': 3, 'jueves': 3,
    'vie': 4, 'viernes': 4,
    'sáb': 5, 'sab': 5, 'sábado': 5, 'sabado': 5,
    'dom': 6, 'domingo': 6
}

def parse_time_24(time_str):
    """Parses '19:00' into time object."""
    return datetime.strptime(time_str.strip(), '%H:%M').time()

def parse_complex_horario(horario_str):
    """
    Parses strings like:
    - 'Lun, Mar, Vie 19:00–22:00'
    - 'Mar 12:00–15:00, Jue 12:00–17:00'
    - 'Sábado 09:00–12:00'
    - 'Mié y Jue 16:00–19:00'
    Returns a list of dictionaries: [{'days': [0, 1, 4], 'start': time(19,0), 'end': time(22,0)}, ...]
    """
    parts = [p.strip() for p in horario_str.split(',')]
    schedules = []
    
    # Sometimes days are separated by 'y' or ',' but they share the same time
    # e.g., 'Lun y Jue 16:00–19:00'
    # We need to find the time pattern in each part or look ahead
    
    current_days = []
    for part in parts:
        # Check for time pattern 'HH:MM–HH:MM' (note the en-dash or hyphen)
        match = re.search(r'(\d{1,2}:\d{2})[–-](\d{1,2}:\d{2})', part)
        
        # Extract days mentioned in this part
        found_days = []
        for day_name, day_idx in DAY_MAP.items():
            # Use word boundaries to avoid matching 'mar' in 'martes' twice incorrectly
            # or matching parts of other words.
            if re.search(rf'\b{day_name}\b', part.lower()):
                found_days.append(day_idx)
        
        if match:
            # We found a time, so these days (and any accumulated previous days)
            # belong to this time slot.
            all_days = sorted(list(set(current_days + found_days)))
            start_t = parse_time_24(match.group(1))
            end_t = parse_time_24(match.group(2))
            schedules.append({'days': all_days, 'start': start_t, 'end': end_t})
            current_days = []
        else:
            # No time found, accumulate days for the next time slot found
            current_days.extend(found_days)
            
    return schedules

def generate_sessions(row):
    """Generates a list of (start_dt, end_dt) for a course until total hours are met."""
    start_date = datetime.strptime(row['Inicio'].strip(), '%Y-%m-%d').date()
    total_hours = float(row['Horas'])
    schedules = parse_complex_horario(row['Horario'])
    
    sessions = []
    accumulated_hours = 0.0
    current_date = start_date
    
    # Limit search to 1 year to avoid infinite loops if data is weird
    max_date = start_date + timedelta(days=365)
    
    while accumulated_hours < total_hours and current_date < max_date:
        wd = current_date.weekday()
        # Find if any schedule applies to this weekday
        for sch in schedules:
            if wd in sch['days']:
                s_start = datetime.combine(current_date, sch['start'])
                s_end = datetime.combine(current_date, sch['end'])
                
                # Duration in hours
                duration = (s_end - s_start).total_seconds() / 3600.0
                
                if accumulated_hours + duration > total_hours:
                    # Cap the last session
                    remaining = total_hours - accumulated_hours
                    s_end = s_start + timedelta(hours=remaining)
                    duration = remaining
                
                sessions.append((s_start, s_end))
                accumulated_hours += duration
                
                if accumulated_hours >= total_hours:
                    break
                    
        current_date += timedelta(days=1)
    
    return sessions

def has_conflict(sessions1, sessions2):
    """Checks if two sets of sessions overlap."""
    for s1_start, s1_end in sessions1:
        for s2_start, s2_end in sessions2:
            if s1_start < s2_end and s2_start < s1_end:
                return True
    return False

def solve_schedule(df):
    """Main solver using CP-SAT."""
    courses = df.to_dict('records')
    for i, course in enumerate(courses):
        course['id_solver'] = i
        # Use priority 1 as default if not provided, or extract from elsewhere
        # The prompt doesn't specify new priorities, so I'll assume equal or 
        # try to look for Priority in the data (but cursos.txt doesn't have it)
        # Assuming Priority 1 for all for now or 1 if not present.
        course['PRIORIDAD'] = course.get('PRIORIDAD', 1)
        course['sessions'] = generate_sessions(course)
    
    num_courses = len(courses)
    num_accounts = 2
    
    model = cp_model.CpModel()
    x = {}
    for i in range(num_courses):
        for a in range(num_accounts):
            x[i, a] = model.NewBoolVar(f'x_{i}_{a}')
            
    y = [model.NewBoolVar(f'y_{i}') for i in range(num_courses)]
    
    for i in range(num_courses):
        model.Add(sum(x[i, a] for a in range(num_accounts)) == y[i])
        
    for i in range(num_courses):
        for j in range(i + 1, num_courses):
            if has_conflict(courses[i]['sessions'], courses[j]['sessions']):
                for a in range(num_accounts):
                    model.Add(x[i, a] + x[j, a] <= 1)
                    
    # Optimization: Maximize number of courses (equal priority if not specified)
    # If priorities were available, we'd use them.
    max_p = max(c['PRIORIDAD'] for c in courses)
    objective_terms = []
    for i in range(num_courses):
        prio = courses[i]['PRIORIDAD']
        weight = 10 ** (max_p - prio)
        objective_terms.append(y[i] * weight)
        
    model.Maximize(sum(objective_terms))
    
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    results = {'account1': [], 'account2': [], 'unassigned': []}
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        for i in range(num_courses):
            info = {
                'id': courses[i].get('ID Curso', i),
                'name': courses[i]['Curso'],
                'priority': courses[i]['PRIORIDAD']
            }
            assigned = False
            for a in range(num_accounts):
                if solver.Value(x[i, a]):
                    results[f'account{a+1}'].append(info)
                    assigned = True
                    break
            if not assigned:
                results['unassigned'].append(info)
                
    return results
