"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

# 운영 배포 편의: systemd로 gunicorn 재시작 시 migrate/collectstatic 자동 수행
try:
    from django.conf import settings
    from pathlib import Path
    from core.utils.autodeploy import run_autodeploy_if_needed

    run_autodeploy_if_needed(base_dir=str(Path(__file__).resolve().parent.parent), debug=bool(getattr(settings, "DEBUG", True)))
except Exception:
    # WSGI 초기화는 절대 깨지지 않게 fail-safe
    pass