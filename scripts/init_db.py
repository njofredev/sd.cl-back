import psycopg2
import os
from dotenv import load_dotenv
import sys

# Load environment variables
load_dotenv()

def init_db():
    print("Connecting to database...")
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=os.getenv("DB_PORT", "5432")
        )
        cur = conn.cursor()
        
        print("Creating tables...")
        # Create users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS registros_usuarios (
                id SERIAL PRIMARY KEY,
                rut VARCHAR(20) UNIQUE NOT NULL,
                nombre_completo VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                sede VARCHAR(100),
                reservas_realizadas INT DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Create logs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS logs_atenciones (
                id SERIAL PRIMARY KEY,
                rut_paciente VARCHAR(20) NOT NULL,
                nombre_especialista VARCHAR(255),
                motivo_consulta TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (rut_paciente) REFERENCES registros_usuarios (rut)
            );
            
            -- Nuevas tablas institucionales
            CREATE TABLE IF NOT EXISTS usuarios_institucionales (
                id SERIAL PRIMARY KEY,
                rut_institucion VARCHAR(15),
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                nombre VARCHAR(100),
                apellido VARCHAR(100),
                rol VARCHAR(50) NOT NULL,
                sede_id INT,
                institucion_id INT
            );

            CREATE TABLE IF NOT EXISTS profesionales (
                id SERIAL PRIMARY KEY,
                prof_id_ext VARCHAR(50) UNIQUE,
                nombre VARCHAR(100) NOT NULL,
                apellido VARCHAR(100) NOT NULL,
                titulo VARCHAR(100),
                universidad VARCHAR(255),
                especialidad VARCHAR(255),
                registro VARCHAR(255),
                descripcion TEXT,
                genero VARCHAR(20),
                tipo_terapia TEXT[],
                grupo_etario TEXT[],
                foto TEXT,
                link TEXT,
                sede_id VARCHAR(50),
                institucion_id VARCHAR(50),
                disponibilidad VARCHAR(100),
                horarios TEXT[]
            );
        """)
        
        # Insert a test user if not exists
        print("Inserting multiple test users...")
        cur.execute("""
            INSERT INTO registros_usuarios (rut, nombre_completo, email, sede, reservas_realizadas)
            VALUES 
            ('18765432-1', 'Camila Reyes', 'creyes@example.com', 'Providencia', 0),
            ('19123456-7', 'Juan Pérez', 'jperez@example.com', 'Santiago Centro', 2),
            ('17987654-3', 'María López', 'mlopez@example.com', 'Las Condes', 4)
            ON CONFLICT (rut) DO NOTHING;
        """)

        # Insert some test logs for the user Camila
        cur.execute("SELECT COUNT(*) FROM logs_atenciones WHERE rut_paciente = '18765432-1'")
        count = cur.fetchone()[0]
        if count == 0:
            print("Inserting test attendance logs for Camila...")
            cur.execute("""
                INSERT INTO logs_atenciones (rut_paciente, nombre_especialista, motivo_consulta)
                VALUES 
                ('18765432-1', 'Dra. María González', 'Evaluación inicial'),
                ('18765432-1', 'Dra. María González', 'Seguimiento psicológico');
            """)
            
        # Insert some test logs for the user Juan
        cur.execute("SELECT COUNT(*) FROM logs_atenciones WHERE rut_paciente = '19123456-7'")
        count2 = cur.fetchone()[0]
        if count2 == 0:
            print("Inserting test attendance logs for Juan...")
            cur.execute("""
                INSERT INTO logs_atenciones (rut_paciente, nombre_especialista, motivo_consulta)
                VALUES 
                ('19123456-7', 'Dr. Alberto Ruiz', 'Trastorno de ansiedad'),
                ('19123456-7', 'Dr. Alberto Ruiz', 'Control mensual');
            """)

        # Insert institutional test users
        print("Inserting institutional test users...")
        cur.execute("""
            INSERT INTO usuarios_institucionales (rut_institucion, email, password_hash, nombre, apellido, rol, sede_id, institucion_id)
            VALUES 
            ('99.999.999-9', 'admin@sanad.cl', 'admin123', 'Diego', 'Martínez', 'admin_sistema', NULL, NULL),
            ('76.100.200-3', 'jperez@uandina.cl', 'matriz123', 'Juan', 'Pérez Sánchez', 'admin_casa_matriz', NULL, 1),
            ('76.100.200-3', 'mlopez@uandina.cl', 'sede123', 'Marcela', 'López', 'admin_sede', 1, 1),
            ('76.100.200-3', 'c.gonzalez@uandina.cl', 'clinico123', 'Carolina', 'González', 'clinico', 1, 1)
            ON CONFLICT (email) DO NOTHING;
        """)

        # Insert professionals
        print("Inserting professionals...")
        profesionales_data = [
            ('prof-001', 'María Carolina', 'Fones', 'Psicóloga', 'Universidad del Desarrollo', 'Psicología Clínica', 'Registro N°287422 Superintendencia de Salud', 'Diplomado en Psiquiatría y Psicología Forense. Diplomado en Psicoanálisis Relacional. Terapeuta en Adicciones.', 'Mujer', ['Individual', 'Cuidadores / familiares'], ['Adultos jóvenes (18–25)', 'Adultos (26–64)', 'Adultos mayores (65+)'], 'https://cdn.prod.website-files.com/68f677b74ad8262f24254c20/69541fb945ca375f5462fcb8_PsicologaFoto-Carolina_Fones_Caballero.jpeg', 'https://beta-sacmed.novacaribe.com/ReservaOnline/11590/parameters/2494/6157/6c6d1b27-8f36-4342-aa17-6936e6d0f00f', 'sede-001', 'inst-001', 'Lun-Vie', ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00']),
            ('prof-002', 'Francisca', 'Rojas Jamet', 'Psicóloga', 'Universidad de las Américas', 'Psicología Clínica y Educacional', 'Registro N°687225 Superintendencia de Salud', 'Formación en Psicología y Pedagogía. Especialista en TEA y diversidad. Atención empática y sin juicios.', 'Mujer', ['Individual', 'Familias', 'Personas LGBTQ+', 'Personas neurodivergentes'], ['Niños (0–12)', 'Adolescentes (13–17)', 'Adultos jóvenes (18–25)'], 'https://cdn.prod.website-files.com/68f677b74ad8262f24254c20/69541fb98505845a74513f03_Psico%CC%81logaFoto-Francisca_Rojas_Jamet.jpeg', 'https://beta-sacmed.novacaribe.com/ReservaOnline/11590/parameters/2494/6157/a8def84b-70e0-4748-951d-9567e1f82ab4', 'sede-001', 'inst-001', 'Lun-Jue', ['09:00', '10:00', '11:00', '15:00', '16:00']),
            ('prof-003', 'Jose Luis', 'Escalona Muñoz', 'Psicólogo', 'Universidad Viña del Mar', 'Neuropsicología y Psicología Clínica', 'Registro N°410845 Superintendencia de Salud', 'Magister en Neurociencias U. de Chile. Evaluación neuropsicológica, detección de demencias y TDAH. Abordaje sistémico constructivista.', 'Hombre', ['Individual', 'Parejas', 'Personas neurodivergentes'], ['Adultos jóvenes (18–25)', 'Adultos (26–64)', 'Adultos mayores (65+)'], 'https://cdn.prod.website-files.com/68f677b74ad8262f24254c20/69541fb98d8fb9b839c8f61f_Psico%CC%81logoFoto-Jose_Escalona_Mun%CC%83oz.jpeg', 'https://beta-sacmed.novacaribe.com/ReservaOnline/11590/parameters/2494/6157/0ecb63e2-acd8-4061-8012-bc7bdfbb1574', 'sede-001', 'inst-001', 'Mar-Sáb', ['10:00', '11:00', '12:00', '14:00', '15:00']),
            ('prof-004', 'Marcela', 'Salinas Abarca', 'Psicóloga', 'Universidad de Chile', 'Psicología Sistémica', 'Registro N°882788 Superintendencia de Salud', 'Acompaño a adolescentes y adultos, ofreciendo un espacio seguro, cercano y respetuoso desde enfoque sistémico.', 'Mujer', ['Individual', 'Parejas', 'Familias', 'Personas LGBTQ+'], ['Adolescentes (13–17)', 'Adultos jóvenes (18–25)', 'Adultos (26–64)'], 'https://cdn.prod.website-files.com/68f677b74ad8262f24254c20/6954298a79ffd2dfa2dffdb8_Psico%CC%81logaFoto_Marcela_Salinas_Abarca.jpg', 'https://beta-sacmed.novacaribe.com/ReservaOnline/11590/parameters/2494/6157/397d4746-4fff-4f1c-8af5-31666be26530', 'sede-001', 'inst-001', 'Lun-Vie', ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00', '17:00']),
            ('prof-005', 'Carolina', 'Infante Aravena', 'Psicóloga', 'Universidad Diego Portales', 'Psicología Psicoanalítica', 'Registro N°99369 Superintendencia de Salud', '15 años de experiencia. Especializada en trastornos de ansiedad, ánimo, personalidad y estrés post traumático.', 'Mujer', ['Individual', 'Cuidadores / familiares', 'Personas LGBTQ+'], ['Adultos jóvenes (18–25)', 'Adultos (26–64)', 'Adultos mayores (65+)'], 'https://cdn.prod.website-files.com/68f677b74ad8262f24254c20/69541fb975de06dfc89dc5b2_Psico%CC%81logaFoto-Carolina_Infante_Aravena.jpeg', 'https://beta-sacmed.novacaribe.com/ReservaOnline/11590/parameters/2494/6157/8e5be992-3df8-48d0-acaf-9ded9ae9cd0c', 'sede-002', 'inst-001', 'Lun-Mié', ['10:00', '11:00', '12:00', '15:00', '16:00']),
            ('prof-006', 'Isabel', 'Morales Chabla', 'Psicóloga', 'Universidad de Chile', 'Psicología Humanista-Existencial', 'Registro N°882766 Superintendencia de Salud', 'Diplomado en Psicoterapia Humanista Existencial y Terapia Breve Centrada en Soluciones.', 'Mujer', ['Individual', 'Personas LGBTQ+'], ['Adultos jóvenes (18–25)', 'Adultos (26–64)', 'Adultos mayores (65+)'], 'https://cdn.prod.website-files.com/68f677b74ad8262f24254c20/69541fb99943a24358caf65d_Psico%CC%81logaFoto-Isabel_Morales_Chabla.jpeg', 'https://beta-sacmed.novacaribe.com/ReservaOnline/11590/parameters/2494/6157/22a1b15f-07a6-4c40-bada-778d897a1a68', 'sede-002', 'inst-001', 'Mar-Vie', ['09:00', '10:00', '14:00', '15:00', '16:00']),
            ('prof-007', 'Pablo', 'Martínez Zúñiga', 'Psicólogo', 'Universidad de la Serena', 'Psicología Cognitivo Contextual', 'Registro N°777486 Superintendencia de Salud', 'Psicoterapeuta online. Enfoque cognitivo contextual: equilibrar aceptación con cambio.', 'Hombre', ['Individual', 'Parejas', 'Personas LGBTQ+', 'Personas neurodivergentes'], ['Adolescentes (13–17)', 'Adultos jóvenes (18–25)', 'Adultos (26–64)'], 'https://cdn.prod.website-files.com/68f677b74ad8262f24254c20/69541fb9d0cdf907b2fd7d7d_Psico%CC%81logoFoto-Pablo_Marti%CC%81nez_Zu%CC%81n%CC%83iga.jpeg', 'https://beta-sacmed.novacaribe.com/ReservaOnline/11590/parameters/2494/6157/bfe2c5b9-23ec-49d6-83fe-9e15aa96de69', 'sede-001', 'inst-001', 'Lun-Vie', ['10:00', '11:00', '15:00', '16:00', '17:00']),
            ('prof-008', 'Karin', 'Renck Orellana', 'Psicóloga', 'Pontificia Universidad Católica de Chile', 'Psicoterapia Breve Sistémica', 'Registro N°268407 Superintendencia de Salud', 'Experta en psicoterapia breve sistémica: estrés, comunicación, relaciones, crisis vital, depresión, adicciones.', 'Mujer', ['Individual', 'Personas LGBTQ+', 'Pacientes forenses'], ['Adultos jóvenes (18–25)', 'Adultos (26–64)', 'Adultos mayores (65+)'], 'https://cdn.prod.website-files.com/68f677b74ad8262f24254c20/69541fb911e6c9fa27d6ed6c_PsicologaFoto-Karin_Renck_Orellana.jpeg', 'https://beta-sacmed.novacaribe.com/ReservaOnline/11590/parameters/2494/6157/deecb583-c649-47e5-9394-e6f20cf57c1f', 'sede-002', 'inst-001', 'Lun-Jue', ['09:00', '10:00', '11:00', '14:00', '15:00']),
            ('prof-009', 'Alejandro', 'Gunckel Barría', 'Psicólogo', 'Universidad Pedro de Valdivia', 'Psicología Clínica Integrativa', 'Registro N°287745 Superintendencia de Salud', '11+ años de experiencia. Enfoque integrativo, atención cálida, flexible y personalizada. Especialista en TEA y neurodivergencia.', 'Hombre', ['Individual', 'Personas neurodivergentes'], ['Adultos jóvenes (18–25)', 'Adultos (26–64)', 'Adultos mayores (65+)'], 'https://cdn.prod.website-files.com/68f677b74ad8262f24254c20/69541fb945ca375f5462fc9a_Psico%CC%81logoFoto-Alejandro_Gunkel_Garcia.jpeg', 'https://beta-sacmed.novacaribe.com/ReservaOnline/11590/parameters/2494/6157/4efddf64-a4ef-4067-a385-0c8740933e53', 'sede-003', 'inst-002', 'Mar-Sáb', ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00']),
            ('prof-010', 'Luna', 'Jara de Barca', 'Psicóloga', 'Universidad de Chile', 'Psicología Constructivista Cognitiva', 'Registro N°885058 Superintendencia de Salud', 'Diplomada constructivista cognitiva. Amplia experiencia: trastornos del ánimo, personalidad, conducta alimentaria, neurodivergencias.', 'Mujer', ['Individual', 'Parejas', 'Familias', 'Personas LGBTQ+', 'Personas neurodivergentes'], ['Adolescentes (13–17)', 'Adultos jóvenes (18–25)', 'Adultos (26–64)'], 'https://cdn.prod.website-files.com/68f677b74ad8262f24254c20/69541fb99c3700d08330f1b8_Psico%CC%81logaFoto-Luna_Jara_De_Barca.jpeg', 'https://beta-sacmed.novacaribe.com/ReservaOnline/11590/parameters/2494/6157/a73f0c2e-0eb2-46cf-af5b-a939cea40eb8', 'sede-001', 'inst-001', 'Lun-Vie', ['09:00', '10:00', '11:00', '12:00', '15:00', '16:00']),
            ('prof-011', 'Bryan', 'Paredes Ortíz', 'Psicólogo', 'Universidad de las Américas', 'Psicología Clínica y Educacional', 'Registro N°507914 Superintendencia de Salud', '8 años de experiencia, atención integrativa. Especializado en ansiedad, depresión, bullying, neurodiversidad.', 'Hombre', ['Individual', 'Familias', 'Personas LGBTQ+', 'Personas neurodivergentes'], ['Niños (0–12)', 'Adolescentes (13–17)', 'Adultos jóvenes (18–25)'], 'https://cdn.prod.website-files.com/68f677b74ad8262f24254c20/69541fb9a4057bf2b9f09e99_PsicologoFoto-Bryan_Paredes_Ortiz.jpeg', 'https://beta-sacmed.novacaribe.com/ReservaOnline/11590/parameters/2494/6157/fba2fb2d-d9cc-4457-913b-110df86d9966', 'sede-003', 'inst-002', 'Lun-Jue', ['09:00', '10:00', '11:00', '14:00', '15:00']),
            ('prof-012', 'Kevin', 'Mena Andrade', 'Psicólogo', 'Universidad de Tarapacá', 'Psicología Clínica', 'Registro N°760446 Superintendencia de Salud', 'Atención clínica: evaluación y tratamiento. Acompañamiento terapéutico personalizado, enfoque ético y orientado al bienestar.', 'Hombre', ['Individual', 'Parejas', 'Familias', 'Personas LGBTQ+', 'Personas neurodivergentes'], ['Adolescentes (13–17)', 'Adultos jóvenes (18–25)', 'Adultos (26–64)'], 'https://cdn.prod.website-files.com/68f677b74ad8262f24254c20/69541fb9f67c19d190032624_PsicologoFoto-Kevin_Mena_Andrade.jpeg', 'https://beta-sacmed.novacaribe.com/ReservaOnline/11590/parameters/2494/6157/648ed2ea-efef-4569-bbc9-283346e20046', 'sede-001', 'inst-001', 'Lun-Vie', ['10:00', '11:00', '12:00', '15:00', '16:00', '17:00']),
            ('prof-013', 'Savka', 'Gubelin Morales', 'Psicóloga', 'Universidad Austral de Chile', 'TCC y Terapia de Juego', 'Registro Superintendencia de Salud', 'Experiencia en atención clínica individual y familiar. Terapia Cognitivo Conductual y Terapia de Juego infantojuvenil.', 'Mujer', ['Individual', 'Cuidadores / familiares', 'Personas neurodivergentes'], ['Adolescentes (13–17)', 'Adultos jóvenes (18–25)', 'Adultos (26–64)'], 'https://cdn.prod.website-files.com/68f677b74ad8262f24254c20/69541fb9c4a5ed344bb723fc_Psico%CC%81logaFoto-Savka_Gubelin_Morales.jpeg', 'https://beta-sacmed.novacaribe.com/ReservaOnline/11590/parameters/2494/6157/fd34a2ac-bc38-46d4-842f-7a2325ca1702', 'sede-002', 'inst-001', 'Lun-Mié', ['09:00', '10:00', '14:00', '15:00']),
            ('prof-014', 'Silvia', 'Núñez Mora', 'Psicóloga', 'Universidad La República', 'Psicología Clínica y Comunitaria', 'Registro Superintendencia de Salud', 'Experiencia en atención clínica y comunitaria. Regulación emocional, manejo del estrés, autoestima y desarrollo personal.', 'Mujer', ['Individual', 'Parejas', 'Personas neurodivergentes'], ['Adultos jóvenes (18–25)', 'Adultos (26–64)'], 'https://cdn.prod.website-files.com/68f677b74ad8262f24254c20/69542989a25e926ab5570abb_Psico%CC%81logaFoto_Silvia_Nun%CC%83ez_Mora.jpg', 'https://beta-sacmed.novacaribe.com/ReservaOnline/11590/parameters/2494/6157/19f90d35-a3c5-4658-a6cd-f89791369432', 'sede-003', 'inst-002', 'Mar-Vie', ['10:00', '11:00', '14:00', '15:00', '16:00']),
            ('prof-015', 'Josefa', 'Quijanes Carvajal', 'Psicóloga', 'Universidad de Santiago de Chile', 'Psicoterapia Humanista-Transpersonal', 'Registro N°603472 Superintendencia de Salud', 'Espacio de cuidado y acompañamiento. Incorpora cuerpo y respiración, recuperando la dimensión espiritual del ser humano.', 'Mujer', ['Individual', 'Familias'], ['Niños (0–12)', 'Adolescentes (13–17)', 'Adultos jóvenes (18–25)', 'Adultos (26–64)'], 'https://cdn.prod.website-files.com/68f677b74ad8262f24254c20/69990213130a0cf0069835ed_1f476701eb90c5cf4313c08fcd5a5717_Foto_Psicologa-Josefa%20Quijanes%20Carvajal.jpeg', '', 'sede-001', 'inst-001', 'Lun-Jue', ['09:00', '10:00', '11:00', '15:00', '16:00'])
        ]
        
        for prof in profesionales_data:
            cur.execute("""
                INSERT INTO profesionales (prof_id_ext, nombre, apellido, titulo, universidad, especialidad, registro, descripcion, genero, tipo_terapia, grupo_etario, foto, link, sede_id, institucion_id, disponibilidad, horarios)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (prof_id_ext) DO NOTHING;
            """, prof)


        conn.commit()
        cur.close()
        conn.close()
        print("Database initialization completed successfully.")
        
    except Exception as e:
        print(f"Error initializing database: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    init_db()
