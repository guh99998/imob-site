from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = env("SECRET_KEY")  # noqa: F405
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")  # noqa: F405
# healthcheck do contêiner chama localhost; de fora o Caddy só repassa os domínios dele
ALLOWED_HOSTS += ["localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])  # noqa: F405

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SECURE_REDIRECT_EXEMPT = [r"^healthz/$"]  # healthcheck do contêiner fala HTTP
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True

if env("AWS_STORAGE_BUCKET_NAME", default=""):  # noqa: F405
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")  # noqa: F405
    AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default=None)  # noqa: F405
    AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN", default=None)  # noqa: F405
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = False
    STORAGES["default"] = {"BACKEND": "storages.backends.s3.S3Storage"}  # noqa: F405

MAILERS = {
    "default": {
        "BACKEND": env(  # noqa: F405
            "EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend"
        ),
        "OPTIONS": {
            "host": env("EMAIL_HOST", default="localhost"),  # noqa: F405
            "port": env.int("EMAIL_PORT", default=587),  # noqa: F405
            "username": env("EMAIL_HOST_USER", default=""),  # noqa: F405
            "password": env("EMAIL_HOST_PASSWORD", default=""),  # noqa: F405
            "use_tls": env.bool("EMAIL_USE_TLS", default=True),  # noqa: F405
        },
    },
}

# WhiteNoise serve os estáticos (collectstatic) apenas em produção.
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
