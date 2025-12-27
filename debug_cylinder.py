#!/usr/bin/env python
"""특정 용기 데이터 확인 스크립트"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

cylinder_no = 'E2018636'

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT 
            c."CYLINDER_NO",
            COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') as gas_name,
            c."CAPACITY",
            COALESCE(vs."NAME", '') as valve_spec,
            COALESCE(cs."NAME", '') as cylinder_spec,
            COALESCE(c."USE_DEPARTMENT_CODE", '') as usage_place,
            COALESCE(ls."POSITION_USER_NAME", '') as location,
            ls."CONDITION_CODE",
            ls."MOVE_DATE",
            c."WITHSTAND_PRESSURE_MAINTE_DATE",
            GREATEST(
                COALESCE(c."UPDATE_DATETIME", c."ADD_DATETIME"),
                COALESCE(ls."MOVE_DATE", NOW())
            ) as source_updated_at
        FROM "fcms_cdc"."ma_cylinders" c
        LEFT JOIN "fcms_cdc"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
        LEFT JOIN "fcms_cdc"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
        LEFT JOIN "fcms_cdc"."ma_valve_specs" vs ON c."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
        LEFT JOIN "fcms_cdc"."tr_latest_cylinder_statuses" ls ON c."CYLINDER_NO" = ls."CYLINDER_NO"
        WHERE c."CYLINDER_NO" = %s
    """, [cylinder_no])
    
    columns = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    
    print(f"용기번호: {cylinder_no}")
    print(f"컬럼 수: {len(columns)}")
    print(f"데이터 수: {len(row) if row else 0}")
    print("\n컬럼 목록:")
    for i, col in enumerate(columns):
        print(f"  [{i}] {col}")
    
    if row:
        print("\n데이터:")
        for i, (col, val) in enumerate(zip(columns, row)):
            print(f"  [{i}] {col}: {val}")
    else:
        print("\n데이터 없음")





















