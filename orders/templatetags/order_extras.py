"""
Orders 앱 템플릿 필터
"""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    딕셔너리에서 키로 값을 가져오는 필터
    
    사용법: {{ my_dict|get_item:"key_name" }}
    """
    if dictionary is None:
        return None
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def subtract(value, arg):
    """
    뺄셈 필터
    
    사용법: {{ value|subtract:arg }}
    """
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return value

