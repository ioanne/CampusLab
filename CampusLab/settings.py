import os 
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
# Lee el archivo .env de la raíz del proyecto, si existe, y deja sus valores
# disponibles como variables de entorno. Lo que ya venga del sistema o de Docker
# tiene prioridad: el .env nunca pisa una variable que ya estaba definida.

load_dotenv(BASE_DIR / ".env")

def env(name, default=None):
    return os.getenv (name, default)

def env_bool(name, default=False):
    return env(name, str(int(default))).strip().lower() in {"1", "true", "on"}


SECRET_KEY = env("SECRET_KEY", "cambia-esta-clave-en-desarrollo")
JWT_SECRET_KEY = env("JWT_SECRET_KEY", "clave-jwt-desarrollo-super-segura-12345")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(env("ACCESS_TOKEN_MINUTES", "60"))
REFRESH_TOKEN_DAYS = int(env("REFRESH_TOKEN_DAYS", "7"))

DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = [host.strip() for host in env("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

EXTERNAL_APPS = [
    "ninja",
]

# Una app por cada cosa distinta que resuelve el sistema. El orden de la lista
# no cambia el funcionamiento, pero conviene escribirlas de la que no depende de
# nadie a la que depende de todas: es el mismo orden en el que se construyen.
LOCAL_APPS = [
    "apps.accounts.apps.AccountsConfig",
]

INSTALLED_APPS = DJANGO_APPS + EXTERNAL_APPS + LOCAL_APPS


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'CampusLab.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'CampusLab.wsgi.application'

sqlite_path = Path(env("SQLITE_PATH", BASE_DIR / "data" / "db.sqlite3"))
sqlite_path.parent.mkdir(parents=True, exist_ok=True)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': sqlite_path,
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        "OPTIONS": {"min_length": 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]



LANGUAGE_CODE = "es-ar"
TIME_ZONE = "America/Argentina/Buenos_Aires"

USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"


MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

AUTH_USER_MODEL = "accounts.User"


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


