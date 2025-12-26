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
        TR_MOVE_REPORTS와 JOIN하여 취소된 이동서(PROGRESS_CODE='51') 제외
        
        Args:
            customer_order_no: PO번호(고객발주번호)
        
        Returns:
            연결된 FCMS 주문 리스트 (ARRIVAL_SHIPPING_NO별)
        """
        # 먼저 JOIN 쿼리 시도 (취소 이동서 제외)
        # TR_MOVE_REPORTS: 충전일/출하일/LOT
        # TR_ORDER_INFORMATIONS: 예정일/메모
        # TR_MOVE_REPORT_DETAILS: 확정수량 (CYLINDER_NO 개수)
        # TR_CYLINDER_STATUS_HISTORIES: 출하수량 (MOVE_CODE='60')
        query_with_join = '''
            SELECT 
                o."ARRIVAL_SHIPPING_NO",
                o."CUSTOMER_ORDER_NO",
                o."SUPPLIER_USER_CODE",
                o."SUPPLIER_USER_NAME",
                o."ORDER_DATE",
                o."TRADE_CONDITION_CODE",
                o."ORDER_REMARKS",
                o."SELECTION_PATTERN_CODE",
                o."ITEM_NAME",
                o."PACKING_NAME",
                o."INSTRUCTION_QUANTITY",
                o."INSTRUCTION_COUNT",
                o."FILLING_THRESHOLD",
                o."DELIVERY_DATE",
                o."MOVE_REPORT_REMARKS",
                COALESCE(m."PROGRESS_CODE", '') as progress_code,
                m."FILLING_DATE" as filling_date,
                m."SHIPPING_DATE" as shipping_date,
                CONCAT(
                    COALESCE(m."FILLING_LOT_HEADER", ''),
                    COALESCE(m."FILLING_LOT_NO", ''),
                    CASE WHEN m."FILLING_LOT_BRANCH" IS NOT NULL AND m."FILLING_LOT_BRANCH" != '' 
                         THEN '-' || m."FILLING_LOT_BRANCH" 
                         ELSE '' 
                    END
                ) as filling_lot_no,
                oi."FILLING_PLAN_DATE" as filling_plan_date,
                oi."WAREHOUSING_PLAN_DATE" as warehousing_plan_date,
                oi."SHIPPING_PLAN_DATE" as shipping_plan_date,
                oi."SALES_REMARKS" as sales_remarks,
                oi."BUSINESS_REMARKS" as business_remarks,
                oi."PRODUCTION_REMARKS" as production_remarks,
                COALESCE(d.confirmed_count, 0) as confirmed_count,
                COALESCE(s.shipped_count, 0) as shipped_count
            FROM fcms_cdc.tr_orders o
            LEFT JOIN fcms_cdc.tr_move_reports m 
                ON TRIM(o."ARRIVAL_SHIPPING_NO") = TRIM(m."MOVE_REPORT_NO")
            LEFT JOIN fcms_cdc.tr_order_informations oi
                ON TRIM(o."ARRIVAL_SHIPPING_NO") = TRIM(oi."MOVE_REPORT_NO")
            LEFT JOIN (
                SELECT "MOVE_REPORT_NO", COUNT("CYLINDER_NO") as confirmed_count
                FROM fcms_cdc.tr_move_report_details
                GROUP BY "MOVE_REPORT_NO"
            ) d ON TRIM(o."ARRIVAL_SHIPPING_NO") = TRIM(d."MOVE_REPORT_NO")
            LEFT JOIN (
                SELECT "MOVE_REPORT_NO", COUNT("CYLINDER_NO") as shipped_count
                FROM fcms_cdc.tr_cylinder_status_histories
                WHERE "MOVE_CODE" = '60'
                GROUP BY "MOVE_REPORT_NO"
            ) s ON TRIM(o."ARRIVAL_SHIPPING_NO") = TRIM(s."MOVE_REPORT_NO")
            WHERE TRIM(o."CUSTOMER_ORDER_NO") = %s
              AND (m."PROGRESS_CODE" IS NULL OR m."PROGRESS_CODE" != '51')
            ORDER BY o."ARRIVAL_SHIPPING_NO"
        '''
        
        # Fallback 쿼리 (JOIN 없이)
        query_simple = '''
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
        
        def parse_rows(rows, has_progress=True):
            result = []
            for row in rows:
                result.append({
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
                    'progress_code': row[15].strip() if has_progress and len(row) > 15 and row[15] else '',
                    'filling_date': row[16] if has_progress and len(row) > 16 else None,
                    'shipping_date': row[17] if has_progress and len(row) > 17 else None,
                    'filling_lot_no': row[18].strip() if has_progress and len(row) > 18 and row[18] else '',
                    'filling_plan_date': row[19] if has_progress and len(row) > 19 else None,
                    'warehousing_plan_date': row[20] if has_progress and len(row) > 20 else None,
                    'shipping_plan_date': row[21] if has_progress and len(row) > 21 else None,
                    'sales_remarks': row[22].strip() if has_progress and len(row) > 22 and row[22] else '',
                    'business_remarks': row[23].strip() if has_progress and len(row) > 23 and row[23] else '',
                    'production_remarks': row[24].strip() if has_progress and len(row) > 24 and row[24] else '',
                    'confirmed_count': row[25] if has_progress and len(row) > 25 else 0,
                    'shipped_count': row[26] if has_progress and len(row) > 26 else 0,
                })
            return result
        
        try:
            with connection.cursor() as cursor:
                # JOIN 쿼리 시도
                try:
                    cursor.execute(query_with_join, [customer_order_no])
                    rows = cursor.fetchall()
                    return parse_rows(rows, has_progress=True)
                except Exception as join_error:
                    logger.warning(f"JOIN 쿼리 실패, 단순 쿼리로 fallback: {join_error}")
                    # Fallback: 단순 쿼리
                    cursor.execute(query_simple, [customer_order_no])
                    rows = cursor.fetchall()
                    return parse_rows(rows, has_progress=False)
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
        취소된 이동서(PROGRESS_CODE='51') 제외
        
        Returns:
            [{customer_order_no, arrival_count, total_instruction_count, ...}]
        """
        query_with_join = '''
            SELECT 
                TRIM(o."CUSTOMER_ORDER_NO") as customer_order_no,
                COUNT(DISTINCT o."ARRIVAL_SHIPPING_NO") as arrival_count,
                COALESCE(SUM(o."INSTRUCTION_COUNT"), 0) as total_instruction_count,
                MIN(o."ORDER_DATE") as first_order_date,
                MAX(o."ORDER_DATE") as last_order_date
            FROM fcms_cdc.tr_orders o
            LEFT JOIN fcms_cdc.tr_move_reports m 
                ON TRIM(o."ARRIVAL_SHIPPING_NO") = TRIM(m."MOVE_REPORT_NO")
            WHERE o."CUSTOMER_ORDER_NO" IS NOT NULL
              AND TRIM(o."CUSTOMER_ORDER_NO") != ''
              AND (m."PROGRESS_CODE" IS NULL OR m."PROGRESS_CODE" != '51')
            GROUP BY TRIM(o."CUSTOMER_ORDER_NO")
            ORDER BY MAX(o."ORDER_DATE") DESC
            LIMIT 500
        '''
        
        query_simple = '''
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
        
        def parse_rows(rows):
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
        
        try:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(query_with_join)
                    rows = cursor.fetchall()
                    return parse_rows(rows)
                except Exception as join_error:
                    logger.warning(f"JOIN 쿼리 실패, 단순 쿼리로 fallback: {join_error}")
                    cursor.execute(query_simple)
                    rows = cursor.fetchall()
                    return parse_rows(rows)
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
    # 이동서 상세 조회
    # ============================================
    
    @staticmethod
    def get_move_report_detail(move_report_no: str) -> Optional[Dict[str, Any]]:
        """
        이동서번호로 상세 정보 및 용기번호 리스트 조회
        TR_ORDERS 기준으로 조회 (아직 충전 안 된 이동서도 조회 가능)
        
        Returns:
            {
                'move_report': {...},  # 이동서 기본 정보
                'cylinders': [...]      # 연결된 용기번호 리스트
            }
        """
        try:
            with connection.cursor() as cursor:
                # 이동서 기본 정보 (TR_ORDERS 기준)
                cursor.execute('''
                    SELECT 
                        o."ARRIVAL_SHIPPING_NO",
                        COALESCE(m."PROGRESS_CODE", '') as progress_code,
                        m."FILLING_DATE",
                        m."SHIPPING_DATE",
                        CONCAT(
                            COALESCE(m."FILLING_LOT_HEADER", ''),
                            COALESCE(m."FILLING_LOT_NO", ''),
                            CASE WHEN m."FILLING_LOT_BRANCH" IS NOT NULL AND m."FILLING_LOT_BRANCH" != '' 
                                 THEN '-' || m."FILLING_LOT_BRANCH" 
                                 ELSE '' 
                            END
                        ) as filling_lot_no,
                        o."CUSTOMER_ORDER_NO",
                        o."SUPPLIER_USER_NAME",
                        o."ITEM_NAME",
                        o."PACKING_NAME",
                        o."INSTRUCTION_COUNT",
                        o."INSTRUCTION_QUANTITY",
                        o."DELIVERY_DATE",
                        oi."FILLING_PLAN_DATE",
                        oi."WAREHOUSING_PLAN_DATE",
                        oi."SHIPPING_PLAN_DATE",
                        oi."SALES_REMARKS",
                        oi."BUSINESS_REMARKS",
                        oi."PRODUCTION_REMARKS"
                    FROM fcms_cdc.tr_orders o
                    LEFT JOIN fcms_cdc.tr_move_reports m 
                        ON TRIM(o."ARRIVAL_SHIPPING_NO") = TRIM(m."MOVE_REPORT_NO")
                    LEFT JOIN fcms_cdc.tr_order_informations oi
                        ON TRIM(o."ARRIVAL_SHIPPING_NO") = TRIM(oi."MOVE_REPORT_NO")
                    WHERE TRIM(o."ARRIVAL_SHIPPING_NO") = %s
                ''', [move_report_no.strip()])
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                move_report = {
                    'move_report_no': row[0].strip() if row[0] else '',
                    'progress_code': row[1].strip() if row[1] else '',
                    'filling_date': row[2],
                    'shipping_date': row[3],
                    'filling_lot_no': row[4].strip() if row[4] else '',
                    'customer_order_no': row[5].strip() if row[5] else '',
                    'supplier_user_name': row[6].strip() if row[6] else '',
                    'item_name': row[7].strip() if row[7] else '',
                    'packing_name': row[8].strip() if row[8] else '',
                    'instruction_count': row[9] or 0,
                    'instruction_quantity': row[10] or 0,
                    'delivery_date': row[11],
                    'filling_plan_date': row[12],
                    'warehousing_plan_date': row[13],
                    'shipping_plan_date': row[14],
                    'sales_remarks': row[15].strip() if row[15] else '',
                    'business_remarks': row[16].strip() if row[16] else '',
                    'production_remarks': row[17].strip() if row[17] else '',
                }
                
                # 용기번호 리스트
                cursor.execute('''
                    SELECT 
                        d."CYLINDER_NO",
                        d."SEQ_NO",
                        h."MOVE_CODE" as last_move_code,
                        h."MOVE_DATE" as last_move_date
                    FROM fcms_cdc.tr_move_report_details d
                    LEFT JOIN LATERAL (
                        SELECT "MOVE_CODE", "MOVE_DATE"
                        FROM fcms_cdc.tr_cylinder_status_histories
                        WHERE "CYLINDER_NO" = d."CYLINDER_NO"
                          AND "MOVE_REPORT_NO" = d."MOVE_REPORT_NO"
                        ORDER BY "HISTORY_SEQ" DESC
                        LIMIT 1
                    ) h ON true
                    WHERE TRIM(d."MOVE_REPORT_NO") = %s
                    ORDER BY d."SEQ_NO", d."CYLINDER_NO"
                ''', [move_report_no.strip()])
                
                cylinders = []
                for cyl_row in cursor.fetchall():
                    cylinders.append({
                        'cylinder_no': cyl_row[0].strip() if cyl_row[0] else '',
                        'seq_no': cyl_row[1] or 0,
                        'last_move_code': cyl_row[2].strip() if cyl_row[2] else '',
                        'last_move_date': cyl_row[3],
                    })
                
                return {
                    'move_report': move_report,
                    'cylinders': cylinders,
                }
        except Exception as e:
            logger.error(f"이동서 상세 조회 실패 ({move_report_no}): {e}")
            return None
    
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

