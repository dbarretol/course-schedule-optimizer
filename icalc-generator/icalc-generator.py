import pandas as pd
import os
import sys

# Add the parent directory to sys.path to reuse scheduler logic if needed, 
# but for standalone simplicity in icalc-generator, I'll copy the core logic here.
from datetime import datetime, timedelta, time
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
    return datetime.strptime(time_str.strip(), '%H:%M').time()

def parse_days(days_str):
    days_str = days_str.lower()
    found_days = []
    for day_name, day_idx in DAY_MAP.items():
        if re.search(rf'\b{day_name}\b', days_str):
            found_days.append(day_idx)
    return sorted(list(set(found_days)))

def generate_sessions_for_group(rows):
    if rows.empty:
        return []
    
    hours_limit = float(rows.iloc[0]['Horas'])
    schedules = []
    earliest_start = None
    
    for _, row in rows.iterrows():
        try:
            row_start_date = datetime.strptime(row['Inicio'].strip(), '%d/%m/%Y').date()
        except ValueError:
            row_start_date = datetime.strptime(row['Inicio'].strip(), '%Y-%m-%d').date()
            
        if earliest_start is None or row_start_date < earliest_start:
            earliest_start = row_start_date
            
        days = parse_days(row['Días'])
        s_time = parse_time_24(row['Hora inicio'])
        e_time = parse_time_24(row['Hora fin'])
        schedules.append({'days': days, 'start': s_time, 'end': e_time})
        
    sessions = []
    accumulated_hours = 0.0
    current_date = earliest_start
    max_date = earliest_start + timedelta(days=365)
    
    while accumulated_hours < hours_limit and current_date < max_date:
        wd = current_date.weekday()
        for sch in schedules:
            if wd in sch['days']:
                s_start = datetime.combine(current_date, sch['start'])
                s_end = datetime.combine(current_date, sch['end'])
                
                duration = (s_end - s_start).total_seconds() / 3600.0
                if duration <= 0: continue
                
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

def main():
    input_file = 'COURSES.csv'
    output_file = 'SESSIONS.csv'
    
    if not os.path.exists(input_file):
        print(f"Error: No se encuentra {input_file}")
        return

    try:
        df = pd.read_csv(input_file, sep=';', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(input_file, sep=';', encoding='latin-1')

    # Data cleaning
    df['Horas'] = pd.to_numeric(df['Horas'], errors='coerce')
    df = df.dropna(subset=['Curso', 'Horas'])
    
    # Group by ID and Name to handle multi-slot courses
    # Use 'ID Curso' if present, else just 'Curso'
    group_col = 'ID Curso' if 'ID Curso' in df.columns else 'Curso'
    grouped = df.groupby([group_col, 'Curso'])
    
    all_sessions_data = []
    
    for (cid, cname), group_df in grouped:
        sessions = generate_sessions_for_group(group_df)
        
        for i, (start, end) in enumerate(sessions):
            all_sessions_data.append({
                'Course Name': cname,
                'Session Number': i + 1,
                'Date': start.strftime('%d/%m/%Y'),
                'Start Hour': start.strftime('%H:%M'),
                'End Hour': end.strftime('%H:%M')
            })
            
    output_df = pd.DataFrame(all_sessions_data)
    
    # Save to CSV
    output_df.to_csv(output_file, index=False, sep=',', encoding='utf-8-sig')
    print(f"Éxito: Se han generado {len(output_df)} sesiones en {output_file}")

if __name__ == "__main__":
    main()
