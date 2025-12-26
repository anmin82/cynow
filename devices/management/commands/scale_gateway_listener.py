"""
Scale Gateway API - Django Management Command

저울 TCP 리스너를 실행하는 커맨드

실행 방법:
    python manage.py scale_gateway_listener

systemd 유닛으로 관리 가능
"""
from django.core.management.base import BaseCommand
from django.conf import settings
import logging

from devices.scale_gateway.listener import ScaleGatewayListener

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scale Gateway API - TCP 저울 데이터 리스너 실행'
    
    def add_arguments(self, parser):
        """커맨드 인자 정의"""
        parser.add_argument(
            '--host',
            type=str,
            default=None,
            help='리스너 바인딩 주소 (기본값: settings.SCALE_GATEWAY_LISTEN_HOST)'
        )
        parser.add_argument(
            '--port',
            type=int,
            default=None,
            help='리스너 포트 (기본값: settings.SCALE_GATEWAY_LISTEN_PORT)'
        )
        parser.add_argument(
            '--scale-id',
            type=str,
            default='default',
            help='저울 식별자 (기본값: default)'
        )
    
    def handle(self, *args, **options):
        """커맨드 실행"""
        # 설정 로드
        host = options['host'] or getattr(settings, 'SCALE_GATEWAY_LISTEN_HOST', '0.0.0.0')
        port = options['port'] or getattr(settings, 'SCALE_GATEWAY_LISTEN_PORT', 4001)
        scale_id = options['scale_id']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'[Scale Gateway] 리스너 시작 중...\n'
                f'  - 주소: {host}:{port}\n'
                f'  - 저울 ID: {scale_id}'
            )
        )
        
        # 리스너 생성 및 실행
        listener = ScaleGatewayListener(
            host=host,
            port=port,
            scale_id=scale_id
        )
        
        try:
            listener.start()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('[Scale Gateway] Ctrl+C 감지, 종료 중...'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[Scale Gateway] 오류: {e}'))
            raise
        finally:
            listener.stop()
            self.stdout.write(self.style.SUCCESS('[Scale Gateway] 리스너 종료됨'))



















