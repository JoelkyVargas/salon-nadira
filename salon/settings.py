import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# -----------------------------------------------
# BASE DIR
# -----------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------
# CARGA VARIABLES .ENV
# -----------------------------------------------
load_dotenv(BASE_DIR / ".env")

# -----------------------------------------------
# CONFIGURACIONES BÁSICAS
# -----------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "clave_por_defecto_insegura")
DEBUG = os.getenv("DEBUG", "False") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
CSRF_TRUSTED_ORIGINS = os.getenv("CSRF_TRUSTED_ORIGINS", "http://localhost").split(",")

# -----------------------------------------------
# APLICACIONES INSTALADAS
# -----------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'citas',
    # agrega aquí tus apps personalizadas, ej:
    # 'reservas',
]

# -----------------------------------------------
# MIDDLEWARE
# -----------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # para servir estáticos en producción
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# -----------------------------------------------
# URLS Y WSGI
# -----------------------------------------------
ROOT_URLCONF = 'salon.urls'
WSGI_APPLICATION = 'salon.wsgi.application'

# -----------------------------------------------
# BASE DE DATOS
# -----------------------------------------------
DEFAULT_DB_URL = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"

# ==========================
# BASE DE DATOS (Render/Local)
# ==========================
# Producción (Render) usa DATABASE_URL; local cae a SQLite.
if os.getenv("DATABASE_URL"):
    import dj_database_url
    DATABASES = {
        "default": dj_database_url.config(conn_max_age=600, ssl_require=True)
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# -----------------------------------------------
# CONFIGURACIÓN DE TEMPLATES
# -----------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# -----------------------------------------------
# CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS
# -----------------------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR
