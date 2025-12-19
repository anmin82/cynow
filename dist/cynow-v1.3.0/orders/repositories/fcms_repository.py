"""
FCMS CDC 테이블 조회 Repository

PostgreSQL fcms_cdc 스키마의 테이블을 직접 조회
Django ORM 대신 Raw SQL 사용 (CDC 테이블은 Django 모델로 정의되지 않음)
"""

from django.db import connection
from typing import Optional, List, Dict, Any


class FcmsRepository:
    """FCMS CDC 데이터 조회"""
    
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
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            row = cursor.fetchone()
            return row[0] if row else None
    
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
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            row = cursor.fetchone()
            return row[0] if row else None
    
    @staticmethod
    def find_order_by_arrival_shipping_no(arrival_shipping_no: str) -> Optional[Dict[str, Any]]:
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
                o.arrival_shipping_no,
                o.supplier_user_code,
                o.order_date,
                o.trade_condition_code,
                COUNT(oi.id) as item_count,
                SUM(oi.instruction_count) as total_instruction_count
            FROM fcms_cdc.tr_orders o
            LEFT JOIN fcms_cdc.tr_order_informations oi ON o.id = oi.order_id
            WHERE o.arrival_shipping_no = %s
            GROUP BY o.id, o.arrival_shipping_no, o.supplier_user_code, o.order_date, o.trade_condition_code
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query, [arrival_shipping_no])
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'arrival_shipping_no': row[1],
                'supplier_user_code': row[2],
                'order_date': row[3],
                'trade_condition_code': row[4],
                'item_count': row[5],
                'total_instruction_count': row[6],
            }
    
    @staticmethod
    def find_move_report_by_no(move_report_no: str) -> Optional[Dict[str, Any]]:
        """
        이동서번호로 이동서 조회
        
        Args:
            move_report_no: 이동서번호
        
        Returns:
            이동서 정보 dict 또는 None
        """
        query = """
            SELECT 
                mr.id,
                mr.move_report_no,
                mr.move_date,
                mr.from_location_code,
                mr.to_location_code,
                COUNT(mrd.id) as cylinder_count
            FROM fcms_cdc.tr_move_reports mr
            LEFT JOIN fcms_cdc.tr_move_report_details mrd ON mr.id = mrd.move_report_id
            WHERE mr.move_report_no = %s
            GROUP BY mr.id, mr.move_report_no, mr.move_date, mr.from_location_code, mr.to_location_code
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query, [move_report_no])
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'move_report_no': row[1],
                'move_date': row[2],
                'from_location_code': row[3],
                'to_location_code': row[4],
                'cylinder_count': row[5],
            }
    
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
                SUM(oi.instruction_count) as instruction_count,
                COUNT(DISTINCT mrd.cylinder_no) as filled_count
            FROM fcms_cdc.tr_orders o
            LEFT JOIN fcms_cdc.tr_order_informations oi ON o.id = oi.order_id
            LEFT JOIN fcms_cdc.tr_move_reports mr ON o.arrival_shipping_no = mr.move_report_no
            LEFT JOIN fcms_cdc.tr_move_report_details mrd ON mr.id = mrd.move_report_id
            WHERE o.arrival_shipping_no = %s
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query, [arrival_shipping_no])
            row = cursor.fetchone()
            
            return {
                'instruction_count': int(row[0] or 0),
                'filled_count': int(row[1] or 0),
            }
    
    @staticmethod
    def search_orders_by_supplier(supplier_user_code: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        거래처 코드로 주문 검색 (역수입용)
        
        Args:
            supplier_user_code: 거래처 코드
            limit: 최대 조회 건수
        
        Returns:
            주문 정보 리스트
        """
        query = """
            SELECT 
                o.id,
                o.arrival_shipping_no,
                o.supplier_user_code,
                o.order_date,
                o.trade_condition_code,
                SUM(oi.instruction_count) as total_qty
            FROM fcms_cdc.tr_orders o
            LEFT JOIN fcms_cdc.tr_order_informations oi ON o.id = oi.order_id
            WHERE o.supplier_user_code = %s
            GROUP BY o.id, o.arrival_shipping_no, o.supplier_user_code, o.order_date, o.trade_condition_code
            ORDER BY o.order_date DESC
            LIMIT %s
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query, [supplier_user_code, limit])
            rows = cursor.fetchall()
            
            return [
                {
                    'id': row[0],
                    'arrival_shipping_no': row[1],
                    'supplier_user_code': row[2],
                    'order_date': row[3],
                    'trade_condition_code': row[4],
                    'total_qty': int(row[5] or 0),
                }
                for row in rows
            ]
    
    @staticmethod
    def get_all_recent_orders(days: int = 90, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        최근 주문 전체 조회 (역수입용)
        
        Args:
            days: 최근 N일
            limit: 최대 조회 건수
        
        Returns:
            주문 정보 리스트
        """
        query = """
            SELECT 
                o.id,
                o.arrival_shipping_no,
                o.supplier_user_code,
                o.order_date,
                o.trade_condition_code,
                SUM(oi.instruction_count) as total_qty
            FROM fcms_cdc.tr_orders o
            LEFT JOIN fcms_cdc.tr_order_informations oi ON o.id = oi.order_id
            WHERE o.order_date >= CURRENT_DATE - INTERVAL '%s days'
            GROUP BY o.id, o.arrival_shipping_no, o.supplier_user_code, o.order_date, o.trade_condition_code
            ORDER BY o.order_date DESC
            LIMIT %s
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query, [days, limit])
            rows = cursor.fetchall()
            
            return [
                {
                    'id': row[0],
                    'arrival_shipping_no': row[1],
                    'supplier_user_code': row[2],
                    'order_date': row[3],
                    'trade_condition_code': row[4],
                    'total_qty': int(row[5] or 0),
                }
                for row in rows
            ]
    
    @staticmethod
    def dict_fetchall(cursor) -> List[Dict[str, Any]]:
        """
        커서 결과를 dict 리스트로 변환
        
        Args:
            cursor: DB cursor
        
        Returns:
            결과 리스트
        """
        columns = [col[0] for col in cursor.description]
        return [
            dict(zip(columns, row))
            for row in cursor.fetchall()
        ]

