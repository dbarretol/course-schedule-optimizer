import logging

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scheduler.log', encoding='utf-8')
    ]
)

# archivo de entrada
INPUT_FILE = 'data/9no_PIT.csv'

# Número de cuentas disponibles
NUM_ACCOUNTS = 2

# Timeout del solver en segundos
SOLVER_TIMEOUT = 60.0

# Máximo de días hacia adelante para generar sesiones
MAX_DAYS_AHEAD = 365

# Base para pesos lexicográficos
LEXICOGRAPHIC_BASE = 100

# Columnas requeridas en el CSV
REQUIRED_COLUMNS = [
    'ID Curso', 'Curso', 'Inicio', 'Días',
    'Hora inicio', 'Hora fin', 'Horas', 'Prioridad'
]
