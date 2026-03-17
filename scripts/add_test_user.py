import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def add_user(rut, nombre):
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=os.getenv("DB_PORT", "5432")
        )
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO registros_usuarios (rut, nombre_completo, email, sede) VALUES (%s, %s, %s, %s) ON CONFLICT (rut) DO NOTHING",
            (rut, nombre, 'pruebas@sanad.cl', 'Providencia')
        )
        conn.commit()
        print(f"User {rut} added successfully.")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    add_user('19258679-8', 'Usuario Pruebas')
