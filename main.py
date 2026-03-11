from fastapi import FastAPI, Depends, HTTPException, status, Security, APIRouter
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from fastapi.security.api_key import APIKeyHeader, APIKey
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import os
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import requests

load_dotenv()

# --- CONFIGURACIÓN DE SEGURIDAD (JWT & API KEY) ---
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("Missing SECRET_KEY environment variable. Cannot start server securely.")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Configuración API Key de acceso a SANAD (Nuestra API)
API_KEY_NAME = "X-ApiKey"
API_KEY_VALUE = os.getenv("SANAD_API_KEY")
if not API_KEY_VALUE:
    raise ValueError("Missing SANAD_API_KEY environment variable. Cannot start server securely.")
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY_VALUE:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing X-ApiKey",
    )

SACMED_API_KEY = os.getenv("SACMED_API_KEY")
SACMED_BASE_URL = "https://availability-ms-prod-860551794565.southamerica-west1.run.app"

# --- PISCINA DE CONEXIONES (DB POOL) ---
db_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool
    try:
        db_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            port=os.getenv("DB_PORT", "5432")
        )
        print("✅ [DB] Connection pool initialized successfully.")
    except Exception as e:
        print("❌ [DB] Error initializing connection pool:", e)
        
    yield # Aquí se ejecuta la aplicación
    
    # Cuando la app se apaga, cerramos todas las conexiones
    if db_pool:
        db_pool.closeall()
        print("🔒 [DB] Connection pool closed.")

# --- INICIALIZACIÓN DE LA APP ---
app = FastAPI(
    title="Sanad API 🛡️", 
    description="Backend principal para el sistema SANAD - Plataforma Integral de Salud Institucional",
    version="1.1.0",
    docs_url=None,      # Deshabilitado para inyectar custom UI
    redoc_url=None,
    lifespan=lifespan
)

# Montar estáticos para CSS customizado
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-custom.css",
    )

# APIRouter protegido para todas las rutas que empiecen con /api
api_router = APIRouter(dependencies=[Depends(get_api_key)])

# --- CONFIGURACIÓN CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# --- 2. CONEXIÓN A BASE DE DATOS ---
def get_db():
    """Inyecta una conexión activa desde el Pool, en lugar de crear una nueva de cero."""
    if db_pool is None:
        raise HTTPException(status_code=500, detail="Database connection pool not ready")
        
    conn = db_pool.getconn()
    try:
        yield conn
    finally:
        # Devuelve la conexión al pool para que otro usuario pueda usarla instantáneamente
        if conn:
            db_pool.putconn(conn)

# --- 3. FUNCIONES DE UTILIDAD (JWT) ---
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- 4. ESQUEMAS (PYDANTIC) ---
class LoginPacienteRequest(BaseModel):
    rut: str = Field(..., title="RUT del Paciente", description="El RUT debe enviarse con dígito verificador y guión, sin puntos.", json_schema_extra={"example": "18765432-1"})

class LoginInstitucionRequest(BaseModel):
    email: str = Field(..., title="Correo electrónico", json_schema_extra={"example": "admin@sanad.cl"})
    password: str = Field(..., title="Contraseña", json_schema_extra={"example": "admin123"})
    rut_institucion: str | None = Field(None, title="RUT Institución")

class AgendarRequest(BaseModel):
    profesional_id: str = Field(..., title="ID del Profesional")
    motivo: str = Field(default="Consulta General", title="Motivo de Consulta")

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    paciente: dict | None = None
    usuario: dict | None = None

class ProfesionalResponse(BaseModel):
    id: int
    prof_id_ext: str | None
    nombre: str
    apellido: str
    titulo: str | None
    universidad: str | None
    especialidad: str | None
    registro: str | None
    descripcion: str | None
    genero: str | None
    tipo_terapia: list[str] | None
    grupo_etario: list[str] | None
    foto: str | None
    link: str | None
    sede_id: str | None
    institucion_id: str | None
    disponibilidad: str | None
    horarios: list[str] | None

# --- 5. ENDPOINTS ---

