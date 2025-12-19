from django import template
import re
from core.utils.translation import translate_text

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """딕셔너리에서 키로 값을 가져오는 필터"""
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def extract_material(spec_string):
    """용기스펙 문자열에서 재질 코드만 추출"""
    if not spec_string:
        return "-"
    
    # 주요 재질 코드 리스트
    materials = ['SUS', 'BRASS', 'Mn-St', 'Cr-Mo', 'BN', 'YC', 'AL', 'STEEL', 'Ti', 'Cu']
    
    spec_upper = str(spec_string).upper()
    found = []
    
    for mat in materials:
        if mat.upper() in spec_upper:
            found.append(mat)
    
    if found:
        return ' '.join(found)
    
    # 재질을 찾지 못하면 앞부분만 잘라서 표시
    spec_str = str(spec_string)
    if len(spec_str) > 10:
        return spec_str[:8] + "…"
    return spec_str


@register.filter
def extract_valve(valve_string):
    """밸브스펙 문자열에서 CGA 코드 추출"""
    if not valve_string:
        return "-"
    
    import re
    valve_str = str(valve_string)
    
    # CGA 코드 패턴 추출 (CGA + 숫자)
    cga_pattern = re.search(r'CGA\s*-?\s*(\d+)', valve_str, re.IGNORECASE)
    if cga_pattern:
        return f"CGA{cga_pattern.group(1)}"
    
    # DISS 코드 패턴
    diss_pattern = re.search(r'DISS\s*-?\s*(\d+)', valve_str, re.IGNORECASE)
    if diss_pattern:
        return f"DISS{diss_pattern.group(1)}"
    
    # DIN 코드 패턴
    din_pattern = re.search(r'DIN\s*-?\s*(\d+)', valve_str, re.IGNORECASE)
    if din_pattern:
        return f"DIN{din_pattern.group(1)}"
    
    # 패턴을 찾지 못하면 앞부분만 표시
    if len(valve_str) > 10:
        return valve_str[:8] + "…"
    return valve_str


@register.filter
def short_spec(spec_string, max_len=8):
    """스펙 문자열을 짧게 축약"""
    if not spec_string:
        return "-"
    
    spec_str = str(spec_string)
    if len(spec_str) > max_len:
        return spec_str[:max_len-1] + "…"
    return spec_str


@register.filter
def translate(field_value, field_type):
    """
    필드 값을 번역
    
    Usage:
        {{ cylinder.gas_name|translate:"gas_name" }}
        {{ cylinder.location|translate:"location" }}
    """
    if not field_value:
        return field_value
    
    return translate_text(field_type, field_value, default=field_value)


@register.filter
def translate_gas_name(value):
    """가스명 번역"""
    return translate_text('gas_name', value, default=value)


@register.filter
def translate_valve_spec(value):
    """밸브 스펙 번역"""
    return translate_text('valve_spec', value, default=value)


@register.filter
def translate_cylinder_spec(value):
    """용기 스펙 번역"""
    return translate_text('cylinder_spec', value, default=value)


@register.filter
def translate_usage_place(value):
    """사용처 번역"""
    return translate_text('usage_place', value, default=value)


@register.filter
def translate_location(value):
    """위치 번역"""
    return translate_text('location', value, default=value)


@register.filter
def format_usage_place(value):
    """사용처 포맷팅 (KDKK/LGD 형식)"""
    if not value:
        return "-"
    
    usage_str = str(value)
    # 이미 / 가 포함되어 있으면 그대로 반환
    if '/' in usage_str:
        return usage_str
    return usage_str


@register.filter
def parse_cylinder_spec(value):
    """용기 스펙 파싱"""
    from core.utils.view_helper import parse_cylinder_spec as parse_func
    if not value:
        return {'format': '', 'material': ''}
    return parse_func(value)


@register.filter
def parse_valve_spec(value):
    """밸브 스펙 파싱"""
    from core.utils.view_helper import parse_valve_spec as parse_func
    if not value:
        return {'format': '', 'material': ''}
    return parse_func(value)


@register.filter
def format_capacity(value):
    """용량을 정수 + L 단위로 표시"""
    if not value and value != 0:
        return "-"
    
    try:
        # 소수점 제거하고 정수로 변환
        capacity_int = int(float(value))
        return f"{capacity_int}L"
    except (ValueError, TypeError):
        return str(value)

