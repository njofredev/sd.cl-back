import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        port=os.getenv("DB_PORT", "5432")
    )
    cur = conn.cursor()

    print("Borrando logs de atenciones...")
    cur.execute("DELETE FROM logs_atenciones;")
    
    print("Borrando todos los pacientes...")
    cur.execute("DELETE FROM registros_usuarios;")
    
    print("Borrando usuarios institucionales (excepto admin@sanad.cl)...")
    cur.execute("DELETE FROM usuarios_institucionales WHERE email != 'admin@sanad.cl';")

    conn.commit()
    print("✅ Base de datos reiniciada exitosamente. Solo quedó el admin general.")
except Exception as e:
    if 'conn' in locals():
        conn.rollback()
    print("❌ Error al reiniciar la base de datos:", e)
finally:
    if 'cur' in locals(): cur.close()
    if 'conn' in locals(): conn.close()
