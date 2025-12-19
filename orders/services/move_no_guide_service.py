"""
이동서번호 가이드 계산 서비스

⚠️ 중요:
- CYNOW는 번호를 발급하지 않음
- CDC로 확인한 FCMS 최신 번호 기준 +1 추천만 제공
- 실제 기준은 FCMS에 생성된 문서
"""

from datetime import datetime
from django.db import connection


def calculate_suggested_move_no():
    """
    추천 이동서번호 계산
    
    형식: FP + YY(년도 2자리) + 6자리 연번
    예시: FP250001
    
    Returns:
        str: 추천 이동서번호
    """
    
    # Step 1: 현재 연도
    current_year = datetime.now().strftime('%y')
    
    # Step 2: FCMS CDC에서 최신 이동서번호 조회
    try:
        with connection.cursor() as cursor:
            # TR_MOVE_REPORTS 테이블에서 올해 최대 번호 조회
            query = """
                SELECT MAX(MOVE_REPORT_NO) 
                FROM fcms_cdc.TR_MOVE_REPORTS
                WHERE MOVE_REPORT_NO LIKE %s
            """
            cursor.execute(query, [f'FP{current_year}%'])
            result = cursor.fetchone()
            latest_move_no = result[0] if result and result[0] else None
    except Exception as e:
        # CDC 연결 실패 시 기본값
        print(f"FCMS CDC 조회 실패: {e}")
        latest_move_no = None
    
    # Step 3: 번호 파싱 및 +1
    if latest_move_no:
        # 예: FP240123 → 123
        try:
            sequence_str = latest_move_no[4:]  # 'FP24' 이후
            sequence = int(sequence_str)
            next_sequence = sequence + 1
        except (ValueError, IndexError):
            # 파싱 실패 시 1부터 시작
            next_sequence = 1
    else:
        # FCMS에 올해 데이터 없으면 1부터 시작
        next_sequence = 1
    
    # Step 4: 추천 번호 생성
    suggested_no = f"FP{current_year}{next_sequence:06d}"
    
    return suggested_no


def check_fcms_match(customer_order_no, suggested_move_no):
    """
    FCMS 매칭 검증
    
    가이드 번호와 FCMS 실제 입력 번호 비교
    
    Args:
        customer_order_no: PO번호(고객발주번호)
        suggested_move_no: 추천 이동서번호
    
    Returns:
        dict: {
            'match_state': 'MATCHED' | 'NOT_ENTERED' | 'MISMATCH',
            'fcms_arrival_shipping_no': str or None,
            'fcms_move_report_no': str or None
        }
    """
    
    try:
        with connection.cursor() as cursor:
            # FCMS에서 실제 이동서 조회
            query = """
                SELECT 
                    mr.MOVE_REPORT_NO,
                    o.ARRIVAL_SHIPPING_NO
                FROM fcms_cdc.TR_MOVE_REPORTS mr
                LEFT JOIN fcms_cdc.TR_ORDERS o 
                    ON mr.ORDERS_ID = o.id
                WHERE o.CUSTOMER_ORDER_NO = %s
                LIMIT 1
            """
            cursor.execute(query, [customer_order_no])
            result = cursor.fetchone()
            
            if not result:
                # FCMS에 아직 미입력
                return {
                    'match_state': 'NOT_ENTERED',
                    'fcms_arrival_shipping_no': None,
                    'fcms_move_report_no': None
                }
            
            fcms_move_no, fcms_arrival_no = result
            
            # 매칭 판단
            if fcms_move_no == suggested_move_no:
                match_state = 'MATCHED'
            else:
                match_state = 'MISMATCH'
            
            return {
                'match_state': match_state,
                'fcms_arrival_shipping_no': fcms_arrival_no,
                'fcms_move_report_no': fcms_move_no
            }
            
    except Exception as e:
        print(f"FCMS 매칭 확인 실패: {e}")
        return {
            'match_state': 'NOT_ENTERED',
            'fcms_arrival_shipping_no': None,
            'fcms_move_report_no': None
        }


