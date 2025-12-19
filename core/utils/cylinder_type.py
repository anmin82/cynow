"""용기종류 관련 유틸리티"""
import hashlib


def generate_cylinder_type_key(gas_name, capacity, valve_spec, cylinder_spec, usage_place):
    """
    용기종류 키 생성 (가스명/용량/밸브/스펙/사용처 조합)
    
    Args:
        gas_name: 가스명
        capacity: 용기용량 (nullable)
        valve_spec: 밸브스펙 (nullable)
        cylinder_spec: 용기스펙 (nullable)
        usage_place: 사용처 (nullable)
    
    Returns:
        str: MD5 해시값 (32자)
    """
    key_string = f"{gas_name}|{capacity or ''}|{valve_spec or ''}|{cylinder_spec or ''}|{usage_place or ''}"
    return hashlib.md5(key_string.encode('utf-8')).hexdigest()

