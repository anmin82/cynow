#!/usr/bin/env python
"""기본 회사정보 데이터 생성"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from voucher.models import CompanyInfo

# 자사 정보
company, created = CompanyInfo.objects.get_or_create(
    code='KDFPK',
    defaults={
        'name': 'KDFPK Co., Ltd.',
        'name_en': 'KDFPK Co., Ltd.',
        'is_supplier': True,
        'is_customer': False,
        'is_active': True,
    }
)
print(f"KDFPK (supplier): {'created' if created else 'exists'}")

# KDKK 거래처
company, created = CompanyInfo.objects.get_or_create(
    code='KDKK',
    defaults={
        'name': 'KDKK',
        'name_en': 'Kanto Denka Kogyo Co., Ltd.',
        'name_jp': '関東電化工業株式会社',
        'is_supplier': False,
        'is_customer': True,
        'is_active': True,
    }
)
print(f"KDKK (customer): {'created' if created else 'exists'}")

print("Done!")

