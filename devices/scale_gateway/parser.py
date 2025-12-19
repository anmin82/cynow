"""
Scale Gateway API - FG-150KAL 저울 데이터 파서

라인 포맷: "ST , +000053.26 _kg\r\n"
상태: ST (안정), US (불안정), OL (과부하)
"""
import re
import logging
from decimal import Decimal, InvalidOperation
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class ScaleDataParser:
    """
    FG-150KAL 저울 데이터 파서
    
    예시 라인:
    - "ST , +000053.26 _kg"
    - "US , +000053.26 _kg"
    - "OL , +000000.00 _kg"
    """
    
    # 정규식: "상태 , 부호숫자 _kg" 형식
    # 예: "ST , +000053.26 _kg"
    PATTERN = re.compile(
        r'^(?P<status>ST|US|OL)\s*,\s*'
        r'(?P<sign>[+-])'
        r'(?P<value>\d+(?:\.\d+)?)'
        r'\s*_?kg\s*$',
        re.IGNORECASE
    )
    
    @classmethod
    def parse_line(cls, line: str) -> Optional[Dict[str, any]]:
        """
        한 줄의 저울 데이터를 파싱
        
        Args:
            line: 저울에서 수신한 라인 (예: "ST , +000053.26 _kg")
        
        Returns:
            {
                'status': 'ST'|'US'|'OL',
                'weight': Decimal(53.26),
                'raw': 원본 라인
            }
            파싱 실패 시 None
        """
        if not line:
            return None
        
        # 공백 제거
        line_clean = line.strip()
        if not line_clean:
            return None
        
        match = cls.PATTERN.match(line_clean)
        if not match:
            logger.warning(f"파싱 실패 (포맷 불일치): {line_clean[:50]}")
            return None
        
        status = match.group('status').upper()
        sign = match.group('sign')
        value_str = match.group('value')
        
        # 숫자 변환
        try:
            weight_value = Decimal(value_str)
            if sign == '-':
                weight_value = -weight_value
        except (InvalidOperation, ValueError) as e:
            logger.error(f"숫자 변환 실패: {value_str}, 오류: {e}")
            return None
        
        return {
            'status': status,
            'weight': weight_value,
            'raw': line_clean
        }
    
    @classmethod
    def is_stable(cls, parsed_data: Optional[Dict]) -> bool:
        """
        안정 상태(ST)인지 확인
        
        Args:
            parsed_data: parse_line() 결과
        
        Returns:
            True if status == 'ST', False otherwise
        """
        if not parsed_data:
            return False
        return parsed_data.get('status') == 'ST'





