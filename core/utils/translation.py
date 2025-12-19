"""다국어 번역 유틸리티"""
from typing import Optional
from core.models import Translation


# 현재 언어 설정 (기본: 한국어)
_current_language = 'ko'


def set_language(lang: str):
    """현재 언어 설정"""
    global _current_language
    _current_language = lang


def get_language() -> str:
    """현재 언어 반환"""
    return _current_language


def translate_text(field_type: str, source_text: Optional[str], lang: Optional[str] = None, default: Optional[str] = None) -> Optional[str]:
    """
    원본 텍스트를 지정 언어로 번역
    
    Args:
        field_type: 필드 타입 (gas_name, valve_spec, cylinder_spec, usage_place, location)
        source_text: FCMS 원본 텍스트
        lang: 대상 언어 (ko, ja, en) - None이면 현재 언어 사용
        default: 번역이 없을 때 반환할 기본값 (None이면 원문 반환)
    
    Returns:
        str: 번역된 텍스트 또는 기본값/원문
    """
    if not source_text:
        return default or source_text
    
    # 언어 결정
    target_lang = lang or _current_language
    
    # 공백 제거 및 정규화
    normalized_text = str(source_text).strip()
    if not normalized_text:
        return default or source_text
    
    # 번역 테이블에서 조회
    try:
        translation = Translation.objects.filter(
            field_type=field_type,
            source_text__iexact=normalized_text,  # 대소문자 구분 없음
            is_active=True
        ).first()
        
        if translation:
            return translation.get_display(target_lang)
    except Exception:
        # DB 에러 시 원문 반환
        pass
    
    # 번역이 없으면 기본값 또는 원문 반환
    return default if default is not None else source_text


def translate_dict(data: dict, field_types: Optional[list] = None, lang: Optional[str] = None) -> dict:
    """
    딕셔너리의 여러 필드를 한번에 번역
    
    Args:
        data: 번역할 딕셔너리
        field_types: 번역할 필드 타입 리스트 (None이면 모든 필드 타입 시도)
        lang: 대상 언어
    
    Returns:
        dict: 번역된 딕셔너리 (원본 수정 없이 새 딕셔너리 반환)
    """
    if field_types is None:
        field_types = ['gas_name', 'valve_spec', 'cylinder_spec', 'usage_place', 'location']
    
    translated = data.copy()
    
    # 필드 타입별 매핑
    field_mapping = {
        'gas_name': 'gas_name',
        'valve_spec': 'valve_spec',
        'cylinder_spec': 'cylinder_spec',
        'usage_place': 'usage_place',
        'location': 'location',
    }
    
    for field_type in field_types:
        if field_type in field_mapping:
            field_name = field_mapping[field_type]
            if field_name in translated:
                translated[field_name] = translate_text(
                    field_type,
                    translated[field_name],
                    lang=lang,
                    default=translated[field_name]  # 번역 없으면 원문 유지
                )
    
    return translated


def translate_list(data_list: list, field_types: Optional[list] = None, lang: Optional[str] = None) -> list:
    """
    딕셔너리 리스트의 모든 항목을 번역
    
    Args:
        data_list: 번역할 딕셔너리 리스트
        field_types: 번역할 필드 타입 리스트
        lang: 대상 언어
    
    Returns:
        list: 번역된 딕셔너리 리스트
    """
    return [translate_dict(item, field_types, lang) for item in data_list]


def get_or_create_translation(field_type: str, source_text: str, display_ko: str = None, 
                               display_ja: str = None, display_en: str = None) -> tuple:
    """
    번역을 가져오거나 생성
    
    Args:
        field_type: 필드 타입
        source_text: FCMS 원본 텍스트
        display_ko: 한국어 표시명
        display_ja: 일본어 표시명 (선택)
        display_en: 영어 표시명 (선택)
    
    Returns:
        tuple: (Translation 객체, created 여부)
    """
    normalized_source = str(source_text).strip()
    
    if not normalized_source:
        return None, False
    
    translation, created = Translation.objects.get_or_create(
        field_type=field_type,
        source_text__iexact=normalized_source,
        defaults={
            'source_text': normalized_source,
            'display_ko': display_ko or normalized_source,  # 번역 없으면 원문
            'display_ja': display_ja,
            'display_en': display_en,
            'is_active': True,
        }
    )
    
    # 기존 번역이 있고 표시명이 제공된 경우 업데이트
    if not created:
        updated = False
        if display_ko and translation.display_ko != display_ko:
            translation.display_ko = display_ko
            updated = True
        if display_ja and translation.display_ja != display_ja:
            translation.display_ja = display_ja
            updated = True
        if display_en and translation.display_en != display_en:
            translation.display_en = display_en
            updated = True
        if updated:
            translation.save()
    
    return translation, created
