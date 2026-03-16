import os

filepath = 'c:/Users/Nicolito/Desktop/handoff/prototype/backend_repo/main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace Imports
content = content.replace(
    'from fastapi import FastAPI, Depends, HTTPException, status',
    'from fastapi import FastAPI, Depends, HTTPException, status, Security, APIRouter\nfrom fastapi.openapi.docs import get_swagger_ui_html\nfrom fastapi.staticfiles import StaticFiles\nfrom fastapi.security.api_key import APIKeyHeader, APIKey'
)

# Replace Security Config
content = content.replace(
    '''# --- CONFIGURACIÓN DE SEGURIDAD (JWT) ---
SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_sanad_key_2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
SACMED_API_KEY = os.getenv("SACMED_API_KEY")''',
    '''# --- CONFIGURACIÓN DE SEGURIDAD (JWT & API KEY) ---
SECRET_KEY = os.getenv("SECRET_KEY", "super_secret_sanad_key_2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Configuración API Key de acceso a SANAD (Nuestra API)
API_KEY_NAME = "X-ApiKey"
API_KEY_VALUE = os.getenv("SANAD_API_KEY", "SANAD_DEV_KEY_2026")
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY_VALUE:
        return api_key
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing X-ApiKey",
    )

SACMED_API_KEY = os.getenv("SACMED_API_KEY")'''
)

# Replace App Init
content = content.replace(
    '''app = FastAPI(
    title="Sanad API 🛡️", 
    description="Backend principal para el sistema SANAD - Plataforma Integral de Salud Institucional",
    version="1.1.0",
    docs_url="/docs",      # Swagger UI
    redoc_url="/redoc",    # ReDoc
    lifespan=lifespan
)''',
    '''app = FastAPI(
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
api_router = APIRouter(dependencies=[Depends(get_api_key)])'''
)

# Replace remaining occurrences
lines = content.split('\n')
for i in range(len(lines)):
    if lines[i].startswith('@app.') and '/api/' in lines[i]:
        lines[i] = lines[i].replace('@app.', '@api_router.')

content = '\n'.join(lines)
if '# --- INCORPORAR ROUTER ---' not in content:
    content += '\n\n# --- INCORPORAR ROUTER ---\napp.include_router(api_router)\n'

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("File successfully refactored.")
