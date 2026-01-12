import pandas as pd
from datetime import datetime, timedelta
from ortools.sat.python import cp_model
import re

DAY_MAP = {
    'lunes': 0,
    'martes': 1,
    'miércoles': 2,
    'miercoles': 2,
    'jueves': 3,
    'viernes': 4,
    'sábado': 5,
    'sabado': 5,
    'domingo': 6
}

def parse_time(time_str):
    """Parses '6:00 p.m.' or '11:00 a.m.' into time object."""
    time_str = time_str.strip().lower().replace('.', '')
    # Handle formats like '6:00 pm' or '11:00 am'
    return datetime.strptime(time_str, '%I:%M %p').time()

def parse_days(days_str):
    """Parses 'Lunes, Miércoles y Viernes' into list of weekday integers."""
    days_str = days_str.lower()
    found_days = []
    for day_name, day_idx in DAY_MAP.items():
        if day_name in days_str:
            found_days.append(day_idx)
    return sorted(list(set(found_days)))

def generate_sessions(row):
    """Generates a list of (start_dt, end_dt) for a course."""
    start_date = datetime.strptime(row['FECHA_INICIO'].strip(), '%d/%m/%Y').date()
    days = parse_days(row['DIAS'])
    start_time = parse_time(row['HORA_INICIO'])
    end_time = parse_time(row['HORA_FIN'])
    n_sessions = int(float(row['N_SESIONES']))
    
    sessions = []
    current_date = start_date
    while len(sessions) < n_sessions:
        if current_date.weekday() in days:
            session_start = datetime.combine(current_date, start_time)
            session_end = datetime.combine(current_date, end_time)
            sessions.append((session_start, session_end))
        current_date += timedelta(days=1)
    
    return sessions

def has_conflict(sessions1, sessions2):
    """Checks if two sets of sessions overlap."""
    for s1_start, s1_end in sessions1:
        for s2_start, s2_end in sessions2:
            # Overlap if: startA < endB and startB < endA
            if s1_start < s2_end and s2_start < s1_end:
                return True
    return False

def solve_schedule(df):
    """Main solver using CP-SAT."""
    courses = df.to_dict('records')
    for i, course in enumerate(courses):
        course['id'] = i
        course['sessions'] = generate_sessions(course)
    
    num_courses = len(courses)
    num_accounts = 2
    
    model = cp_model.CpModel()
    
    # x[i, a] = 1 if course i is in account a
    x = {}
    for i in range(num_courses):
        for a in range(num_accounts):
            x[i, a] = model.NewBoolVar(f'x_{i}_{a}')
            
    # y[i] = 1 if course i is taken in any account
    y = [model.NewBoolVar(f'y_{i}') for i in range(num_courses)]
    
    # Each course at most one account
    for i in range(num_courses):
        model.Add(sum(x[i, a] for a in range(num_accounts)) == y[i])
        
    # Conflicts: no overlap within the same account
    conflicts = []
    for i in range(num_courses):
        for j in range(i + 1, num_courses):
            if has_conflict(courses[i]['sessions'], courses[j]['sessions']):
                conflicts.append((i, j))
                for a in range(num_accounts):
                    model.Add(x[i, a] + x[j, a] <= 1)
                    
    # Lexicographic objective: Priority 1 > Priority 2 > Priority 3 > Priority 4
    # We use large weights
    priorities = sorted(df['PRIORIDAD'].unique())
    # Max weight needed roughly: sum of courses in lower priority + 1
    # To be safe, let's use powers of 10 or just a large enough gap
    # Weight_p = 100^(max_priority - p)
    max_p = max(priorities)
    objective_terms = []
    for i in range(num_courses):
        prio = courses[i]['PRIORIDAD']
        weight = 10 ** (max_p - prio)
        objective_terms.append(y[i] * weight)
        
    model.Maximize(sum(objective_terms))
    
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    results = {
        'account1': [],
        'account2': [],
        'unassigned': []
    }
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        for i in range(num_courses):
            info = {
                'name': courses[i]['CURSO'],
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
