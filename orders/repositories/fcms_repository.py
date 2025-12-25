"""
FCMS CDC 테이블 조회 Repository

PostgreSQL fcms_cdc 스키마의 테이블을 직접 조회
Django ORM 대신 Raw SQL 사용 (CDC 테이블은 Django 모델로 정의되지 않음)

주요 테이블:
- TR_ORDERS: 주문 정보 (ARRIVAL_SHIPPING_NO, CUSTOMER_ORDER_NO, TRADE_CONDITION_CODE)
- TR_ORDER_INFORMATIONS: 주문 상세 품목 (INSTRUCTION_COUNT, ITEM_NAME, PACKING_NAME)
- TR_MOVE_REPORTS: 이동 보고서
- TR_MOVE_REPORT_DETAILS: 이동 보고서 상세

관계성:
- PO.customer_order_no = TR_ORDERS.CUSTOMER_ORDER_NO
- 하나의 PO에 여러 ARRIVAL_SHIPPING_NO 연결 (여러 번 생산/출하)
"""

from django.db import connection
from typing import Optional, List, Dict, Any
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class FcmsRepository:
    """FCMS CDC 데이터 조회"""
    
    # ============================================
    # 기본 조회 메서드
    # ============================================
    
    @staticmethod
    def get_latest_arrival_shipping_no() -> Optional[str]:
        """
        최신 도착출하번호 조회
        
        Returns:
            최신 ARRIVAL_SHIPPING_NO (예: FP25000668) 또는 None
        """
        query = '''
            SELECT "ARRIVAL_SHIPPING_NO"
            FROM fcms_cdc.tr_orders
            WHERE "ARRIVAL_SHIPPING_NO" IS NOT NULL
              AND "ARRIVAL_SHIPPING_NO" LIKE 'FP%%'
            ORDER BY "ARRIVAL_SHIPPING_NO" DESC
            LIMIT 1
        '''
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                row = cursor.fetchone()
                return row[0].strip() if row and row[0] else None
        except Exception as e:
            logger.warning(f"최신 도착출하번호 조회 실패: {e}")
            return None
    
    @staticmethod
    def get_next_move_no() -> str:
        """
        다음 이동서번호 추천
        
        이동서번호 형식: FP + 년도(2자리) + 연번(6자리)
        예: FP25000001, FP25000669
        
        Returns:
            추천 이동서번호 (예: FP25000669)
        """
        from datetime import datetime
        
        current_year = datetime.now().strftime('%y')  # 25
        prefix = f'FP{current_year}'
        
        query = '''
            SELECT "ARRIVAL_SHIPPING_NO"
            FROM fcms_cdc.tr_orders
            WHERE "ARRIVAL_SHIPPING_NO" IS NOT NULL
              AND "ARRIVAL_SHIPPING_NO" LIKE %s
            ORDER BY "ARRIVAL_SHIPPING_NO" DESC
            LIMIT 1
        '''
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, [f'{prefix}%'])
                row = cursor.fetchone()
                
                if row and row[0]:
                    latest_no = row[0].strip()
                    # FP25xxxxxx에서 숫자 부분 추출
                    # FP + 2자리 년도 = 4글자 이후가 연번
                    seq_part = latest_no[4:]  # 000668 등
                    try:
                        next_seq = int(seq_part) + 1
                        # 기존 자릿수 유지 (6자리)
                        seq_len = max(len(seq_part), 6)
                        return f'{prefix}{str(next_seq).zfill(seq_len)}'
                    except ValueError:
                        # 숫자 파싱 실패 시 기본값
                        return f'{prefix}000001'
                else:
                    # 해당 년도 첫 번호
                    return f'{prefix}000001'
        except Exception as e:
            logger.warning(f"다음 이동서번호 추천 실패: {e}")
            return f'{prefix}000001'
    
    @staticmethod
    def check_move_no_exists(move_no: str) -> bool:
        """
        이동서번호 중복 확인
        
        Args:
            move_no: 확인할 이동서번호
        
        Returns:
            True if exists, False otherwise
        """
        query = '''
            SELECT COUNT(*)
            FROM fcms_cdc.tr_orders
            WHERE TRIM("ARRIVAL_SHIPPING_NO") = %s
        '''
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, [move_no])
                row = cursor.fetchone()
                return row[0] > 0 if row else False
        except Exception as e:
            logger.warning(f"이동서번호 중복 확인 실패: {e}")
            return False
    
    @staticmethod
    def get_move_no_range_for_year(year: str = None) -> Dict[str, Any]:
        """
        해당 년도 이동서번호 범위 조회
        
        Args:
            year: 년도 (2자리), None이면 현재 년도
        
        Returns:
            {'min': 최소번호, 'max': 최대번호, 'count': 개수}
        """
        from datetime import datetime
        
        if year is None:
            year = datetime.now().strftime('%y')
        
        prefix = f'FP{year}'
        
        query = '''
            SELECT 
                MIN("ARRIVAL_SHIPPING_NO") as min_no,
                MAX("ARRIVAL_SHIPPING_NO") as max_no,
                COUNT(*) as cnt
            FROM fcms_cdc.tr_orders
            WHERE "ARRIVAL_SHIPPING_NO" IS NOT NULL
              AND "ARRIVAL_SHIPPING_NO" LIKE %s
        '''
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, [f'{prefix}%'])
                row = cursor.fetchone()
                
                if row:
                    return {
                        'min': row[0].strip() if row[0] else None,
                        'max': row[1].strip() if row[1] else None,
                        'count': int(row[2]) if row[2] else 0,
                    }
                return {'min': None, 'max': None, 'count': 0}
        except Exception as e:
            logger.warning(f"년도별 이동서번호 범위 조회 실패: {e}")
            return {'min': None, 'max': None, 'count': 0}
    
    @staticmethod
    def get_latest_move_report_no() -> Optional[str]:
        """
        최신 이동서번호 조회 (TR_ORDERS 기준)
        
        Returns:
            최신 ARRIVAL_SHIPPING_NO (예: FP25000668) 또는 None
        """
        # TR_ORDERS의 ARRIVAL_SHIPPING_NO가 이동서번호
        return FcmsRepository.get_latest_arrival_shipping_no()
    
    # ============================================
    # 수주별 생산 진척 조회 (수주관리표용)
    # ============================================
    
    @staticmethod
    def get_orders_by_customer_order_no(customer_order_no: str) -> List[Dict[str, Any]]:
        """
        고객주문번호(PO번호)로 연결된 모든 FCMS 주문 조회
        
        TR_ORDERS 테이블에서 CUSTOMER_ORDER_NO로 검색
        (TR_ORDERS에 품목 정보가 모두 포함되어 있음)
        
        Args:
            customer_order_no: PO번호(고객발주번호)
        
        Returns:
            연결된 FCMS 주문 리스트 (ARRIVAL_SHIPPING_NO별)
        """
        query = '''
            SELECT 
                "ARRIVAL_SHIPPING_NO",
                "CUSTOMER_ORDER_NO",
                "SUPPLIER_USER_CODE",
                "SUPPLIER_USER_NAME",
                "ORDER_DATE",
                "TRADE_CONDITION_CODE",
                "ORDER_REMARKS",
                "SELECTION_PATTERN_CODE",
                "ITEM_NAME",
                "PACKING_NAME",
                "INSTRUCTION_QUANTITY",
                "INSTRUCTION_COUNT",
                "FILLING_THRESHOLD",
                "DELIVERY_DATE",
                "MOVE_REPORT_REMARKS"
            FROM fcms_cdc.tr_orders
            WHERE TRIM("CUSTOMER_ORDER_NO") = %s
            ORDER BY "ARRIVAL_SHIPPING_NO"
        '''
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, [customer_order_no])
                rows = cursor.fetchall()
                
                return [
                    {
                        'arrival_shipping_no': row[0].strip() if row[0] else '',
                        'customer_order_no': row[1].strip() if row[1] else '',
                        'supplier_user_code': row[2].strip() if row[2] else '',
                        'supplier_user_name': row[3].strip() if row[3] else '',
                        'order_date': row[4],
                        'trade_condition_code': row[5].strip() if row[5] else '',
                        'order_remarks': row[6].strip() if row[6] else '',
                        'selection_pattern_code': row[7].strip() if row[7] else '',
                        'item_name': row[8].strip() if row[8] else '',
                        'packing_name': row[9].strip() if row[9] else '',
                        'instruction_quantity': float(row[10]) if row[10] else None,
                        'instruction_count': int(row[11]) if row[11] else 0,
                        'filling_threshold': float(row[12]) if row[12] else None,
                        'delivery_date': row[13],
                        'move_report_remarks': row[14].strip() if row[14] else '',
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.warning(f"고객주문번호별 FCMS 주문 조회 실패: {e}")
            return []
    
    @staticmethod
    def get_order_details_by_arrival_no(arrival_shipping_no: str) -> List[Dict[str, Any]]:
        """
        도착출하번호로 주문 상세 조회
        
        TR_ORDERS 테이블에서 직접 조회 (별도 상세 테이블 없음)
        
        Args:
            arrival_shipping_no: 도착출하번호
        
        Returns:
            품목별 상세 정보 리스트
        """
        query = '''
            SELECT 
                "ARRIVAL_SHIPPING_NO",
                "ITEM_NAME",
                "PACKING_NAME",
                "INSTRUCTION_QUANTITY",
                "INSTRUCTION_COUNT",
                "FILLING_THRESHOLD",
                "ORDER_REMARKS",
                "TRADE_CONDITION_CODE",
                "SELECTION_PATTERN_CODE",
                "DELIVERY_DATE",
                "MOVE_REPORT_REMARKS"
            FROM fcms_cdc.tr_orders
            WHERE TRIM("ARRIVAL_SHIPPING_NO") = %s
        '''
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, [arrival_shipping_no])
                rows = cursor.fetchall()
                
                return [
                    {
                        'arrival_shipping_no': row[0].strip() if row[0] else '',
                        'item_name': row[1].strip() if row[1] else '',
                        'packing_name': row[2].strip() if row[2] else '',
                        'instruction_quantity': float(row[3]) if row[3] else None,
                        'instruction_count': int(row[4]) if row[4] else 0,
                        'filling_threshold': float(row[5]) if row[5] else None,
                        'order_remarks': row[6].strip() if row[6] else '',
                        'trade_condition_code': row[7].strip() if row[7] else '',
                        'selection_pattern_code': row[8].strip() if row[8] else '',
                        'delivery_date': row[9],
                        'move_report_remarks': row[10].strip() if row[10] else '',
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.warning(f"도착출하번호별 주문 상세 조회 실패: {e}")
            return []
    
    @staticmethod
    def get_production_summary_by_customer_order_no(customer_order_no: str) -> Dict[str, Any]:
        """
        고객주문번호(PO번호)별 생산 진척 요약 조회 (제품코드별 그룹화)
        
        Args:
            customer_order_no: PO번호(고객발주번호)
        
        Returns:
            {
                'customer_order_no': PO번호,
                'products': {
                    'KF001': {
                        'trade_condition_code': 'KF001',
                        'item_name': 'COS',
                        'total_instruction_count': 30,
                        'orders': [이동서 목록]
                    }
                }
            }
        """
        orders = FcmsRepository.get_orders_by_customer_order_no(customer_order_no)
        
        # 제품코드(TRADE_CONDITION_CODE)별 그룹화
        products = {}
        for order in orders:
            trade_code = order.get('trade_condition_code', 'UNKNOWN') or 'UNKNOWN'
            
            if trade_code not in products:
                products[trade_code] = {
                    'trade_condition_code': trade_code,
                    'item_name': order.get('item_name', ''),
                    'packing_name': order.get('packing_name', ''),
                    'total_instruction_count': 0,
                    'orders': [],
                }
            
            products[trade_code]['orders'].append(order)
            products[trade_code]['total_instruction_count'] += order.get('instruction_count', 0) or 0
        
        return {
            'customer_order_no': customer_order_no,
            'products': products,
            'total_arrival_count': len(orders),
        }
    
    @staticmethod
    def get_all_customer_order_nos_with_progress() -> List[Dict[str, Any]]:
        """
        모든 고객주문번호와 진척 요약 조회 (수주관리표 목록용)
        
        Returns:
            [{customer_order_no, arrival_count, total_instruction_count, ...}]
        """
        query = '''
            SELECT 
                TRIM("CUSTOMER_ORDER_NO") as customer_order_no,
                COUNT(DISTINCT "ARRIVAL_SHIPPING_NO") as arrival_count,
                COALESCE(SUM("INSTRUCTION_COUNT"), 0) as total_instruction_count,
                MIN("ORDER_DATE") as first_order_date,
                MAX("ORDER_DATE") as last_order_date
            FROM fcms_cdc.tr_orders
            WHERE "CUSTOMER_ORDER_NO" IS NOT NULL
              AND TRIM("CUSTOMER_ORDER_NO") != ''
            GROUP BY TRIM("CUSTOMER_ORDER_NO")
            ORDER BY MAX("ORDER_DATE") DESC
            LIMIT 500
        '''
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
                
                return [
                    {
                        'customer_order_no': row[0],
                        'arrival_count': int(row[1]) if row[1] else 0,
                        'total_instruction_count': int(row[2]) if row[2] else 0,
                        'first_order_date': row[3],
                        'last_order_date': row[4],
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.warning(f"전체 고객주문번호 진척 조회 실패: {e}")
            return []
    
    # ============================================
    # 도착출하번호(ARRIVAL_SHIPPING_NO) 기준 조회
    # ============================================
    
    @staticmethod
    def get_order_by_arrival_shipping_no(arrival_shipping_no: str) -> Optional[Dict[str, Any]]:
        """
        도착출하번호로 주문 조회
        
        Args:
            arrival_shipping_no: 도착출하번호
        
        Returns:
            주문 정보 dict 또는 None
        """
        query = '''
            SELECT 
                "ARRIVAL_SHIPPING_NO",
                "CUSTOMER_ORDER_NO",
                "SUPPLIER_USER_CODE",
                "SUPPLIER_USER_NAME",
                "ORDER_DATE",
                "TRADE_CONDITION_CODE",
                "ORDER_REMARKS",
                "INSTRUCTION_COUNT",
                "ITEM_NAME",
                "PACKING_NAME"
            FROM fcms_cdc.tr_orders
            WHERE TRIM("ARRIVAL_SHIPPING_NO") = %s
        '''
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, [arrival_shipping_no])
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return {
                    'arrival_shipping_no': row[0].strip() if row[0] else '',
                    'customer_order_no': row[1].strip() if row[1] else '',
                    'supplier_user_code': row[2].strip() if row[2] else '',
                    'supplier_user_name': row[3].strip() if row[3] else '',
                    'order_date': row[4],
                    'trade_condition_code': row[5].strip() if row[5] else '',
                    'order_remarks': row[6].strip() if row[6] else '',
                    'total_instruction_count': int(row[7]) if row[7] else 0,
                    'item_name': row[8].strip() if row[8] else '',
                    'packing_name': row[9].strip() if row[9] else '',
                }
        except Exception as e:
            logger.warning(f"도착출하번호로 주문 조회 실패: {e}")
            return None
    
    @staticmethod
    def get_filling_progress_by_arrival_shipping_no(arrival_shipping_no: str) -> Dict[str, int]:
        """
        도착출하번호 기준 충전 진행 현황 조회
        
        TR_ORDERS에서 INSTRUCTION_COUNT 조회
        (실제 충전 완료 수는 별도 테이블 필요 - 현재는 지시수량만 반환)
        
        Args:
            arrival_shipping_no: 도착출하번호
        
        Returns:
            {'instruction_count': N, 'filled_count': M} 형식
        """
        query = '''
            SELECT 
                COALESCE("INSTRUCTION_COUNT", 0) as instruction_count
            FROM fcms_cdc.tr_orders
            WHERE TRIM("ARRIVAL_SHIPPING_NO") = %s
        '''
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, [arrival_shipping_no])
                row = cursor.fetchone()
                
                instruction_count = int(row[0]) if row and row[0] else 0
                
                # TODO: 실제 충전 완료 수는 별도 조회 필요
                # 현재는 지시수량만 반환
                return {
                    'instruction_count': instruction_count,
                    'filled_count': 0,  # 실제 충전 완료 추적 테이블 필요
                }
        except Exception as e:
            logger.warning(f"충전 진행 현황 조회 실패: {e}")
            return {'instruction_count': 0, 'filled_count': 0}
    
    # ============================================
    # 유틸리티 메서드
    # ============================================
    
    @staticmethod
    def dict_fetchall(cursor) -> List[Dict[str, Any]]:
        """
        커서 결과를 dict 리스트로 변환
        """
        columns = [col[0] for col in cursor.description]
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

