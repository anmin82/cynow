"""
Scale Gateway API - 최신 저울 데이터 저장소 (스레드 안전)

TCP 리스너가 수신한 최신 안정값(ST)을 메모리에 캐시하고,
API에서 조회할 수 있도록 제공
"""
import threading
from datetime import datetime, timezone
from typing import Optional, Dict
from decimal import Decimal


class ScaleStateManager:
    """
    최신 저울 데이터를 메모리에 저장하는 스레드 안전 싱글톤
    
    여러 스레드(TCP 리스너 + API 요청)에서 동시 접근 가능하도록
    threading.Lock으로 보호
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """싱글톤 패턴"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_state()
        return cls._instance
    
    def _init_state(self):
        """내부 상태 초기화"""
        self._data_lock = threading.Lock()
        self._latest_data: Optional[Dict] = None
    
    def update_latest(self, scale_id: str, status: str, weight: Decimal, raw_line: str):
        """
        최신 저울 데이터 업데이트
        
        Args:
            scale_id: 저울 식별자 (예: "default")
            status: 상태 (ST, US, OL)
            weight: 무게 (kg)
            raw_line: 원본 라인
        """
        with self._data_lock:
            self._latest_data = {
                'scale_id': scale_id,
                'status': status,
                'weight': weight,
                'raw': raw_line,
                'received_at': datetime.now(timezone.utc)
            }
    
    def get_latest(self) -> Optional[Dict]:
        """
        최신 저울 데이터 조회
        
        Returns:
            {
                'scale_id': 'default',
                'status': 'ST',
                'weight': Decimal(53.26),
                'raw': 'ST , +000053.26 _kg',
                'received_at': datetime(...)
            }
            데이터 없으면 None
        """
        with self._data_lock:
            if self._latest_data:
                # 딕셔너리 복사본 반환 (외부 수정 방지)
                return self._latest_data.copy()
            return None
    
    def get_latest_stable(self) -> Optional[Dict]:
        """
        최신 안정(ST) 데이터만 조회
        
        Returns:
            status == 'ST'인 최신 데이터, 없으면 None
        """
        latest = self.get_latest()
        if latest and latest.get('status') == 'ST':
            return latest
        return None
    
    def clear(self):
        """저장된 데이터 초기화 (테스트용)"""
        with self._data_lock:
            self._latest_data = None


# 싱글톤 인스턴스 생성 (모듈 로드 시 한 번만)
_state_manager = ScaleStateManager()


def get_state_manager() -> ScaleStateManager:
    """
    글로벌 ScaleStateManager 인스턴스 반환
    
    Returns:
        ScaleStateManager 싱글톤 인스턴스
    """
    return _state_manager

