"""
FCMS CDC 테이블 구조 확인 - 수주관리표 연동용
Django DB 연결 사용
"""
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.db import connection

print('=' * 80)
print('TR_ORDERS 테이블 구조')
print('=' * 80)

with connection.cursor() as cursor:
    cursor.execute('''
        SELECT column_name, data_type, character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'fcms_cdc' AND table_name = 'tr_orders'
        ORDER BY ordinal_position
    ''')
    for col in cursor.fetchall():
        length = f'({col[2]})' if col[2] else ''
        print(f'  {col[0]:40s} {col[1]}{length}')

print()
print('=' * 80)
print('TR_ORDER_INFORMATIONS 테이블 구조')
print('=' * 80)

with connection.cursor() as cursor:
    cursor.execute('''
        SELECT column_name, data_type, character_maximum_length
        FROM information_schema.columns
        WHERE table_schema = 'fcms_cdc' AND table_name = 'tr_order_informations'
        ORDER BY ordinal_position
    ''')
    for col in cursor.fetchall():
        length = f'({col[2]})' if col[2] else ''
        print(f'  {col[0]:40s} {col[1]}{length}')

# 샘플 데이터 확인
print()
print('=' * 80)
print('TR_ORDERS 샘플 데이터 (최근 5건)')
print('=' * 80)

with connection.cursor() as cursor:
    cursor.execute('''
        SELECT arrival_shipping_no, customer_order_no, trade_condition_code, 
               order_date, supplier_user_code
        FROM fcms_cdc.tr_orders 
        WHERE arrival_shipping_no IS NOT NULL
        ORDER BY arrival_shipping_no DESC 
        LIMIT 5
    ''')
    for row in cursor.fetchall():
        print(f'  {row}')

print()
print('=' * 80)
print('TR_ORDER_INFORMATIONS 샘플 데이터 (최근 5건)')
print('=' * 80)

with connection.cursor() as cursor:
    cursor.execute('''
        SELECT * FROM fcms_cdc.tr_order_informations
        ORDER BY id DESC
        LIMIT 5
    ''')
    colnames = [desc[0] for desc in cursor.description]
    print('컬럼: ' + ', '.join(colnames))
    print()
    for row in cursor.fetchall():
        print(f'  {row}')