@app.get("/", tags=["General"], summary="Health Check Base")
def read_root():
    """Endpoint principal para verificar que el servicio está levantado."""
    return {"status": "ok", "message": "Bienvenido a la API SANAD", "docs": "/docs"}

@app.get("/health", tags=["General"], summary="Health Check Detallado")
def health_check():
    """Verifica el estado de los servicios internos (ej. Base de datos)."""
    # Aquí podríamos agregar un test de BD
    try:
        conn = next(get_db())
        conn.close()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return {"status": "ok", "database": db_status, "timestamp": datetime.now().isoformat()}

@api_router.post("/api/auth/login-paciente", response_model=TokenResponse, tags=["Autenticación"], summary="Login de Pacientes")
def login_paciente(req: LoginPacienteRequest, conn = Depends(get_db)):
    """
    Inicia sesión para un paciente. 
    Verifica que el RUT exista en la BD y que no haya superado su límite de sesiones.
    Retorna un token JWT y los datos del paciente.
    """
    rut_clean = req.rut.replace(".", "").strip().upper()
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("SELECT rut, nombre_completo, email, sede, reservas_realizadas FROM registros_usuarios WHERE rut = %s", (rut_clean,))
        paciente = cur.fetchone()
        
    if not paciente:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RUT no encontrado en los registros.")
        
    if paciente['reservas_realizadas'] >= 5: # Límite ejemplo
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Límite de atenciones alcanzado. Comunícate con el DAE.")
        
    # Generar Token JWT Seguro
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": paciente['rut'], "rol": "paciente"}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "paciente": paciente
    }

@api_router.get("/api/pacientes/{rut}/historial", tags=["Pacientes"], summary="Historial de Atenciones")
def get_historial(rut: str, conn = Depends(get_db)):
    """Obtiene el historial clínico/atenciones pasadas de un paciente específico."""
    rut_clean = rut.replace(".", "").strip().upper()
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT nombre_especialista, motivo_consulta, 
            fecha_registro AT TIME ZONE 'UTC' AT TIME ZONE 'America/Santiago' as fecha_registro 
            FROM logs_atenciones WHERE rut_paciente = %s 
            ORDER BY fecha_registro DESC LIMIT 5
        """, (rut_clean,))
        historial = cur.fetchall()
        
    return {"historial": historial, "total": len(historial)}

@api_router.get("/api/profesionales", tags=["General"], response_model=list[ProfesionalResponse])
def get_profesionales(
    search: str | None = None,
    genero: str | None = None,
    tipo_terapia: str | None = None,
    grupo_etario: str | None = None,
    motivo: str | None = None,
    conn = Depends(get_db)
):
    """Obtiene la lista de profesionales con filtros dinámicos opcionales."""
    query = "SELECT * FROM profesionales WHERE 1=1"
    params = []

    if search:
        query += " AND (nombre ILIKE %s OR apellido ILIKE %s OR especialidad ILIKE %s)"
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    if genero:
        query += " AND genero = %s"
        params.append(genero)

    if tipo_terapia:
        # Use ILIKE with array elements for more flexibility
        query += " AND EXISTS (SELECT 1 FROM unnest(tipo_terapia) s WHERE s ILIKE %s)"
        params.append(f"%{tipo_terapia}%")

    if grupo_etario:
        query += " AND EXISTS (SELECT 1 FROM unnest(grupo_etario) s WHERE s ILIKE %s)"
        params.append(f"%{grupo_etario}%")

    if motivo:
        query += " AND (especialidad ILIKE %s OR descripcion ILIKE %s)"
        params.extend([f"%{motivo}%", f"%{motivo}%"])

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, tuple(params))
        profesionales = cur.fetchall()
        
    return profesionales

@api_router.post("/api/pacientes/{rut}/agendar", tags=["Pacientes"], summary="Agendar nueva sesión")
def agendar_sesion(rut: str, req: AgendarRequest, conn = Depends(get_db)):
    """Permite al paciente agendar una cita, respetando su límite máximo de 4 sesiones."""
    rut_clean = rut.replace(".", "").strip().upper()
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Obtener nombre del profesional
        cur.execute("SELECT nombre, apellido, titulo FROM profesionales WHERE id = %s", (req.profesional_id,))
        prof_res = cur.fetchone()
        prof_nombre = f"{prof_res['titulo']} {prof_res['nombre']} {prof_res['apellido']}" if prof_res else f"Especialista {req.profesional_id}"

        # Verificar cantidad de sesiones actuales
        cur.execute("SELECT reservas_realizadas FROM registros_usuarios WHERE rut = %s", (rut_clean,))
        paciente = cur.fetchone()
        
        if not paciente:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")
            
        if paciente['reservas_realizadas'] >= 4:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Límite de atenciones alcanzado. Ya has utilizado tus 4 sesiones."
            )
            
        # Agendar: Incrementar reservas en el usuario y crear el log de atención
        try:
            cur.execute("""
                UPDATE registros_usuarios 
                SET reservas_realizadas = reservas_realizadas + 1 
                WHERE rut = %s
            """, (rut_clean,))
            
            cur.execute("""
                INSERT INTO logs_atenciones (rut_paciente, nombre_especialista, motivo_consulta)
                VALUES (%s, %s, %s)
            """, (rut_clean, prof_nombre, req.motivo))
            
            conn.commit()
            
            # Devolvemos el conteo actualizado
            nuevo_conteo = paciente['reservas_realizadas'] + 1
            return {
                "status": "success", 
                "message": "Cita agendada exitosamente.", 
                "reservas_realizadas": nuevo_conteo,
                "limite": 4
            }
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/api/auth/login-institucion", response_model=TokenResponse, tags=["Autenticación"], summary="Login Institucional y Clínicos")
def login_institucion(req: LoginInstitucionRequest, conn = Depends(get_db)):
    """Inicia sesión para administradores y clínicos."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # En producción se debe usar hashing de contraseñas (ej. bcrypt)
        cur.execute("""
            SELECT id, email, nombre, apellido, rol, sede_id, institucion_id 
            FROM usuarios_institucionales 
            WHERE email = %s AND password_hash = %s
        """, (req.email, req.password))
        usuario = cur.fetchone()
        
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales incorrectas")
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": usuario['email'], "rol": usuario['rol'], "institucion_id": usuario['institucion_id']}, 
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "usuario": usuario
    }

