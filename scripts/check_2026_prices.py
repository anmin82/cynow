#!/usr/bin/env python
"""2026년 단가 데이터 확인 스크립트"""
import os
import sys
import django

# Django 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from products.models import ProductPriceHistory, ProductCode

# 2026년 단가 조회
prices_2026 = ProductPriceHistory.objects.filter(
    effective_date__year=2026
).select_related('product_code').order_by('product_code__trade_condition_no')

print(f'2026년 단가 건수: {prices_2026.count()}')
print()
print(f'{"코드":<8} | {"가스명":<18} | {"충전량":>6} | {"단가":>10} | 통화')
print('-' * 60)

for p in prices_2026:
    pc = p.product_code
    gas = pc.gas_name or ""
    weight = f"{pc.filling_weight or 0}kg"
    print(f'{pc.trade_condition_no:<8} | {gas:<18} | {weight:>6} | {p.price_per_kg:>10} | {p.currency}')

