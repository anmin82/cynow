"""
devices 앱 뷰

Scale Gateway API - 저울 데이터 조회 및 커밋
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from .scale_gateway.state import get_state_manager
from .models import ScaleWeightLog

logger = logging.getLogger(__name__)


def _is_stale(received_at: datetime) -> bool:
    """
    최신 데이터가 오래되었는지 확인
    
    Args:
        received_at: 데이터 수신 시각
    
    Returns:
        IDLE_TIMEOUT을 초과하면 True
    """
    timeout = getattr(settings, 'SCALE_GATEWAY_IDLE_TIMEOUT_SEC', 10)
    now = timezone.now()
    age = (now - received_at).total_seconds()
    return age > timeout


@require_http_methods(["GET"])
def latest_weight(request):
    """
    Scale Gateway API - 최신 저울 데이터 조회
    
    GET /api/scale-gateway/latest/
    
    응답:
        {
            "ok": true,
            "scale_id": "default",
            "status": "ST",
            "weight": 53.26,
            "raw": "ST , +000053.26 _kg",
            "received_at": "2025-12-18T10:11:12+09:00",
            "stale": false
        }
    
    데이터 없으면:
        {
            "ok": false,
            "error": "no_data",
            "message": "저울 데이터가 없습니다"
        }
    """
    try:
        state_manager = get_state_manager()
        latest = state_manager.get_latest()
        
        if not latest:
            return JsonResponse({
                'ok': False,
                'error': 'no_data',
                'message': '저울 데이터가 없습니다'
            }, status=404)
        
        # Decimal을 float로 변환
        weight_value = float(latest['weight'])
        
        # stale 여부 확인
        stale = _is_stale(latest['received_at'])
        
        return JsonResponse({
            'ok': True,
            'scale_id': latest['scale_id'],
            'status': latest['status'],
            'weight': weight_value,
            'raw': latest['raw'],
            'received_at': latest['received_at'].isoformat(),
            'stale': stale
        })
    
    except Exception as e:
        logger.exception(f"[Scale Gateway API] latest_weight 오류: {e}")
        return JsonResponse({
            'ok': False,
            'error': 'internal_error',
            'message': str(e)
        }, status=500)


@csrf_exempt  # POC: 내부망 사용, 추후 인증 적용 권장
@require_http_methods(["POST"])
def commit_weight(request):
    """
    Scale Gateway API - 출하/회수 확정 (커밋)
    
    POST /api/scale-gateway/commit/
    
    요청 body:
        {
            "cylinder_no": "CY123456789",
            "event_type": "SHIP",  # SHIP | RETURN
            "arrival_shipping_no": "AS20251218-0001",  # optional
            "move_report_no": "MR20251218-0001"  # optional
        }
    
    응답:
        {
            "ok": true,
            "id": 123,
            "cylinder_no": "CY123456789",
            "event_type": "SHIP",
            "gross_kg": 53.26,
            "committed_at": "2025-12-18T10:11:12+09:00"
        }
    
    오류:
        - no_stable_weight: 안정값(ST) 없음
        - invalid_request: 요청 데이터 오류
    """
    try:
        # JSON 파싱
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'ok': False,
                'error': 'invalid_json',
                'message': 'JSON 파싱 실패'
            }, status=400)
        
        # 필수 파라미터 확인
        cylinder_no = data.get('cylinder_no', '').strip()
        event_type = data.get('event_type', '').strip().upper()
        
        if not cylinder_no:
            return JsonResponse({
                'ok': False,
                'error': 'invalid_request',
                'message': 'cylinder_no가 필요합니다'
            }, status=400)
        
        if event_type not in ['SHIP', 'RETURN']:
            return JsonResponse({
                'ok': False,
                'error': 'invalid_request',
                'message': 'event_type은 SHIP 또는 RETURN이어야 합니다'
            }, status=400)
        
        # 최신 안정값(ST) 가져오기
        state_manager = get_state_manager()
        latest_stable = state_manager.get_latest_stable()
        
        if not latest_stable:
            return JsonResponse({
                'ok': False,
                'error': 'no_stable_weight',
                'message': '안정된 저울 데이터(ST)가 없습니다'
            }, status=400)
        
        # 선택 파라미터
        arrival_shipping_no = data.get('arrival_shipping_no', '').strip() or None
        move_report_no = data.get('move_report_no', '').strip() or None
        
        # ScaleWeightLog 저장
        log = ScaleWeightLog.objects.create(
            scale_id=latest_stable['scale_id'],
            cylinder_no=cylinder_no,
            event_type=event_type,
            gross_kg=latest_stable['weight'],
            raw_line=latest_stable['raw'],
            received_at=latest_stable['received_at'],
            arrival_shipping_no=arrival_shipping_no,
            move_report_no=move_report_no
        )
        
        logger.info(
            f"[Scale Gateway API] 커밋 완료: "
            f"ID={log.id}, 용기={cylinder_no}, "
            f"이벤트={event_type}, 무게={log.gross_kg}kg"
        )
        
        return JsonResponse({
            'ok': True,
            'id': log.id,
            'cylinder_no': log.cylinder_no,
            'event_type': log.event_type,
            'gross_kg': float(log.gross_kg),
            'committed_at': log.committed_at.isoformat()
        })
    
    except Exception as e:
        logger.exception(f"[Scale Gateway API] commit_weight 오류: {e}")
        return JsonResponse({
            'ok': False,
            'error': 'internal_error',
            'message': str(e)
        }, status=500)
