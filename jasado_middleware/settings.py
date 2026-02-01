import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG") == "True"

ALLOWED_HOSTS = ["*"]
if DEBUG:
    SITE_URL = "http://localhost:7000"  # no slash
else:
    SITE_URL = "http://collegiate.pythonanywhere.com"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.aera",
    "apps.core",
    "apps.dentalheld",
    "apps.gls",
    "apps.wawibox",
    "apps.weclapp",
    "apps.shopware",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "jasado_middleware.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "jasado_middleware.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Europe/Berlin"

USE_I18N = True

USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static")
STATICFILES_DIRS = [os.path.join(BASE_DIR, "jasado_middleware/static")]


MEDIA_ROOT = os.path.join(BASE_DIR, "media")
MEDIA_URL = "/media/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# EMAIL
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = os.getenv("EMAIL_PORT")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS")
DEFAULT_FROM_EMAIL = f'"Jasado Middleware" <{EMAIL_HOST_USER}>'

# FTP FILES
FTP_FILES_ROOT = os.path.join(BASE_DIR, "ftp_files")
GLS_DOWNLOAD_PATH = os.path.join(FTP_FILES_ROOT, "gls", "downloads")
PENDING_DELETION_PATH = os.path.join(FTP_FILES_ROOT, "to_be_deleted")
GLS_UPLOAD_PATH = os.path.join(FTP_FILES_ROOT, "gls", "uploads")
WAWIBOX_DOWNLOAD_PATH = os.path.join(FTP_FILES_ROOT, "wawibox", "downloads")
WAWIBOX_UPLOAD_PATH = os.path.join(FTP_FILES_ROOT, "wawibox", "uploads")
DENTALHELD_DOWNLOAD_PATH = os.path.join(FTP_FILES_ROOT, "dentalheld", "downloads")
DENTALHELD_UPLOAD_PATH = os.path.join(FTP_FILES_ROOT, "dentalheld", "uploads")


# AERA API CONFIG
AERA_BASE_URL = os.getenv("AERA_BASE_URL")
AERA_COMPANY_ID = os.getenv("AERA_COMPANY_ID")
AERA_LOGIN_NAME = os.getenv("AERA_LOGIN_NAME")
AERA_PASSWORD = os.getenv("AERA_PASSWORD")

# SHOPWARE API CONFIG
SHOPWARE_BASE_URL = os.getenv("SHOPWARE_BASE_URL")
SHOPWARE_USERNAME = os.getenv("SHOPWARE_USERNAME")
SHOPWARE_ACCESS_ID = os.getenv("SHOPWARE_ACCESS_ID")
SHOPWARE_ACCESS_KEY = os.getenv("SHOPWARE_ACCESS_KEY")
SHOPWARE_EUR_CURRENCY_ID = "b7d2554b0ce847cd82f3ac9bd1c0dfca"
SHOPWARE_GIFT_RULE_ID = ""

# DENTALHELD API CONFIG
DENTALHELD_BASE_URL = os.getenv("DENTALHELD_BASE_URL")
DENTALHELD_API_KEY = os.getenv("DENTALHELD_API_KEY")

# DENTALHELD FTP CONFIG
DENTALHELD_FTP_HOST = os.getenv("DENTALHELD_FTP_HOST")
DENTALHELD_FTP_USER = os.getenv("DENTALHELD_FTP_USER")
DENTALHELD_FTP_PASSWORD = os.getenv("DENTALHELD_FTP_PASSWORD")
DENTALHELD_FTP_PORT = os.getenv("DENTALHELD_FTP_PORT")
DENTALHELD_FILE_UPDATE_CSV = "update.csv"


# GLS FTP CONFIG
GLS_FTP_HOST = os.getenv("GLS_FTP_HOST")
GLS_FTP_USER = os.getenv("GLS_FTP_USER")
GLS_FTP_PASSWORD = os.getenv("GLS_FTP_PASSWORD")
GLS_FTP_PORT = os.getenv("GLS_FTP_PORT")
GLS_FTP_PATH_OUTGOING = os.getenv("GLS_FTP_PATH_OUTGOING")
GLS_FTP_PATH_INCOMING = os.getenv("GLS_FTP_PATH_INCOMING")
GLS_FILE_AS316 = ".316"
GLS_FILE_LB315 = ".315"
GLS_FILE_PL317 = ".317"
GLS_FILE_LS320 = ".320"
GLS_FILE_NO304 = ".304"
GLS_FILE_X310 = ".310"
GLS_FILE_501 = ".501"
GLS_FILE_502 = ".502"
GLS_FILE_503 = ".503"
GLS_FILE_101 = "101"
GLS_FILE_102 = "102"
GLS_DOWNLOAD_FILES_EXT = [
    GLS_FILE_AS316,
    GLS_FILE_LB315,
    GLS_FILE_PL317,
    GLS_FILE_LS320,
    GLS_FILE_NO304,
    GLS_FILE_X310,
    GLS_FILE_501,
    GLS_FILE_502,
    GLS_FILE_503,
]

GLS_UPLOAD_FILES = [GLS_FILE_101, GLS_FILE_102]


# WAWIBOX FTP CONFIG
WAWIBOX_FTP_HOST = os.getenv("WAWIBOX_FTP_HOST")
WAWIBOX_FTP_USER = os.getenv("WAWIBOX_FTP_USER")
WAWIBOX_FTP_PASSWORD = os.getenv("WAWIBOX_FTP_PASSWORD")
WAWIBOX_FTP_PORT = os.getenv("WAWIBOX_FTP_PORT")
WAWIBOX_FTP_PATH_DOWNLOADS = os.getenv("WAWIBOX_FTP_PATH_DOWNLOADS")
WAWIBOX_FTP_PATH_UPLOADS = os.getenv("WAWIBOX_FTP_PATH_UPLOADS")
WAWIBOX_FILE_UPLOAD = ""
WAWIBOX_FILE_PRICE_COMPARISON_SUFFIX = "price_comparison"
WAWIBOX_FILE_MARKETPLACE_PREFIX = "marketplace"

WAWIBOX_DOWNLOAD_FILES_PATTERNS = [
    WAWIBOX_FILE_PRICE_COMPARISON_SUFFIX,
    WAWIBOX_FILE_MARKETPLACE_PREFIX,
]

WAWIBOX_UPLOAD_FILES = [WAWIBOX_FILE_UPLOAD]


# WECLAPP API CONFIG
WECLAPP_BASE_URL = os.getenv("WECLAPP_BASE_URL")
WECLAPP_API_TOKEN = os.getenv("WECLAPP_API_TOKEN")
WECLAPP_SHIPPING_ARTICLE_MAP = {
    "DE": "SHIP001",
    "AT": "SHIP003",
    "NL": "SHIP005",
    "BE": "SHIP005",
    "LU": "SHIP005",
    "DK": "SHIP006",
    "PL": "SHIP007",
    "HU": "SHIP008",
    "IT": "SHIP008",
    "FR": "SHIP008",
    "SK": "SHIP009",
    "SE": "SHIP010",
    "ES": "SHIP011",
    "HR": "SHIP012",
    "BG": "SHIP013",
    "RO": "SHIP013",
    "GR": "SHIP014",
    "EE": "SHIP015",
    "LT": "SHIP015",
    "LV": "SHIP015",
    "FI": "SHIP016",
    "CH": "SHIP017",
    "CZ": "SHIP018",
    "SI": "SHIP019",
}
