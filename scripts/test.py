import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
import json

load_dotenv()

query = """
    SELECT 
        COALESCE(l.motivo_consulta, 'Sin Motivo / No Especificado') as "Motivo de Consulta Clínico",
        COUNT(*) as "Cantidad de Casos",
        ROUND(COUNT(*) * 100.0 / NULLIF((SELECT COUNT(*) FROM logs_atenciones la JOIN registros_usuarios ru ON la.rut_paciente=ru.rut WHERE 1=1 AND la.fecha_registro >= %s::date), 0), 2)::float as "Incidencia (%)"
    FROM logs_atenciones l
    JOIN registros_usuarios r ON l.rut_paciente = r.rut
    WHERE 1=1 AND l.fecha_registro >= %s::date
    GROUP BY l.motivo_consulta ORDER BY "Cantidad de Casos" DESC LIMIT 20
"""

try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=os.getenv("DB_PORT", "5432")
    )
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # testing with a parameter
        cur.execute(query, ('2023-01-01', '2023-01-01'))
        rows = cur.fetchall()
        print(json.dumps([dict(r) for r in rows]))
except Exception as e:
    import traceback
    traceback.print_exc()
