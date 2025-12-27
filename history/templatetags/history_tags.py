from django import template

register = template.Library()


@register.filter
def dict_get(d: dict, key):
    """템플릿에서 dict[key] 접근용"""
    if not d:
        return ""
    return d.get(key, "")



















