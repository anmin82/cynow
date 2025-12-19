#!/usr/bin/env python
"""대시보드 수량 vs FCMS 수량 비교 스크립트"""
import os
import sys
import django

# Django 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from datetime import datetime

def execute_query(query, description):
    """쿼리 실행 및 결과 출력"""
    print(f"\n{'='*60}")
    print(f"📊 {description}")
    print('='*60)
    
    with connection.cursor() as cursor:
        cursor.execute(query)
        
        # 컬럼명 가져오기
        columns = [col[0] for col in cursor.description]
        
        # 결과 출력
        results = cursor.fetchall()
        
        if results:
            # 헤더 출력
            header = " | ".join(f"{col:20}" for col in columns)
            print(header)
            print("-" * len(header))
            
            # 데이터 출력
            for row in results:
                row_str = " | ".join(f"{str(val):20}" for val in row)
                print(row_str)
        else:
            print("결과 없음")
    
    return results

def main():
    print(f"\n🔍 CYNOW 대시보드 수량 진단 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1. cy_cylinder_current 총 개수
    execute_query(
        "SELECT COUNT(*) as cynow_total FROM cy_cylinder_current;",
        "1. cy_cylinder_current 총 개수"
    )
    
    # 2. fcms_cdc.ma_cylinders 총 개수
    execute_query(
        'SELECT COUNT(*) as fcms_total FROM "fcms_cdc"."ma_cylinders";',
        "2. FCMS CDC ma_cylinders 총 개수"
    )
    
    # 3. cy_cylinder_current 최근 업데이트 시간
    execute_query(
        "SELECT MAX(snapshot_updated_at) as last_update FROM cy_cylinder_current;",
        "3. cy_cylinder_current 최근 업데이트 시간"
    )
    
    # 4. JOIN 후 매칭되는 개수 (CYNOW 실제 사용)
    execute_query(
        """
        SELECT COUNT(*) as matched_count
        FROM cy_cylinder_current c
        INNER JOIN "fcms_cdc"."ma_cylinders" mc 
            ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
        WHERE c.dashboard_enduser IS NOT NULL;
        """,
        "4. JOIN 후 실제 매칭 개수 (dashboard_enduser NOT NULL)"
    )
    
    # 5. CYNOW 대시보드 상태별 집계
    execute_query(
        """
        SELECT 
            c.dashboard_status as status,
            COUNT(*) as qty
        FROM cy_cylinder_current c
        INNER JOIN "fcms_cdc"."ma_cylinders" mc 
            ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
        WHERE c.dashboard_enduser IS NOT NULL
        GROUP BY c.dashboard_status
        ORDER BY c.dashboard_status;
        """,
        "5. CYNOW 대시보드 상태별 집계"
    )
    
    # 6. ma_cylinders 테이블 구조 확인 (처음 5개 행)
    execute_query(
        """
        SELECT *
        FROM "fcms_cdc"."ma_cylinders"
        LIMIT 5;
        """,
        "6. FCMS ma_cylinders 샘플 데이터 (테이블 구조 확인)"
    )
    
    # 7. dashboard_enduser가 NULL인 개수
    execute_query(
        """
        SELECT COUNT(*) as null_enduser_count
        FROM cy_cylinder_current
        WHERE dashboard_enduser IS NULL;
        """,
        "7. dashboard_enduser가 NULL인 용기 개수"
    )
    
    # 8. JOIN이 안되는 용기 (cy_cylinder_current에는 있는데 ma_cylinders에 없는)
    execute_query(
        """
        SELECT COUNT(*) as orphan_count
        FROM cy_cylinder_current c
        LEFT JOIN "fcms_cdc"."ma_cylinders" mc 
            ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
        WHERE mc."CYLINDER_NO" IS NULL;
        """,
        "8. 고아 용기 (ma_cylinders에 없는 데이터)"
    )
    
    print("\n" + "="*60)
    print("✅ 진단 완료")
    print("="*60 + "\n")

if __name__ == '__main__':
    main()

