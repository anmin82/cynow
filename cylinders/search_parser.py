"""
자연어 검색 파서 - 키워드 기반으로 필터 조건 변환
"""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional


# 상태 키워드 매핑
STATUS_KEYWORDS = {
    '보관': ['보관', '보관중', '저장', '창고'],
    '충전': ['충전', '충전중', '충전대기', '충전완료'],
    '분석': ['분석', '분석중', '검사', '검사중'],
    '창입': ['창입', '입고', '입고중'],
    '출하': ['출하', '출하중', '배송', '납품'],
    '이상': ['이상', '이상상태', '문제', '불량', '고장'],
    '정비': ['정비', '정비중', '수리', '점검'],
    '폐기': ['폐기', '폐기됨', '스크랩'],
}

# 위치 키워드 매핑
LOCATION_KEYWORDS = {
    'FPK': ['fpk', 'FPK', '천안', '천안공장'],
    'KDKK': ['kdkk', 'KDKK', '한국'],
}

# 내압/기간 관련 키워드
PRESSURE_KEYWORDS = {
    'expired': ['만료', '만료된', '만료됨', '지난', '초과'],
    'expiring_soon': ['임박', '곧만료', '만료임박', '곧'],
    'within_days': ['이내', '내', '안에'],
}

# 일반 검색어 → 가스명 패턴
GAS_PATTERNS = [
    r'\b(cos|COS|Cos)\b',
    r'\b(n2|N2|질소)\b',
    r'\b(o2|O2|산소)\b',
    r'\b(ar|Ar|AR|아르곤)\b',
    r'\b(he|He|HE|헬륨)\b',
    r'\b(h2|H2|수소)\b',
    r'\b(co2|CO2|이산화탄소|탄산)\b',
    r'\b(sf6|SF6)\b',
    r'\b(cf4|CF4)\b',
    r'\b(nf3|NF3)\b',
    r'\b(c4f8|C4F8)\b',
]


def parse_natural_query(query: str) -> Dict:
    """
    자연어 검색어를 필터 조건으로 변환
    
    Args:
        query: 자연어 검색어 (예: "COS 충전중인 용기")
    
    Returns:
        Dict: 파싱된 필터 조건과 메타데이터
    """
    query_lower = query.lower()
    result = {
        'filters': {},
        'parsed_keywords': [],
        'suggestions': [],
        'original_query': query,
    }
    
    # 1. 상태 파싱
    parsed_statuses = []
    for status, keywords in STATUS_KEYWORDS.items():
        for keyword in keywords:
            if keyword in query_lower or keyword in query:
                if status not in parsed_statuses:
                    parsed_statuses.append(status)
                    result['parsed_keywords'].append({
                        'type': 'status',
                        'value': status,
                        'matched': keyword
                    })
    
    if parsed_statuses:
        result['filters']['statuses'] = parsed_statuses
    
    # 2. 위치 파싱
    for location, keywords in LOCATION_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in query_lower:
                result['filters']['location'] = location
                result['parsed_keywords'].append({
                    'type': 'location',
                    'value': location,
                    'matched': keyword
                })
                break
    
    # 3. 가스명 파싱
    for pattern in GAS_PATTERNS:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            gas_keyword = match.group(1).upper()
            result['filters']['gas_keyword'] = gas_keyword
            result['parsed_keywords'].append({
                'type': 'gas_name',
                'value': gas_keyword,
                'matched': match.group(0)
            })
            break
    
    # 4. 내압만료 관련 파싱
    pressure_filter = parse_pressure_keywords(query_lower)
    if pressure_filter:
        result['filters'].update(pressure_filter)
        result['parsed_keywords'].append({
            'type': 'pressure',
            'value': pressure_filter,
            'matched': '내압관련'
        })
    
    # 5. 숫자 + 일 패턴 (예: "30일 이내")
    days_match = re.search(r'(\d+)\s*일', query)
    if days_match:
        days = int(days_match.group(1))
        if any(kw in query_lower for kw in ['이내', '내', '안에', '전']):
            result['filters']['days'] = days
            result['parsed_keywords'].append({
                'type': 'days',
                'value': days,
                'matched': days_match.group(0)
            })
    
    # 6. 추천 필터 생성
    result['suggestions'] = generate_suggestions(result['filters'], result['parsed_keywords'])
    
    return result


