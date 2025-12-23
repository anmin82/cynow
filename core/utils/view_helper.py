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
        valve_spec: 밸브 스펙 문자열 (예: "SUS general Y CGA330 Y NERIKI", "COS_CGA330")
    
    Returns:
        Dict: {'format': 'CGA330', 'material': 'SUS'}
    """
    if not valve_spec:
        return {'format': '', 'material': ''}
    
    valve_str = str(valve_spec).strip()
    
    # 재질 추출 (앞부분) - COS 등 추가 재질 포함
    materials = ['SUS', 'BRASS', 'Mn-St', 'CR-MO', 'CR-Mo', 'Cr-Mo', 'AL', 'STEEL', 'Ti', 'Cu', 'COS', 'SS']
    material = ''
    
    # _ 구분자 처리 (예: COS_CGA330)
    if '_' in valve_str:
        parts = valve_str.split('_')
        if len(parts) >= 2:
            material = parts[0]
            format_type = extract_valve_type(parts[1])
            if format_type:
                return {'format': format_type, 'material': material}
    
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
    EndUserDefault 정책 기준으로 그룹화 (가스명 + 용량 + 밸브 + 용기 + EndUser)
    
    Args:
        inventory_data: vw_cynow_inventory에서 조회한 데이터 리스트
    
    Returns:
        Dict: 그룹화된 용기종류 데이터
    """
    cylinder_types = {}
    
    for row in inventory_data:
        # EndUserDefault 정책과 일치하도록 그룹 키 생성
        # 밸브 그룹이 있으면 그룹명 사용, 없으면 밸브 스펙 사용
        gas_name = (row.get('gas_name', '') or '').strip()
        capacity = row.get('capacity') or ''
        valve_spec = (row.get('valve_spec', '') or '').strip()  # 밸브 그룹명 또는 밸브 스펙
        cylinder_spec = (row.get('cylinder_spec', '') or '').strip()
        enduser = (row.get('enduser', '') or '').strip()
        
        # 그룹 키: 가스명 + 용량 + 밸브 + 용기 + EndUser
        group_key = f"{gas_name}|{capacity}|{valve_spec}|{cylinder_spec}|{enduser}"
        
        valve_type = extract_valve_type(valve_spec)
        
        row_type_key = row.get('cylinder_type_key', '') or ''

        if group_key not in cylinder_types:
            # 용기 스펙 파싱
            cylinder_parsed = parse_cylinder_spec(cylinder_spec)
            # 밸브 스펙 파싱 (원본 스펙 우선 사용 - 그룹명은 재질 추출 불가)
            valve_spec_raw = (row.get('valve_spec_raw', '') or valve_spec).strip()
            valve_parsed = parse_valve_spec(valve_spec_raw)
            
            cylinder_types[group_key] = {
                # 대표 키(기존 동작 유지): 최초 row의 키를 유지하되,
                # 실제 카드 집계가 여러 키를 합칠 수 있으므로 cylinder_type_keys로 전체 키를 함께 보관한다.
                'cylinder_type_key': row_type_key,
                'cylinder_type_keys': set([row_type_key]) if row_type_key else set(),
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
                'statuses_grouped': {},  # 통합된 상태 카운트 (UI 표시용)
                'total_qty': 0,
                'available_qty': 0,
            }
        else:
            # 같은 카드(속성 그룹)에 서로 다른 cylinder_type_key가 섞일 수 있음.
            # 리스트 이동 시 집계와 동일한 결과를 보장하기 위해 전체 키를 누적.
            if row_type_key:
                cylinder_types[group_key].setdefault('cylinder_type_keys', set()).add(row_type_key)
                # 대표 키는 deterministic 하게 가장 작은 값을 사용 (옵션/숨김키 안정화)
                cur_key = cylinder_types[group_key].get('cylinder_type_key', '') or ''
                if not cur_key or row_type_key < cur_key:
                    cylinder_types[group_key]['cylinder_type_key'] = row_type_key
        
        # 상태는 UI/JS에서 정해진 키로 조회되기도 하므로 공백/개행을 정규화하고,
        # 레거시 표기(예: '분석')는 사용자 표시용 상태로 정규화한다.
        status = (row.get('status', '') or '').strip()
        legacy_status_map = {
            # 레거시 '분석'은 진행 상태로 취급하여 '분석중'으로 표시한다.
            '분석': '분석중',
            # 레거시 '충전'은 진행 상태로 취급하여 '충전중'으로 표시한다.
            '충전': '충전중',
            '정비': '정비대상',
            # FCMS/DB 동기화 함수에서 500(倉入)이 '창입'으로 기록되는 경우가 있어
            # 화면/집계 표준 명칭인 '제품'으로 통일한다.
            '창입': '제품',
            '倉入': '제품',
            '倉入済': '제품',
        }
        status = legacy_status_map.get(status, status)
        qty = row.get('qty', 0)
        
        # 상태별 수량 누적 (세분화된 상태)
        if status in cylinder_types[group_key]['statuses']:
            cylinder_types[group_key]['statuses'][status] += qty
        else:
            cylinder_types[group_key]['statuses'][status] = qty
        
        # 통합된 상태 카운트 (UI 표시용)
        grouped_status = status
        if status in ('보관:미회수', '보관:회수'):
            grouped_status = '보관'
        elif status in ('충전중', '충전완료'):
            grouped_status = '충전중'
        elif status == '분석완료':
            grouped_status = '분석중'
        elif status == '정비대상':
            grouped_status = '정비'
        # 제품, 출하, 이상, 폐기는 그대로
        
        if grouped_status in cylinder_types[group_key]['statuses_grouped']:
            cylinder_types[group_key]['statuses_grouped'][grouped_status] += qty
        else:
            cylinder_types[group_key]['statuses_grouped'][grouped_status] = qty
        
        cylinder_types[group_key]['total_qty'] += qty
        
        # 가용수량 계산
        # - Repository가 이미 available_qty를 계산해 내려준다(권장).
        # - 과거/레거시 데이터에서는 status 문자열만으로 가용을 판단할 수도 있으므로 fallback 유지.
        row_available = row.get('available_qty', None)
        if row_available is not None:
            try:
                cylinder_types[group_key]['available_qty'] += int(row_available or 0)
            except Exception:
                # 예외 시 fallback 로직으로 처리
                pass
        else:
            # fallback: 상태 문자열 기반
            if status in ('보관', '보관:미회수', '보관:회수'):
                cylinder_types[group_key]['available_qty'] += qty
    
    # 가용 수량이 0이어도 카드는 표시 (필터링 제거)
    # 고아 데이터는 get_inventory_summary에서 이미 제외됨
    
    # set -> list (템플릿/JSON 직렬화 용)
    for k, v in cylinder_types.items():
        keys_set = v.get('cylinder_type_keys')
        if isinstance(keys_set, set):
            v['cylinder_type_keys'] = sorted([x for x in keys_set if x])
        elif not v.get('cylinder_type_keys'):
            # fallback
            rep = v.get('cylinder_type_key', '')
            v['cylinder_type_keys'] = [rep] if rep else []

        # 카드 하단 배지 표기용 상태 집계 (세부 상태 분리)
        # - 카드에서는 분석중/분석완료, 충전중/충전완료를 분리해서 보여준다.
        st = v.get('statuses', {}) or {}
        def _sum(*keys):
            return sum(int(st.get(key, 0) or 0) for key in keys)

        v['statuses_card'] = {
            # 보관은 상태가 아니라 "가용" 카테고리(미회수+회수 합)로만 표시한다.
            '보관': _sum('보관:미회수', '보관:회수'),
            '충전중': _sum('충전중'),
            '충전완료': _sum('충전완료'),
            '분석중': _sum('분석중'),
            '분석완료': _sum('분석완료'),
            '제품': _sum('제품'),
            '출하': _sum('출하'),
            '이상': _sum('이상'),
            '정비': _sum('정비대상'),
            '폐기': _sum('폐기'),
        }

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



