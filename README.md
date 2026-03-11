# Sanad API - Backend

Backend principal para el sistema SANAD (Plataforma Integral de Salud Institucional).
Construido con **FastAPI** y **PostgreSQL**.

## Requisitos Previos
- Python 3.10+
- PostgreSQL (Base de datos transaccional)
- Coolify (Para despliegue en VPS)

## Configuración y Variables de Entorno
Crea un archivo `.env` en la raíz del proyecto (o configúralo en tu gestor de variables de Coolify) con los siguientes parámetros **estrictamente requeridos**:

```env
# Configuración Base de Datos (PostgreSQL)
DB_HOST=tu_host_ip_o_rds
DB_NAME=sanad_db
DB_USER=tu_usuario
DB_PASS=tu_password
DB_PORT=5432

# Seguridad y Autenticación (¡Obligatorias!)
SECRET_KEY=clave_larga_y_segura_para_firmar_jwt
SANAD_API_KEY=SND-clave_para_proteger_endpoints

# Integración externa SACMED
SACMED_API_KEY=SND-api_key_provista_por_sacmed
```

> **Importante:** La aplicación implementa bloqueos de seguridad y **no arrancará** si percibe que le faltan `SECRET_KEY` o `SANAD_API_KEY` en el entorno. Quedan estrictamente prohibidos los valores incrustados ("hardcoded") por razones de prevención de filtraciones en el repositorio de GitHub.

## Despliegue en Coolify (Guía Rápida)
1. Conecta tu repositorio de GitHub asociándolo a tu proyecto de Coolify.
2. Selecciona **Nixpacks** o un **Dockerfile** si lo prefieres para el tipo de build. Nixpacks autodetectará el archivo `requirements.txt`.
3. Establece el **Start Command**: `uvicorn main:app --host 0.0.0.0 --port 8000`.
4. Añade todas las **Variables de Entorno** requeridas listadas arriba.
5. Inicia el despliegue.

## Entorno Local de Desarrollo
Para levantar el proyecto en tu máquina (Windows/Linux/Mac):

1. Clona el proyecto y entra al directorio.
2. Crea un entorno virtual: `python -m venv venv`
3. Actívalo: 
   - Windows: `.\venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. Instala dependencias: `pip install -r requirements.txt`
5. Configura tu `.env` con credenciales de prueba.
6. Ejecuta la app: `uvicorn main:app --reload`
