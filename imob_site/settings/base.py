from pathlib import Path

import environ
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from apps.core.admin_navigation import site_settings_link

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-only-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
    "django_htmx",
    "django_filters",
    "rest_framework",
    "drf_spectacular",
    "django_tailwind_cli",
    "apps.core",
    "apps.properties",
    "apps.leads",
    "apps.people",
    "apps.crm",
    "apps.api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "imob_site.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "imob_site.wsgi.application"

DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Módulos do painel ligados neste site (env FEATURES="brokers,partners,owners,searches").
SITE_FEATURES = env.list("FEATURES", default=["brokers", "partners", "owners", "searches", "crm"])

# API aberta (módulo opcional `api`, desligado por padrão): chaves criadas no painel.
API_THROTTLE_RATE = env("API_THROTTLE_RATE", default="120/min")
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.api.authentication.ApiKeyAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["apps.api.permissions.ApiEnabled"],
    "DEFAULT_THROTTLE_CLASSES": ["apps.api.throttles.ApiKeyThrottle"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.api.pagination.Pagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "UNAUTHENTICATED_USER": None,
}
SPECTACULAR_SETTINGS = {
    "TITLE": "API do site",
    "DESCRIPTION": (
        "Envie contatos, consulte e atualize clientes do CRM e leia os imóveis publicados. "
        "Autentique com o header `Authorization: Api-Key <chave>` (chave criada no painel)."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
}

# Crédito no rodapé do site (None desliga).
DEVELOPER_CREDIT = {
    "name": "Gustavo Lopes",
    "instagram": "https://www.instagram.com/devlopes_guh/",
    "github": "https://github.com/guh99998",
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

MAILERS = {
    "default": {
        "BACKEND": env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"),
    },
}
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@imob-site.local")

UNFOLD = {
    "SITE_TITLE": "DevLopesMóveis",
    "SITE_HEADER": "DevLopesMóveis",
    "SITE_SUBHEADER": _("Painel de gestão"),
    "SITE_URL": "/",
    "SHOW_HISTORY": True,
    "THEME": "light",
    "SCRIPTS": ["apps.core.admin_navigation.masks_script"],
    "BORDER_RADIUS": "4px",
    "DASHBOARD_CALLBACK": "apps.core.admin_dashboard.dashboard_callback",
    # Paleta alinhada ao site público.
    "COLORS": {
        # Roxo de desenvolvedorgustavolopes.com.br (#6d28d9 = 700)
        "primary": {
            "50": "#f5f3ff",
            "100": "#ede9fe",
            "200": "#ddd6fe",
            "300": "#c4b5fd",
            "400": "#a78bfa",
            "500": "#8b5cf6",
            "600": "#7c3aed",
            "700": "#6d28d9",
            "800": "#5b21b6",
            "900": "#4c1d95",
            "950": "#2e1065",
        },
    },
    "SIDEBAR": {
        "show_search": False,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Início"),
                "separator": False,
                "items": [
                    {
                        "title": _("Painel"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            {
                "title": _("Imóveis"),
                "separator": True,
                "items": [
                    {
                        "title": _("Todos os imóveis"),
                        "icon": "home_work",
                        "link": reverse_lazy("admin:properties_property_changelist"),
                        "active": "apps.core.admin_navigation.all_properties_active",
                        "permission": "apps.core.admin_navigation.can_view_property",
                    },
                    {
                        "title": _("Cadastrar imóvel"),
                        "icon": "add_home",
                        "link": reverse_lazy("admin:properties_property_add"),
                        "active": "apps.core.admin_navigation.add_property_active",
                        "permission": "apps.core.admin_navigation.can_add_property",
                    },
                    {
                        "title": _("Categorias"),
                        "icon": "category",
                        "link": reverse_lazy("admin:properties_category_changelist"),
                        "permission": "apps.core.admin_navigation.can_view_category",
                    },
                    {
                        "title": _("Comodidades"),
                        "icon": "pool",
                        "link": reverse_lazy("admin:properties_feature_changelist"),
                        "permission": "apps.core.admin_navigation.can_view_feature",
                    },
                ],
            },
            {
                "title": _("Localização"),
                "separator": True,
                "items": [
                    {
                        "title": _("Cidades"),
                        "icon": "location_city",
                        "link": reverse_lazy("admin:properties_city_changelist"),
                        "permission": "apps.core.admin_navigation.can_view_city",
                    },
                    {
                        "title": _("Bairros"),
                        "icon": "map",
                        "link": reverse_lazy("admin:properties_neighborhood_changelist"),
                        "permission": "apps.core.admin_navigation.can_view_neighborhood",
                    },
                ],
            },
            {
                "title": _("Clientes"),
                "separator": True,
                "items": [
                    {
                        "title": _("Clientes"),
                        "icon": "contacts",
                        "link": reverse_lazy("admin:crm_client_changelist"),
                        "permission": "apps.core.admin_navigation.can_view_client",
                    },
                    {
                        "title": _("Retornos"),
                        "icon": "event_upcoming",
                        "link": "apps.core.admin_navigation.followups_link",
                        "badge": "apps.core.admin_navigation.overdue_followups_badge",
                        "permission": "apps.core.admin_navigation.can_view_followup",
                    },
                    {
                        "title": _("Documentos gerados"),
                        "icon": "description",
                        "link": reverse_lazy("admin:crm_generateddocument_changelist"),
                        "permission": "apps.core.admin_navigation.can_view_document",
                    },
                    {
                        "title": _("Modelos de documento"),
                        "icon": "edit_document",
                        "link": reverse_lazy("admin:crm_documenttemplate_changelist"),
                        "permission": "apps.core.admin_navigation.can_view_documenttemplate",
                    },
                ],
            },
            {
                "title": _("Pessoas"),
                "separator": True,
                "items": [
                    {
                        "title": _("Corretores"),
                        "icon": "badge",
                        "link": reverse_lazy("admin:people_broker_changelist"),
                        "permission": "apps.core.admin_navigation.can_view_broker",
                    },
                    {
                        "title": _("Parceiros"),
                        "icon": "handshake",
                        "link": reverse_lazy("admin:people_partner_changelist"),
                        "permission": "apps.core.admin_navigation.can_view_partner",
                    },
                    {
                        "title": _("Proprietários"),
                        "icon": "real_estate_agent",
                        "link": reverse_lazy("admin:people_owner_changelist"),
                        "permission": "apps.core.admin_navigation.can_view_owner",
                    },
                ],
            },
            {
                "title": _("Contatos"),
                "separator": True,
                "items": [
                    {
                        "title": _("Mensagens recebidas"),
                        "icon": "mail",
                        "link": reverse_lazy("admin:leads_lead_changelist"),
                        "badge": "apps.core.admin_navigation.new_leads_badge",
                        "permission": "apps.core.admin_navigation.can_view_lead",
                    },
                    {
                        "title": _("Procuras de clientes"),
                        "icon": "person_search",
                        "link": reverse_lazy("admin:leads_propertysearch_changelist"),
                        "badge": "apps.core.admin_navigation.new_searches_badge",
                        "permission": "apps.core.admin_navigation.can_view_search",
                    },
                    {
                        "title": _("Buscas no site"),
                        "icon": "trending_up",
                        "link": reverse_lazy("admin:properties_searchquery_changelist"),
                        "permission": "apps.core.admin_navigation.can_view_searchquery",
                    },
                ],
            },
            {
                "title": _("Configurações"),
                "separator": True,
                "items": [
                    {
                        "title": _("Dados da imobiliária"),
                        "icon": "storefront",
                        "link": site_settings_link,
                        "permission": "apps.core.admin_navigation.can_view_settings",
                    },
                    {
                        "title": _("Chaves de API"),
                        "icon": "key",
                        "link": reverse_lazy("admin:api_apikey_changelist"),
                        "permission": "apps.core.admin_navigation.can_view_apikey",
                    },
                    {
                        "title": _("Equipe"),
                        "icon": "group",
                        "link": reverse_lazy("admin:auth_user_changelist"),
                        "permission": "apps.core.admin_navigation.can_view_user",
                    },
                ],
            },
        ],
    },
}

TAILWIND_CLI_SRC_CSS = "frontend/source.css"