@api_router.get("/api/dashboard/kpis", tags=["Dashboard"], summary="Métricas principales (KPIs)")
def get_dashboard_kpis(sede: str | None = None, conn = Depends(get_db)):
    """Obtiene los KPIs y datos de gráficos para el dashboard."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 1. Total Pacientes y Sesiones
        query_pacs = "SELECT COUNT(*) as total_pacs, COALESCE(SUM(reservas_realizadas), 0) as total_res FROM registros_usuarios"
        params_pacs = []
        if sede and sede != 'todas':
            query_pacs += " WHERE sede = %s"
            params_pacs.append(sede)
            
        cur.execute(query_pacs, tuple(params_pacs))
        row_pacs = cur.fetchone()
        total_pacs = row_pacs['total_pacs'] if row_pacs else 0
        total_res_uso = row_pacs['total_res'] if row_pacs else 0
        
        # 2. Total Atenciones
        query_logs = """
            SELECT COUNT(*) as total_atenciones 
            FROM logs_atenciones l
            JOIN registros_usuarios r ON l.rut_paciente = r.rut
        """
        params_logs = []
        if sede and sede != 'todas':
            query_logs += " WHERE r.sede = %s"
            params_logs.append(sede)
            
        cur.execute(query_logs, tuple(params_logs))
        total_atenciones = cur.fetchone()['total_atenciones']
        
        # 3. Gráfico Semanal (últimos 7 días)
        hoy = datetime.now().date()
        fechas = [(hoy - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]
        labels_dias = [(hoy - timedelta(days=i)).strftime('%a') for i in range(6, -1, -1)]
        chart_bar_data = [0] * 7
        
        query_bar = """
            SELECT l.fecha_registro::date as dia, COUNT(*) as count
            FROM logs_atenciones l
            JOIN registros_usuarios r ON l.rut_paciente = r.rut
            WHERE l.fecha_registro >= NOW() - INTERVAL '7 days'
        """
        if sede and sede != 'todas':
            query_bar += " AND r.sede = %s"
            
        query_bar += " GROUP BY dia"
        cur.execute(query_bar, tuple(params_logs))
        
        dias_db = cur.fetchall()
        for d in dias_db:
            dia_str = d['dia'].isoformat() if hasattr(d['dia'], 'isoformat') else str(d['dia'])
            if dia_str in fechas:
                chart_bar_data[fechas.index(dia_str)] = d['count']
                
        # 4. Gráfico Dona (Tipos de Atención / Motivo)
        query_donut = """
            SELECT l.motivo_consulta, COUNT(*) as count
            FROM logs_atenciones l
            JOIN registros_usuarios r ON l.rut_paciente = r.rut
        """
        if sede and sede != 'todas':
            query_donut += " WHERE r.sede = %s"
        query_donut += " GROUP BY l.motivo_consulta"
        
        cur.execute(query_donut, tuple(params_logs))
        motivos_db = cur.fetchall()
        doughnut_labels = []
        doughnut_data = []
        for m in motivos_db:
            doughnut_labels.append(m['motivo_consulta'])
            doughnut_data.append(m['count'])
            
        # 5. Citas Recientes
        query_citas = """
            SELECT l.id, l.rut_paciente, l.nombre_especialista, l.motivo_consulta,
                   l.fecha_registro AT TIME ZONE 'UTC' AT TIME ZONE 'America/Santiago' as fecha_registro,
                   r.nombre_completo as paciente_nombre, r.sede
            FROM logs_atenciones l
            JOIN registros_usuarios r ON l.rut_paciente = r.rut
        """
        if sede and sede != 'todas':
            query_citas += " WHERE r.sede = %s"
        query_citas += " ORDER BY l.fecha_registro DESC LIMIT 5"
        
        cur.execute(query_citas, tuple(params_logs))
        citas_recientes = cur.fetchall()
        
    bolsa_total = 1500
    restantes = bolsa_total - total_res_uso
    
    return {
        "kpis": {
            "pacientes_activos": total_pacs,
            "sesiones_totales_mes": total_res_uso,
            "bolsa_restante": restantes,
            "bolsa_total": bolsa_total,
            "porcentaje_asistencia": 100, 
            "ausencias": 0,
            "total_atenciones_pasadas": total_atenciones
        },
        "charts": {
            "bar": {
                "labels": labels_dias,
                "data": chart_bar_data
            },
            "doughnut": {
                "labels": doughnut_labels if doughnut_labels else ["Sin Datos"],
                "data": doughnut_data if doughnut_data else [1]
            }
        },
        "citas_recientes": citas_recientes
    }

@api_router.get("/api/dashboard/pacientes", tags=["Dashboard"], summary="Lista de Pacientes activos")
def get_dashboard_pacientes(sede: str | None = None, conn = Depends(get_db)):
    """Devuelve la lista de pacientes registrados."""
    query = """
        SELECT 
            r.rut, 
            r.nombre_completo, 
            r.sede, 
            r.reservas_realizadas,
            (SELECT MAX(fecha_registro) FROM logs_atenciones WHERE rut_paciente = r.rut) as ultima_cita
        FROM registros_usuarios r
    """
    params = []
    if sede and sede != 'todas':
        query += " WHERE r.sede = %s"
        params.append(sede)
        
    query += " ORDER BY r.nombre_completo ASC"

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, tuple(params))
        pacientes = cur.fetchall()
    return pacientes

class PacienteCreate(BaseModel):
    rut: str
    nombre_completo: str
    sede: str

@api_router.post("/api/admin/pacientes", tags=["Admin"], summary="Añadir nuevo paciente")
def create_paciente(paciente: PacienteCreate, conn = Depends(get_db)):
    """Añade un nuevo paciente."""
    rut_clean = paciente.rut.replace(".", "").strip().upper()
    with conn.cursor() as cur:
        try:
            cur.execute(
                "INSERT INTO registros_usuarios (rut, nombre_completo, sede, email, reservas_realizadas) VALUES (%s, %s, %s, %s, 0)",
                (rut_clean, paciente.nombre_completo, paciente.sede, 'N/A')
            )
            conn.commit()
            return {"message": "Paciente creado exitosamente"}
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=str(e))

@api_router.delete("/api/admin/pacientes/{rut}", tags=["Admin"], summary="Eliminar paciente")
def delete_paciente(rut: str, conn = Depends(get_db)):
    """Elimina un paciente por su RUT."""
    with conn.cursor() as cur:
        try:
            # First delete related logs
            cur.execute("DELETE FROM logs_atenciones WHERE rut_paciente = %s", (rut,))
            # Then delete user
            cur.execute("DELETE FROM registros_usuarios WHERE rut = %s", (rut,))
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="Paciente no encontrado")
            conn.commit()
            return {"message": "Paciente eliminado exitosamente"}
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/api/instituciones", tags=["Instituciones"], summary="Obtener Instituciones (WIP)")
def get_instituciones():
    """(En Desarrollo) Retornará la lista de instituciones afiliadas a SANAD."""
    return [
        {"id": 1, "nombre": "Universidad Andina", "estado": "activa"},
        {"id": 2, "nombre": "Instituto de Salud", "estado": "inactiva"}
    ]
@api_router.get("/api/admin/sacmed/data", tags=["Admin"], summary="Proxy para obtener datos de SACMED")
def get_sacmed_data():
    """Actúa como proxy para la API de SACMED (solo admin_sistema)."""
    if not SACMED_API_KEY:
        raise HTTPException(status_code=500, detail="SACMED_API_KEY no configurada")

    headers = {
        "X-ApiKey": SACMED_API_KEY,
        "Accept": "application/json"
    }

    try:
        # 1. Obtener servicios
        services_res = requests.get(f"{SACMED_BASE_URL}/api/v1/service/by-company", headers=headers, timeout=10)
        services_data = services_res.json() if services_res.ok else []
        # Unwrap if it's {"services": [...]}
        services = services_data.get("services", services_data) if isinstance(services_data, dict) else services_data

        # 2. Obtener especialistas
        practitioners_res = requests.get(f"{SACMED_BASE_URL}/api/v1/practitioners", headers=headers, timeout=10)
        practitioners_data = practitioners_res.json() if practitioners_res.ok else []
        # SACMED returns {"practitioners": [...]}
        practitioners = practitioners_data.get("practitioners", practitioners_data) if isinstance(practitioners_data, dict) else practitioners_data

        return {
            "services": services,
            "practitioners": practitioners
        }
    except Exception as e:
        print(f"Error calling SACMED API: {e}")
        raise HTTPException(status_code=500, detail="Error de conexión con SACMED")


@api_router.get("/api/admin/sacmed/events/practitioner/{identification}/{from_date}/{to_date}", tags=["Admin"])
def get_sacmed_events_practitioner(identification: str, from_date: str, to_date: str):
    """Obtiene eventos de SACMED por especialista y rango de fechas."""
    if not SACMED_API_KEY:
        raise HTTPException(status_code=500, detail="SACMED_API_KEY no configurada")
    
    headers = {"X-ApiKey": SACMED_API_KEY, "Accept": "application/json"}
    url = f"{SACMED_BASE_URL}/api/v1/events/by-practitioner/identification/{identification}/fechas/{from_date}/{to_date}"
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json() if res.ok else []
    except Exception as e:
        print(f"Error calling SACMED Events API: {e}")
        raise HTTPException(status_code=500, detail="Error de conexión con SACMED")

@api_router.get("/api/admin/sacmed/events/patient/{identification}", tags=["Admin"])
def get_sacmed_events_patient(identification: str):
    """Obtiene eventos de SACMED por paciente (RUT)."""
    if not SACMED_API_KEY:
        raise HTTPException(status_code=500, detail="SACMED_API_KEY no configurada")
    
    headers = {"X-ApiKey": SACMED_API_KEY, "Accept": "application/json"}
    url = f"{SACMED_BASE_URL}/api/v1/events/by-patient/identification/{identification}"
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        return res.json() if res.ok else []
    except Exception as e:
        print(f"Error calling SACMED Patient Events API: {e}")
        raise HTTPException(status_code=500, detail="Error de conexión con SACMED")


# --- INCORPORAR ROUTER ---
app.include_router(api_router)
