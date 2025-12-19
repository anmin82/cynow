"""
수주 진행현황 집계 서비스

PO(customer_order_no) 기준으로 FCMS 실제 문서 집계
"""

from django.db import connection


def calculate_progress(customer_order_no):
    """
    진행현황 계산
    
    Args:
        customer_order_no: PO번호(고객발주번호)
    
    Returns:
        dict: {
            'order_qty': 수주수량,
            'instruction_qty': 충전지시수량,
            'filling_qty': 충전진행수량,
            'warehouse_in_qty': 입고수량,
            'shipping_qty': 출하수량,
            'current_stage': 현재단계텍스트
        }
    """
    
    from ..models import PO
    
    # 1. 수주수량: POItem 합계
    try:
        po = PO.objects.get(customer_order_no=customer_order_no)
        order_qty = po.total_qty
    except PO.DoesNotExist:
        order_qty = 0
    
    # 2. 충전지시수량: FCMS 충전지시 문서 합계
    instruction_qty = get_instruction_qty(customer_order_no)
    
    # 3. 충전진행수량: 이동서 상세 병 수
    filling_qty = get_filling_qty(customer_order_no)
    
    # 4. 입고수량: FCMS 입고 완료 문서 기준
    warehouse_in_qty = get_warehouse_in_qty(customer_order_no)
    
    # 5. 출하수량: FCMS 출하 완료 문서 기준
    shipping_qty = get_shipping_qty(customer_order_no)
    
    # 6. 현재 단계 판단
    current_stage = determine_stage(
        order_qty,
        instruction_qty,
        filling_qty,
        warehouse_in_qty,
        shipping_qty
    )
    
    return {
        'order_qty': order_qty,
        'instruction_qty': instruction_qty,
        'filling_qty': filling_qty,
        'warehouse_in_qty': warehouse_in_qty,
        'shipping_qty': shipping_qty,
        'current_stage': current_stage,
    }


def get_instruction_qty(customer_order_no):
    """충전지시수량 조회"""
    try:
        with connection.cursor() as cursor:
            query = """
                SELECT COALESCE(SUM(oi.INSTRUCTION_COUNT), 0)
                FROM fcms_cdc.TR_ORDERS_INFORMATIONS oi
                JOIN fcms_cdc.TR_ORDERS o ON oi.ORDERS_ID = o.id
                WHERE o.CUSTOMER_ORDER_NO = %s
            """
            cursor.execute(query, [customer_order_no])
            result = cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        print(f"충전지시수량 조회 실패: {e}")
        return 0


def get_filling_qty(customer_order_no):
    """충전진행수량 조회 (이동서 상세 병 수)"""
    try:
        with connection.cursor() as cursor:
            query = """
                SELECT COUNT(*)
                FROM fcms_cdc.TR_MOVE_REPORT_DETAILS mrd
                JOIN fcms_cdc.TR_MOVE_REPORTS mr ON mrd.MOVE_REPORTS_ID = mr.id
                JOIN fcms_cdc.TR_ORDERS o ON mr.ORDERS_ID = o.id
                WHERE o.CUSTOMER_ORDER_NO = %s
            """
            cursor.execute(query, [customer_order_no])
            result = cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        print(f"충전진행수량 조회 실패: {e}")
        return 0


def get_warehouse_in_qty(customer_order_no):
    """입고수량 조회"""
    # TODO: FCMS 입고 테이블 구조 확인 후 구현
    try:
        with connection.cursor() as cursor:
            # 임시: 이동서 상세 중 입고 완료된 것
            query = """
                SELECT COUNT(*)
                FROM fcms_cdc.TR_MOVE_REPORT_DETAILS mrd
                JOIN fcms_cdc.TR_MOVE_REPORTS mr ON mrd.MOVE_REPORTS_ID = mr.id
                JOIN fcms_cdc.TR_ORDERS o ON mr.ORDERS_ID = o.id
                WHERE o.CUSTOMER_ORDER_NO = %s
                -- TODO: 입고 완료 조건 추가
            """
            cursor.execute(query, [customer_order_no])
            result = cursor.fetchone()
            return result[0] if result else 0
    except Exception as e:
        print(f"입고수량 조회 실패: {e}")
        return 0


def get_shipping_qty(customer_order_no):
    """출하수량 조회"""
    # TODO: FCMS 출하 테이블 구조 확인 후 구현
    try:
        with connection.cursor() as cursor:
            # 임시: 출하 테이블 조회
            query = """
                SELECT COUNT(*)
                FROM fcms_cdc.[출하테이블]
                WHERE CUSTOMER_ORDER_NO = %s
            """
            # cursor.execute(query, [customer_order_no])
            # result = cursor.fetchone()
            # return result[0] if result else 0
            return 0  # 임시
    except Exception as e:
        print(f"출하수량 조회 실패: {e}")
        return 0


def determine_stage(order_qty, instruction_qty, filling_qty, warehouse_in_qty, shipping_qty):
    """
    현재 단계 판단
    
    Returns:
        str: 현재 단계 텍스트
    """
    if shipping_qty >= order_qty and order_qty > 0:
        return "완료"
    elif shipping_qty > 0:
        return "출하 진행중"
    elif warehouse_in_qty > 0:
        return "입고 진행중"
    elif filling_qty > 0:
        return "충전 진행중"
    elif instruction_qty > 0:
        return "충전 지시됨"
    else:
        return "대기중"


