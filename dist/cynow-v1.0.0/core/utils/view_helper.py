"""VIEW 데이터 처리 헬퍼 함수"""
import re
from typing import Dict, List, Optional
from core.utils.cylinder_type import generate_cylinder_type_key


def parse_cylinder_spec(cylinder_spec: Optional[str]) -> Dict[str, str]:
    """
    용기 스펙에서 형식과 재질 추출
    
    Args:
        cylinder_spec: 용기 스펙 문자열 (예: "BN SUS WELDING SHOT-Y In-screw")
    
    Returns:
        Dict: {'format': 'BN', 'material': 'SUS'}
    """
    if not cylinder_spec:
        return {'format': '', 'material': ''}
    
    spec_str = str(cylinder_spec).strip()
    
    # 형식 추출 (BN, YC 등)
    format_match = re.match(r'^([A-Z]+)', spec_str)
    format_type = format_match.group(1) if format_match else ''
    
    # 재질 추출
    materials = ['SUS', 'BRASS', 'Mn-St', 'CR-MO', 'CR-Mo', 'Cr-Mo', 'AL', 'STEEL', 'Ti', 'Cu', 'Mn-St']
    material = ''
    
    for mat in materials:
        if mat.upper() in spec_str.upper():
            material = mat
            break
    
    return {'format': format_type, 'material': material}


def parse_valve_spec(valve_spec: Optional[str]) -> Dict[str, str]:
    """
    밸브 스펙에서 형식과 재질 추출
    
    Args:
        valve_spec: 밸브 스펙 문자열 (예: "SUS general Y CGA330 Y NERIKI")
    
    Returns:
        Dict: {'format': 'CGA330', 'material': 'SUS'}
    """
    if not valve_spec:
        return {'format': '', 'material': ''}
    
    valve_str = str(valve_spec).strip()
    
    # 재질 추출 (앞부분)
    materials = ['SUS', 'BRASS', 'Mn-St', 'CR-MO', 'CR-Mo', 'Cr-Mo', 'AL', 'STEEL', 'Ti', 'Cu']
    material = ''
    
    for mat in materials:
        if valve_str.upper().startswith(mat.upper()):
            material = mat
            break
    
    # 형식 추출 (CGA, DISS, DIN 코드)
    format_type = extract_valve_type(valve_str)
    
    return {'format': format_type, 'material': material}


def parse_usage_place(usage_place: Optional[str], location: Optional[str] = None) -> str:
    """
    사용처 파싱 (KDKK/LGD 형식 지원)
    
    Args:
        usage_place: 사용처 문자열 (예: "000001", "LGD")
        location: 위치 문자열 (예: "KDKK")
    
    Returns:
        str: 파싱된 사용처 (예: "KDKK/LGD")
    """
    if not usage_place:
        return ''
    
    usage_str = str(usage_place).strip()
    
    # 이미 / 가 포함되어 있으면 그대로 반환
    if '/' in usage_str:
        return usage_str
    
    # location이 있고 usage_place가 짧은 코드면 조합
    if location and location.strip():
        location_str = str(location).strip()
        # location이 KDKK 같은 형식이고 usage_place가 코드면 조합
        if len(usage_str) <= 10 and location_str:  # usage_place가 짧은 코드인 경우
            return f"{location_str}/{usage_str}"
    
    # 코드 형식이면 그대로 반환
    return usage_str


def extract_valve_type(valve_spec: Optional[str]) -> str:
    """
    밸브 스펙에서 밸브 형식(CGA330, JIS-R 등) 추출
    
    Args:
        valve_spec: 밸브 스펙 문자열
    
    Returns:
        str: 추출된 밸브 형식 (예: "CGA330", "DISS724", "JIS-R")
    """
    import re
    if not valve_spec:
        return ''
    
    valve_str = str(valve_spec)
    
    # CGA 코드 패턴
    cga = re.search(r'CGA\s*-?\s*(\d+)', valve_str, re.IGNORECASE)
    if cga:
        return f"CGA{cga.group(1)}"
    
    # DISS 코드 패턴
    diss = re.search(r'DISS\s*-?\s*(\d+)', valve_str, re.IGNORECASE)
    if diss:
        return f"DISS{diss.group(1)}"
    
    # DIN 코드 패턴
    din = re.search(r'DIN\s*-?\s*(\d+)', valve_str, re.IGNORECASE)
    if din:
        return f"DIN{din.group(1)}"
    
    # JIS 코드 패턴 (JIS-R, JIS-B 등)
    jis = re.search(r'JIS\s*-?\s*([A-Z0-9-]+)', valve_str, re.IGNORECASE)
    if jis:
        return f"JIS-{jis.group(1)}"
    
    # 패턴 없으면 원본 반환
    return valve_str


