import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def check_users():
    print("Connecting to database to check users...")
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=os.getenv("DB_PORT", "5432")
        )
        cur = conn.cursor()
        
        cur.execute("SELECT column_name, data_type, character_maximum_length FROM information_schema.columns WHERE table_name = 'registros_usuarios' AND column_name = 'rut';")
        info = cur.fetchone()
        print(f"Column Info for 'rut': {info}")
        
        cur.execute("SELECT rut, nombre_completo FROM registros_usuarios LIMIT 5;")
        rows = cur.fetchall()
        
        print(f"Found {len(rows)} users:")
        for row in rows:
            print(f"- RUT: '{row[0]}', Name: {row[1]}")
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_users()
