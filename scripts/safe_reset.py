import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def safe_reset():
    conn = None
    cur = None
    try:
        print("Connecting to database for safe reset...")
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASS'),
            port=os.getenv('DB_PORT', '5432')
        )
        cur = conn.cursor()
        
        # 1. Clear attention logs
        print("Cleaning logs_atenciones table...")
        cur.execute("DELETE FROM logs_atenciones;")
        
        # 2. Reset session counters
        print("Resetting sessions counter to 0 in registros_usuarios...")
        cur.execute("UPDATE registros_usuarios SET reservas_realizadas = 0;")
        
        conn.commit()
        print("✅ Safe reset successful.")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Error: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    safe_reset()
