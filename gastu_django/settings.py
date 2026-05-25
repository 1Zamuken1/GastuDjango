from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-sr^8%d0t&zht-2qbvnql&_p0a0(qd6b2v*@9u#z^6-u(zbrjul')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['10.1.164.209', 'localhost', '127.0.0.1', '.onrender.com']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    # ── Tailwind CSS ─────────────────────────────────────────────
    'tailwind',
    'theme',
    'django_browser_reload',
    # ── django-allauth ───────────────────────────────────────────
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    # ── Apps del proyecto ────────────────────────────────────────
    'landing',
    'usuarios',
    'movimientos',
    'ahorros',
    'notificaciones',
    'dashboard',
    'programaciones',
    'panel_admin',
    'agente_financiero',
    'presupuesto',
    'categorias',
    'historial',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Requerido por django-allauth
    'allauth.account.middleware.AccountMiddleware',
    # Tailwind hot reload (solo en DEBUG)
    'django_browser_reload.middleware.BrowserReloadMiddleware',
    # ── Separación de contextos Admin / Usuario ───────────────
    'gastu_django.middleware.AdminAreaMiddleware',
]

ROOT_URLCONF = 'gastu_django.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Requerido por django-allauth
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'gastu_django.wsgi.application'

# ──────────────────────────────────────────────────────────────
# BASE DE DATOS
#
# MODO ACTIVO: SQLite local (USE_SQLITE=True en .env)
# Para volver a Supabase: cambiar USE_SQLITE=False en .env
# ──────────────────────────────────────────────────────────────

# ── SQLite — desarrollo local (activo) ───────────────────────
if os.getenv('USE_SQLITE', 'False') == 'True':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ── Supabase / PostgreSQL — producción (en pausa) ────────────
else:
    DATABASES = {
        'default': dj_database_url.config(
            default=os.getenv('DATABASE_URL'),
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
    # Requerido para Transaction pooler de Supabase (puerto 6543)
    # DATABASE_URL debe empezar con postgresql://, no postgres://
    DATABASES['default']['OPTIONS'] = {
        'prepare_threshold': None,
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ──────────────────────────────────────────────────────────────
# TAILWIND CSS
# ──────────────────────────────────────────────────────────────
TAILWIND_APP_NAME = 'theme'
NPM_BIN_PATH = r'C:\Program Files\nodejs\npm.cmd'
INTERNAL_IPS = ['127.0.0.1']

AUTH_USER_MODEL = 'usuarios.Usuario'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# ──────────────────────────────────────────────────────────────
# AUTHENTICATION BACKENDS
# ModelBackend: login nativo por email (nuestro flujo propio)
# allauth:      login social (Google OAuth, futuro)
# ──────────────────────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# ──────────────────────────────────────────────────────────────
# DJANGO-ALLAUTH — Configuracion
# ──────────────────────────────────────────────────────────────
SITE_ID = 1

# Configuracion de cuenta
ACCOUNT_LOGIN_METHODS         = {'email'}
ACCOUNT_SIGNUP_FIELDS         = ['email*', 'password1*', 'password2*']
ACCOUNT_UNIQUE_EMAIL          = True
ACCOUNT_EMAIL_VERIFICATION    = 'none'    # sin verificacion por ahora (desarrollo)
ACCOUNT_LOGIN_REDIRECT_URL    = '/dashboard/'
ACCOUNT_LOGOUT_REDIRECT_URL   = '/'
ACCOUNT_EMAIL_SUBJECT_PREFIX  = ''        # Quita el sufijo [ejemplo.com] de los correos


# Configuracion de redes sociales — Google OAuth
# client_id y secret se obtienen de Google Cloud Console
# Dejar vacios en desarrollo; completar al activar OAuth en produccion
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': '',
            'secret':    '',
            'key':       '',
        },
        'SCOPE':       ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'EMAIL_AUTHENTICATION': True,
    }
}

# ──────────────────────────────────────────────────────────────
# CONFIGURACION DE CORREO (Gmail SMTP)
# ──────────────────────────────────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'soporte.gastuapp@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