def group_cylinder_types(inventory_data: List[Dict]) -> Dict[str, Dict]:
    """
    용기종류별로 데이터를 그룹화
    EndUser 정책에 따라 같은 EndUser를 가진 용기들은 하나의 카드로 합쳐짐
    
    Args:
        inventory_data: vw_cynow_inventory에서 조회한 데이터 리스트
    
    Returns:
        Dict: 그룹화된 용기종류 데이터
    """
    cylinder_types = {}
    
    for row in inventory_data:
        gas_name = row.get('gas_name', '')
        capacity = row.get('capacity') or ''
        valve_spec = row.get('valve_spec', '')
        valve_type = extract_valve_type(valve_spec)
        cylinder_spec = row.get('cylinder_spec', '')
        enduser = row.get('enduser', '') or ''
        
        # 그룹 키 (EndUser 포함 - EndUser가 다르면 별도 카드로 분리)
        group_key = f"{gas_name}|{capacity}|{valve_type}|{cylinder_spec}|{enduser}"
        
        if group_key not in cylinder_types:
            # 용기 스펙 파싱
            cylinder_parsed = parse_cylinder_spec(cylinder_spec)
            # 밸브 스펙 파싱 (원본 스펙 우선 사용 - 그룹명은 재질 추출 불가)
            valve_spec_raw = row.get('valve_spec_raw', '') or valve_spec
            valve_parsed = parse_valve_spec(valve_spec_raw)
            
            cylinder_types[group_key] = {
                'cylinder_type_key': row.get('cylinder_type_key', ''),
                'gas_name': gas_name,
                'capacity': capacity,
                'valve_type': valve_type,
                'valve_spec': valve_spec,  # 전체 밸브 스펙
                'valve_format': valve_parsed['format'],
                'valve_material': valve_parsed['material'],
                'cylinder_spec': cylinder_spec,
                'cylinder_format': cylinder_parsed['format'],
                'cylinder_material': cylinder_parsed['material'],
                'usage_place': enduser,  # EndUser를 usage_place로 표시 (하위 호환성)
                'statuses': {},
                'total_qty': 0,
                'available_qty': 0,
            }
        
        status = row.get('status', '')
        qty = row.get('qty', 0)
        
        # 상태별 수량 누적
        if status in cylinder_types[group_key]['statuses']:
            cylinder_types[group_key]['statuses'][status] += qty
        else:
            cylinder_types[group_key]['statuses'][status] = qty
        
        cylinder_types[group_key]['total_qty'] += qty
        
        # 가용수량 계산 (보관 + 충전)
        if status in ['보관', '충전']:
            cylinder_types[group_key]['available_qty'] += qty
    
    # 가용 수량이 0이어도 카드는 표시 (필터링 제거)
    # 고아 데이터는 get_inventory_summary에서 이미 제외됨
    
    return cylinder_types


def calculate_risk_level(available_qty: int, total_qty: int, abnormal_qty: int = 0, disposal_qty: int = 0) -> str:
    """
    위험도 레벨 계산
    
    Args:
        available_qty: 가용 수량
        total_qty: 총 수량
        abnormal_qty: 이상 수량
        disposal_qty: 폐기 수량
    
    Returns:
        str: HIGH, MEDIUM, LOW, NORMAL
    """
    if total_qty == 0:
        return 'NORMAL'
    
    # 이상/폐기 수량이 있으면 HIGH
    if abnormal_qty > 0 or disposal_qty > 0:
        return 'HIGH'
    
    # 가용 수량이 0이면 HIGH
    if available_qty == 0:
        return 'HIGH'
    
    # 가용 수량 비율 계산
    available_ratio = available_qty / total_qty
    
    if available_ratio < 0.1:  # 10% 미만
        return 'HIGH'
    elif available_ratio < 0.2:  # 20% 미만
        return 'MEDIUM'
    elif available_ratio < 0.3:  # 30% 미만
        return 'LOW'
    else:
        return 'NORMAL'



