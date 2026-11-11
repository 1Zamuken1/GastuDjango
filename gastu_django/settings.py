from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False').strip().lower() in ('true', '1', 't')

if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-key-do-not-use-in-production'
    else:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured("SECRET_KEY no configurada en las variables de entorno.")

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
# llama-3.3-70b-versatile fue retirado de Groq (responde 404). gpt-oss-120b es el
# mejor de la cuenta con tools; qwen3.8 queda de respaldo si el principal falla.
GROQ_MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')
# Respaldos en orden (cada modelo tiene su propia cuota por minuto en Groq).
GROQ_MODEL_RESPALDO = os.getenv('GROQ_MODEL_RESPALDO', 'openai/gpt-oss-20b,qwen/qwen3.8-27b')
GROQ_REASONING_EFFORT = os.getenv('GROQ_REASONING_EFFORT', 'low')
# Modelo de la lectura de alertas bancarias (captura); por defecto el mismo.
GROQ_MODEL_CAPTURA = os.getenv('GROQ_MODEL_CAPTURA', GROQ_MODEL)
# Mensajes al agente por usuario y por dia (protege la cuota de Groq).
AGENTE_MAX_MENSAJES_DIA = int(os.getenv('AGENTE_MAX_MENSAJES_DIA', '100'))

# ── Hosts y Seguridad ─────────────────────────────────────────
_allowed_hosts_env = os.getenv('ALLOWED_HOSTS')
if _allowed_hosts_env:
    ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_env.split(',') if h.strip()]
else:
    ALLOWED_HOSTS = ['10.1.164.209', 'localhost', '127.0.0.1', '.onrender.com']

# CSRF Trusted Origins para producción
_csrf_origins_env = os.getenv('CSRF_TRUSTED_ORIGINS')
if _csrf_origins_env:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins_env.split(',') if o.strip()]
else:
    CSRF_TRUSTED_ORIGINS = ['https://gastu.onrender.com']

# Forzar HTTPS cuando se está detrás de un proxy (Render, Nginx en OCI, etc.)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'django.contrib.sites',
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
    'captura_bancaria',
    'channels',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Whitenoise: solo en producción (DEBUG=False).
    # En desarrollo, Django sirve los estáticos de cada app directamente.
    *(['whitenoise.middleware.WhiteNoiseMiddleware'] if not DEBUG else []),
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Requerido por django-allauth
    'allauth.account.middleware.AccountMiddleware',
    # Tailwind hot reload (solo en DEBUG)
    *(['django_browser_reload.middleware.BrowserReloadMiddleware'] if DEBUG else []),
    # 🔹 Separación de contextos Admin / Usuario 🔹───────────────
    'gastu_django.middleware.AdminAreaMiddleware',
    'gastu_django.middleware.ContentSecurityPolicyMiddleware',
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
                'django.template.context_processors.request',
                'notificaciones.context_processors.notificaciones_count',
                'captura_bancaria.interruptor.contexto_captura',
            ],
        },
    },
]

WSGI_APPLICATION = 'gastu_django.wsgi.application'
ASGI_APPLICATION = 'gastu_django.asgi.application'

if os.getenv('REDIS_URL'):
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [os.getenv('REDIS_URL')],
            },
        },
    }
else:
    # Capa en memoria para desarrollo local (no requiere servidor Redis extra)
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer"
        }
    }

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
            'OPTIONS': {
                'timeout': 20,
            },
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
# Estaticos con hash de version en produccion: cada cambio de CSS/JS genera
# un nombre de archivo nuevo, asi el navegador nunca usa una copia vieja aunque
# nginx los cachee 30 dias. Django 5.1+ ignora STATICFILES_STORAGE; va en STORAGES.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': (
            'whitenoise.storage.CompressedManifestStaticFilesStorage'
            if not DEBUG
            else 'django.contrib.staticfiles.storage.StaticFilesStorage'
        ),
    },
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ──────────────────────────────────────────────────────────────
# TAILWIND CSS
# ──────────────────────────────────────────────────────────────
TAILWIND_APP_NAME = 'theme'
NPM_BIN_PATH = os.getenv('NPM_BIN_PATH', r'C:\Program Files\nodejs\npm.cmd' if os.name == 'nt' else 'npm')
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

# Adaptador personalizado: genera username automatico para usuarios de Google
# (AbstractUser exige username en BD aunque no se muestre en el formulario)
SOCIALACCOUNT_ADAPTER = 'usuarios.adapters.SocialAccountAdapter'
SOCIALACCOUNT_LOGIN_ON_GET = True


# Configuracion de redes sociales — Google OAuth
# client_id y secret se obtienen de Google Cloud Console y se cargan desde .env
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.getenv('GOOGLE_OAUTH_CLIENT_ID', ''),
            'secret':    os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', ''),
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

# ──────────────────────────────────────────────────────────────
# CAPTURA BANCARIA (correo reenviado)
# ──────────────────────────────────────────────────────────────
# Interruptor de la captura automatica. Apagada por defecto en produccion
# (DEBUG=False) hasta montar el servidor de correo; CAPTURA_HABILITADA=True la enciende.
CAPTURA_HABILITADA = os.getenv('CAPTURA_HABILITADA', 'True' if DEBUG else 'False').strip().lower() in ('true', '1', 't')

# Dominio de las direcciones de captura (alias@CAPTURA_DOMINIO).
CAPTURA_DOMINIO = os.getenv('CAPTURA_DOMINIO', 'gastu.duckdns.org')
# URL interna a la que el servidor SMTP entrega cada correo recibido.
CAPTURA_INGESTA_URL = os.getenv('CAPTURA_INGESTA_URL', 'http://127.0.0.1:8000/captura/api/ingesta/')
# Secreto compartido entre el servidor SMTP y Django. Obligatorio en produccion.
CAPTURA_INGESTA_TOKEN = os.getenv('CAPTURA_INGESTA_TOKEN', 'dev-captura-token' if DEBUG else '')
# Leer con IA (Groq) las alertas que el parser de reglas no reconoce.
CAPTURA_USAR_IA = os.getenv('CAPTURA_USAR_IA', 'True') == 'True'
# Lecturas con IA al dia por buzon para correos sin firma DKIM (pueden ser falsos).
CAPTURA_IA_MAX_SIN_DKIM = int(os.getenv('CAPTURA_IA_MAX_SIN_DKIM', '20'))

# --------------------------------------------------------------
# CONFIGURACI�N DE SEGURIDAD (HARDENING)
# --------------------------------------------------------------
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 60 * 60 * 4  # 4 horas de sesion

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 ano
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Content-Security-Policy. En Report-Only hasta sacar los scripts en linea de
# las plantillas; las violaciones salen en la consola del navegador.
CSP_REPORT_ONLY = os.getenv('CSP_REPORT_ONLY', 'True') == 'True'
CSP_POLITICA = '; '.join([
    "default-src 'self'",
    "script-src 'self' https://cdn.jsdelivr.net https://unpkg.com https://cdnjs.cloudflare.com",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net",
    "font-src 'self' data: https://fonts.gstatic.com",
    "img-src 'self' data: blob: https://*.googleusercontent.com",
    "connect-src 'self' ws: wss:",
    "object-src 'none'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
    "form-action 'self' https://accounts.google.com",
])

# Rate limit por IP real del cliente (detras de nginx REMOTE_ADDR es el proxy).
RATELIMIT_IP_META_KEY = 'gastu_django.ratelimit_keys.ip_cliente'

# --------------------------------------------------------------
# REST FRAMEWORK SEGURIDAD POR DEFECTO
# --------------------------------------------------------------
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
}
