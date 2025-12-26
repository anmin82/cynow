"""
FCMS CDC 테이블 구조 확인 스크립트
"""
import psycopg2
import sys

# 출력 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')

try:
    # DB 연결
    conn = psycopg2.connect(
        host="10.78.30.98",
        port=5434,
        user="cynow",
        password="cynow2024!",  # 실제 비밀번호로 변경하세요
        database="cynow_db"
    )
    
    cursor = conn.cursor()
    
    # TR_ORDERS 테이블 구조 확인
    print("=" * 80)
    print("테이블: fcms_cdc.tr_orders")
    print("=" * 80)
    
    cursor.execute("""
        SELECT 
            column_name, 
            data_type, 
            character_maximum_length,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'fcms_cdc' 
        AND table_name = 'tr_orders'
        ORDER BY ordinal_position
    """)
    
    columns = cursor.fetchall()
    print(f"\n총 {len(columns)}개 컬럼:\n")
    for col in columns:
        col_name, data_type, max_length, nullable = col
        length_str = f"({max_length})" if max_length else ""
        print(f"  - {col_name:40s} {data_type}{length_str:20s} NULL={nullable}")
    
    # 데이터 샘플 조회
    print("\n" + "=" * 80)
    print("샘플 데이터 (최근 5건)")
    print("=" * 80)
    
    cursor.execute("""
        SELECT * FROM fcms_cdc.tr_orders 
        WHERE arrival_shipping_no LIKE 'FP%'
        ORDER BY arrival_shipping_no DESC 
        LIMIT 5
    """)
    
    rows = cursor.fetchall()
    colnames = [desc[0] for desc in cursor.description]
    
    print("\n컬럼명:")
    print(", ".join(colnames))
    print()
    
    for row in rows:
        print(row)
    
    # TR_ORDER_INFORMATIONS 테이블 구조 확인
    print("\n\n" + "=" * 80)
    print("테이블: fcms_cdc.tr_order_informations")
    print("=" * 80)
    
    cursor.execute("""
        SELECT 
            column_name, 
            data_type, 
            character_maximum_length,
            is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'fcms_cdc' 
        AND table_name = 'tr_order_informations'
        ORDER BY ordinal_position
    """)
    
    columns = cursor.fetchall()
    if columns:
        print(f"\n총 {len(columns)}개 컬럼:\n")
        for col in columns:
            col_name, data_type, max_length, nullable = col
            length_str = f"({max_length})" if max_length else ""
            print(f"  - {col_name:40s} {data_type}{length_str:20s} NULL={nullable}")
    else:
        print("\n테이블이 존재하지 않거나 컬럼이 없습니다.")
    
    cursor.close()
    conn.close()
    
    print("\n\n조회 완료!")
    
except Exception as e:
    print(f"오류 발생: {e}")
    import traceback
    traceback.print_exc()




















