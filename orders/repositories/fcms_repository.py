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
            최신 ARRIVAL_SHIPPING_NO (예: FP240125) 또는 None
        """
        query = """
            SELECT arrival_shipping_no
            FROM fcms_cdc.tr_orders
            WHERE arrival_shipping_no IS NOT NULL
              AND arrival_shipping_no LIKE 'FP%'
            ORDER BY arrival_shipping_no DESC
            LIMIT 1
        """
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                row = cursor.fetchone()
                return row[0].strip() if row and row[0] else None
        except Exception as e:
            logger.warning(f"최신 도착출하번호 조회 실패: {e}")
            return None
    
    @staticmethod
    def get_latest_move_report_no() -> Optional[str]:
        """
        최신 이동서번호 조회
        
        Returns:
            최신 MOVE_REPORT_NO (예: FP240125) 또는 None
        """
        query = """
            SELECT move_report_no
            FROM fcms_cdc.tr_move_reports
            WHERE move_report_no IS NOT NULL
              AND move_report_no LIKE 'FP%'
            ORDER BY move_report_no DESC
            LIMIT 1
        """
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                row = cursor.fetchone()
                return row[0].strip() if row and row[0] else None
        except Exception as e:
            logger.warning(f"최신 이동서번호 조회 실패: {e}")
            return None
    
    # ============================================
    # 수주별 생산 진척 조회 (수주관리표용)
    # ============================================
    
    @staticmethod
    def get_orders_by_customer_order_no(customer_order_no: str) -> List[Dict[str, Any]]:
        """
        고객주문번호(PO번호)로 연결된 모든 FCMS 주문 조회
        
        Args:
            customer_order_no: PO번호(고객발주번호)
        
        Returns:
            연결된 FCMS 주문 리스트 (ARRIVAL_SHIPPING_NO별)
        """
        query = """
            SELECT 
                o.id,
                TRIM(o.arrival_shipping_no) as arrival_shipping_no,
                TRIM(o.customer_order_no) as customer_order_no,
                TRIM(o.supplier_user_code) as supplier_user_code,
                o.order_date,
                TRIM(o.trade_condition_code) as trade_condition_code,
                TRIM(o.order_remarks) as order_remarks,
                TRIM(o.selection_pattern_code) as selection_pattern_code
            FROM fcms_cdc.tr_orders o
            WHERE TRIM(o.customer_order_no) = %s
            ORDER BY o.arrival_shipping_no
        """
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, [customer_order_no])
                rows = cursor.fetchall()
                
                return [
                    {
                        'id': row[0],
                        'arrival_shipping_no': row[1],
                        'customer_order_no': row[2],
                        'supplier_user_code': row[3],
                        'order_date': row[4],
                        'trade_condition_code': row[5],
                        'order_remarks': row[6],
                        'selection_pattern_code': row[7],
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.warning(f"고객주문번호별 FCMS 주문 조회 실패: {e}")
            return []
    
    @staticmethod
    def get_order_informations_by_order_id(order_id: int) -> List[Dict[str, Any]]:
        """
        주문 ID로 주문 상세(품목별) 정보 조회
        
        Args:
            order_id: TR_ORDERS.id
        
        Returns:
            품목별 상세 정보 리스트
        """
        query = """
            SELECT 
                oi.id,
                oi.order_id,
                TRIM(oi.item_name) as item_name,
                TRIM(oi.packing_name) as packing_name,
                oi.instruction_quantity,
                oi.instruction_count,
                oi.filling_threshold,
                TRIM(oi.order_remarks) as order_remarks,
                TRIM(oi.trade_condition_code) as trade_condition_code,
                TRIM(oi.selection_pattern_code) as selection_pattern_code,
                TRIM(oi.move_report_no) as move_report_no,
                oi.designation_delivery_date,
                oi.filling_plan_date,
                oi.warehousing_plan_date,
                oi.shipping_plan_date,
                TRIM(oi.sales_remarks) as sales_remarks,
                TRIM(oi.business_remarks) as business_remarks,
                TRIM(oi.production_remarks) as production_remarks
            FROM fcms_cdc.tr_order_informations oi
            WHERE oi.order_id = %s
            ORDER BY oi.id
        """
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, [order_id])
                rows = cursor.fetchall()
                
                return [
                    {
                        'id': row[0],
                        'order_id': row[1],
                        'item_name': row[2],
                        'packing_name': row[3],
                        'instruction_quantity': float(row[4]) if row[4] else None,
                        'instruction_count': int(row[5]) if row[5] else 0,
                        'filling_threshold': float(row[6]) if row[6] else None,
                        'order_remarks': row[7],
                        'trade_condition_code': row[8],
                        'selection_pattern_code': row[9],
                        # 일정 정보
                        'move_report_no': row[10],
                        'designation_delivery_date': row[11],
                        'filling_plan_date': row[12],
                        'warehousing_plan_date': row[13],
                        'shipping_plan_date': row[14],
                        # 부서별 비고
                        'sales_remarks': row[15],
                        'business_remarks': row[16],
                        'production_remarks': row[17],
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.warning(f"주문 상세 조회 실패: {e}")
            return []
    
    @staticmethod
    def get_production_summary_by_customer_order_no(customer_order_no: str) -> Dict[str, Any]:
        """
        고객주문번호(PO번호)별 생산 진척 요약 조회
        
        Args:
            customer_order_no: PO번호(고객발주번호)
        
        Returns:
            {
                'total_arrival_count': 도착출하번호 개수,
                'total_instruction_count': 총 지시수량,
                'total_instruction_quantity': 총 지시량(kg),
                'orders': [주문별 상세]
            }
        """
        orders = FcmsRepository.get_orders_by_customer_order_no(customer_order_no)
        
        total_instruction_count = 0
        total_instruction_quantity = Decimal('0')
        
        for order in orders:
            items = FcmsRepository.get_order_informations_by_order_id(order['id'])
            order['items'] = items
            
            for item in items:
                total_instruction_count += item['instruction_count'] or 0
                if item['instruction_quantity']:
                    total_instruction_quantity += Decimal(str(item['instruction_quantity']))
        
        return {
            'customer_order_no': customer_order_no,
            'total_arrival_count': len(orders),
            'total_instruction_count': total_instruction_count,
            'total_instruction_quantity': total_instruction_quantity,
            'orders': orders,
        }
    
    @staticmethod
    def get_all_customer_order_nos_with_progress() -> List[Dict[str, Any]]:
        """
        모든 고객주문번호와 진척 요약 조회 (수주관리표 목록용)
        
        Returns:
            [{customer_order_no, arrival_count, total_instruction_count, ...}]
        """
        query = """
            SELECT 
                TRIM(o.customer_order_no) as customer_order_no,
                COUNT(DISTINCT o.arrival_shipping_no) as arrival_count,
                COALESCE(SUM(oi.instruction_count), 0) as total_instruction_count,
                MIN(o.order_date) as first_order_date,
                MAX(o.order_date) as last_order_date
            FROM fcms_cdc.tr_orders o
            LEFT JOIN fcms_cdc.tr_order_informations oi ON o.id = oi.order_id
            WHERE o.customer_order_no IS NOT NULL
              AND TRIM(o.customer_order_no) != ''
            GROUP BY TRIM(o.customer_order_no)
            ORDER BY MAX(o.order_date) DESC
            LIMIT 500
        """
        
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
        query = """
            SELECT 
                o.id,
                TRIM(o.arrival_shipping_no) as arrival_shipping_no,
                TRIM(o.customer_order_no) as customer_order_no,
                TRIM(o.supplier_user_code) as supplier_user_code,
                o.order_date,
                TRIM(o.trade_condition_code) as trade_condition_code,
                TRIM(o.order_remarks) as order_remarks,
                COALESCE(SUM(oi.instruction_count), 0) as total_instruction_count,
                COUNT(oi.id) as item_count
            FROM fcms_cdc.tr_orders o
            LEFT JOIN fcms_cdc.tr_order_informations oi ON o.id = oi.order_id
            WHERE TRIM(o.arrival_shipping_no) = %s
            GROUP BY o.id, o.arrival_shipping_no, o.customer_order_no, 
                     o.supplier_user_code, o.order_date, o.trade_condition_code, o.order_remarks
        """
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, [arrival_shipping_no])
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                return {
                    'id': row[0],
                    'arrival_shipping_no': row[1],
                    'customer_order_no': row[2],
                    'supplier_user_code': row[3],
                    'order_date': row[4],
                    'trade_condition_code': row[5],
                    'order_remarks': row[6],
                    'total_instruction_count': int(row[7]),
                    'item_count': int(row[8]),
                }
        except Exception as e:
            logger.warning(f"도착출하번호로 주문 조회 실패: {e}")
            return None
    
    @staticmethod
    def get_filling_progress_by_arrival_shipping_no(arrival_shipping_no: str) -> Dict[str, int]:
        """
        도착출하번호 기준 충전 진행 현황 조회
        
        Args:
            arrival_shipping_no: 도착출하번호
        
        Returns:
            {'instruction_count': N, 'filled_count': M} 형식
        """
        query = """
            SELECT 
                COALESCE(SUM(oi.instruction_count), 0) as instruction_count,
                COUNT(DISTINCT mrd.cylinder_no) as filled_count
            FROM fcms_cdc.tr_orders o
            LEFT JOIN fcms_cdc.tr_order_informations oi ON o.id = oi.order_id
            LEFT JOIN fcms_cdc.tr_move_reports mr ON TRIM(o.arrival_shipping_no) = TRIM(mr.move_report_no)
            LEFT JOIN fcms_cdc.tr_move_report_details mrd ON mr.id = mrd.move_report_id
            WHERE TRIM(o.arrival_shipping_no) = %s
        """
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, [arrival_shipping_no])
                row = cursor.fetchone()
                
                return {
                    'instruction_count': int(row[0] or 0),
                    'filled_count': int(row[1] or 0),
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