def parse_pressure_keywords(query: str) -> Optional[Dict]:
    """내압 관련 키워드 파싱"""
    result = {}
    
    if any(kw in query for kw in PRESSURE_KEYWORDS['expired']):
        if '내압' in query or '만료' in query:
            result['pressure_expired'] = True
            return result
    
    if any(kw in query for kw in PRESSURE_KEYWORDS['expiring_soon']):
        if '내압' in query or '만료' in query:
            result['pressure_expiring_soon'] = True
            result['pressure_days'] = 30  # 기본 30일
            return result
    
    return result if result else None


def generate_suggestions(filters: Dict, parsed_keywords: List) -> List[Dict]:
    """검색 결과에 기반한 추천 필터 생성"""
    suggestions = []
    
    # 상태가 없으면 상태 추천
    if 'statuses' not in filters:
        suggestions.append({
            'type': 'status',
            'label': '상태별로 보기',
            'options': ['보관', '충전', '출하', '이상']
        })
    
    # 위치가 없으면 위치 추천
    if 'location' not in filters:
        suggestions.append({
            'type': 'location',
            'label': '위치별로 보기',
            'options': ['FPK', 'KDKK']
        })
    
    # 내압 관련이 없으면 추천
    if 'pressure_expired' not in filters and 'pressure_expiring_soon' not in filters:
        suggestions.append({
            'type': 'pressure',
            'label': '내압 상태',
            'options': ['만료됨', '30일 이내 만료', '정상']
        })
    
    return suggestions


# 시나리오 프리셋
SCENARIO_PRESETS = {
    'pressure_expiring': {
        'name': '🚨 내압만료 임박',
        'description': '30일 이내 내압만료 예정',
        'filters': {'pressure_expiring_soon': True, 'pressure_days': 30},
        'color': 'danger'
    },
    'abnormal': {
        'name': '⚠️ 이상/정비',
        'description': '이상 또는 정비 상태',
        'filters': {'statuses': ['이상', '정비']},
        'color': 'warning'
    },
    'shipped_not_returned': {
        'name': '📦 출하 후 미회수',
        'description': '출하 상태로 30일 이상 경과',
        'filters': {'statuses': ['출하'], 'days_since_event': 30},
        'color': 'info'
    },
    'long_storage': {
        'name': '🔄 장기보관 90일+',
        'description': '보관 상태로 90일 이상',
        'filters': {'statuses': ['보관'], 'days_since_event': 90},
        'color': 'secondary'
    },
    'charging': {
        'name': '🏭 충전중',
        'description': '충전 상태 용기',
        'filters': {'statuses': ['충전']},
        'color': 'charging'
    },
    'storage': {
        'name': '📦 보관중',
        'description': '보관 상태 용기',
        'filters': {'statuses': ['보관']},
        'color': 'storage'
    },
    'shipped': {
        'name': '🚚 출하',
        'description': '출하 상태 용기',
        'filters': {'statuses': ['출하']},
        'color': 'shipped'
    },
    'recent_7days': {
        'name': '📅 최근 7일',
        'description': '최근 7일간 변경된 용기',
        'filters': {'days': 7},
        'color': 'info'
    },
    'today_changed': {
        'name': '📋 오늘 변경',
        'description': '오늘 상태가 변경된 용기',
        'filters': {'days': 1},
        'color': 'success'
    },
}


def get_scenario_presets() -> Dict:
    """시나리오 프리셋 목록 반환"""
    return SCENARIO_PRESETS


def apply_scenario(scenario_key: str) -> Dict:
    """시나리오 프리셋 적용"""
    if scenario_key in SCENARIO_PRESETS:
        return SCENARIO_PRESETS[scenario_key]['filters']
    return {}

