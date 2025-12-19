"""cy_cylinder_current 테이블 조회 전용 Repository"""
from django.db import connection
from typing import List, Dict, Optional
from core.utils.translation import translate_list


class CylinderRepository:
    """cy_cylinder_current 스냅샷 테이블 조회용 Repository"""
    
    @staticmethod
    def get_inventory_summary(filters: Optional[Dict] = None) -> List[Dict]:
        """
        용기종류별 집계 (대시보드용)
        실제로 fcms_cdc.ma_cylinders에 존재하는 용기만 조회 (고아 데이터 제외)
        
        Returns:
            List[Dict]: 용기종류 × 상태 × 위치별 수량 집계
        """
        with connection.cursor() as cursor:
            query = """
                SELECT 
                    c.cylinder_type_key,
                    c.dashboard_gas_name as gas_name,
                    c.dashboard_capacity as capacity,
                    COALESCE(c.dashboard_valve_group_name, c.dashboard_valve_spec_name) as valve_spec,
                    c.dashboard_cylinder_spec_name as cylinder_spec,
                    c.dashboard_status as status,
                    c.dashboard_enduser as enduser,
                    COUNT(*) as qty,
                    SUM(CASE WHEN c.is_available THEN 1 ELSE 0 END) as available_qty,
                    c.dashboard_valve_spec_name as valve_spec_raw
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_enduser IS NOT NULL
            """
            
            params = []
            conditions = []
            
            if filters:
                if 'gas_name' in filters:
                    conditions.append("c.dashboard_gas_name = %s")
                    params.append(filters['gas_name'])
                if 'status' in filters:
                    conditions.append("c.dashboard_status = %s")
                    params.append(filters['status'])
                if 'cylinder_type_key' in filters:
                    conditions.append("c.cylinder_type_key = %s")
                    params.append(filters['cylinder_type_key'])
                if 'enduser' in filters:
                    conditions.append("c.dashboard_enduser = %s")
                    params.append(filters['enduser'])
            
            if conditions:
                query += " AND " + " AND ".join(conditions)
            
            query += """
                GROUP BY 
                    c.cylinder_type_key,
                    c.dashboard_gas_name,
                    c.dashboard_capacity,
                    COALESCE(c.dashboard_valve_group_name, c.dashboard_valve_spec_name),
                    c.dashboard_cylinder_spec_name,
                    c.dashboard_status,
                    c.dashboard_enduser,
                    c.dashboard_valve_spec_name
                ORDER BY c.dashboard_gas_name, c.dashboard_enduser, c.dashboard_status
            """
            
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # 번역 적용
            results = translate_list(results, ['gas_name', 'valve_spec', 'cylinder_spec'])
            
            return results
    
    @staticmethod
    def get_cylinder_list(filters: Optional[Dict] = None, limit: Optional[int] = None, offset: Optional[int] = None, days: Optional[int] = None, sort_by: str = 'cylinder_no', sort_order: str = 'asc') -> List[Dict]:
        """
        개별 용기 리스트
        
        Args:
            filters: 필터 조건
            limit: 최대 개수
            offset: 오프셋 (페이지네이션용)
            days: 최근 N일 이내 데이터만 (last_event_at 기준)
            sort_by: 정렬 기준 컬럼
            sort_order: 정렬 순서 (asc/desc)
        
        Returns:
            List[Dict]: 개별 용기 정보
        """
        with connection.cursor() as cursor:
            query = """
                SELECT 
                    c.cylinder_no,
                    c.dashboard_gas_name as gas_name,
                    c.dashboard_capacity as capacity,
                    COALESCE(c.dashboard_valve_group_name, c.dashboard_valve_spec_name) as valve_spec,
                    c.dashboard_cylinder_spec_name as cylinder_spec,
                    c.dashboard_usage_place as usage_place,
                    c.dashboard_status as status,
                    c.dashboard_location as location,
                    c.pressure_due_date,
                    c.last_event_at,
                    c.snapshot_updated_at as source_updated_at,
                    c.cylinder_type_key,
                    c.manufacture_date,
                    c.pressure_test_date,
                    c.pressure_test_term,
                    c.pressure_expire_date,
                    c.needs_fcms_fix
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_enduser IS NOT NULL
            """
            
            params = []
            conditions = []
            
            if filters:
                if 'cylinder_no' in filters:
                    conditions.append("c.cylinder_no = %s")
                    params.append(filters['cylinder_no'])
                # 단일 가스 필터
                if 'gas_name' in filters:
                    conditions.append("c.dashboard_gas_name = %s")
                    params.append(filters['gas_name'])
                # 다중 가스 필터
                if 'gases' in filters and filters['gases']:
                    gas_list = filters['gases']
                    placeholders = ', '.join(['%s'] * len(gas_list))
                    conditions.append(f"c.dashboard_gas_name IN ({placeholders})")
                    params.extend(gas_list)
                # 단일 상태 필터
                if 'status' in filters:
                    conditions.append("c.dashboard_status = %s")
                    params.append(filters['status'])
                # 다중 상태 필터
                if 'statuses' in filters and filters['statuses']:
                    status_list = filters['statuses']
                    placeholders = ', '.join(['%s'] * len(status_list))
                    conditions.append(f"c.dashboard_status IN ({placeholders})")
                    params.extend(status_list)
                # 단일 위치 필터
                if 'location' in filters:
                    conditions.append("c.dashboard_location = %s")
                    params.append(filters['location'])
                # 다중 위치 필터
                if 'locations' in filters and filters['locations']:
                    loc_list = filters['locations']
                    placeholders = ', '.join(['%s'] * len(loc_list))
                    conditions.append(f"c.dashboard_location IN ({placeholders})")
                    params.extend(loc_list)
                if 'cylinder_type_key' in filters:
                    conditions.append("c.cylinder_type_key = %s")
                    params.append(filters['cylinder_type_key'])
                if 'enduser' in filters:
                    conditions.append("c.dashboard_enduser = %s")
                    params.append(filters['enduser'])
                if 'valve_spec' in filters:
                    conditions.append("COALESCE(c.dashboard_valve_group_name, c.dashboard_valve_spec_name) = %s")
                    params.append(filters['valve_spec'])
                if 'cylinder_spec' in filters:
                    conditions.append("c.dashboard_cylinder_spec_name = %s")
                    params.append(filters['cylinder_spec'])
            
            # 기간 필터 (SQL에서 처리)
            if days is not None:
                conditions.append("(c.last_event_at IS NULL OR c.last_event_at >= NOW() - INTERVAL %s)")
                params.append(f'{days} days')
            
            if conditions:
                query += " AND " + " AND ".join(conditions)
            
            # 정렬 컬럼 매핑 (SQL injection 방지)
            sort_columns = {
                'cylinder_no': 'c.cylinder_no',
                'gas_name': 'c.dashboard_gas_name',
                'status': 'c.dashboard_status',
                'location': 'c.dashboard_location',
                'capacity': 'c.dashboard_capacity',
                'last_event_at': 'c.last_event_at',
                'pressure_expire_date': 'c.pressure_expire_date',
                'manufacture_date': 'c.manufacture_date',
            }
            order_col = sort_columns.get(sort_by, 'c.cylinder_no')
            order_dir = 'DESC' if sort_order == 'desc' else 'ASC'
            query += f" ORDER BY {order_col} {order_dir}"
            
            if limit:
                query += f" LIMIT {limit}"
            if offset:
                query += f" OFFSET {offset}"
            
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # 번역 적용
            results = translate_list(results, ['gas_name', 'valve_spec', 'cylinder_spec', 'usage_place', 'location'])
            
            return results
    
    @staticmethod
    def get_cylinder_count(filters: Optional[Dict] = None, days: Optional[int] = None) -> int:
        """
        용기 개수 조회 (페이지네이션용)
        실제로 fcms_cdc.ma_cylinders에 존재하는 용기만 조회 (고아 데이터 제외)
        
        Args:
            filters: 필터 조건
            days: 최근 N일 이내 데이터만
        
        Returns:
            int: 용기 개수
        """
        with connection.cursor() as cursor:
            query = """
                SELECT COUNT(*) 
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_enduser IS NOT NULL
            """
            
            params = []
            conditions = []
            
            if filters:
                if 'cylinder_no' in filters:
                    conditions.append("c.cylinder_no = %s")
                    params.append(filters['cylinder_no'])
                # 단일 가스 필터
                if 'gas_name' in filters:
                    conditions.append("c.dashboard_gas_name = %s")
                    params.append(filters['gas_name'])
                # 다중 가스 필터
                if 'gases' in filters and filters['gases']:
                    gas_list = filters['gases']
                    placeholders = ', '.join(['%s'] * len(gas_list))
                    conditions.append(f"c.dashboard_gas_name IN ({placeholders})")
                    params.extend(gas_list)
                # 단일 상태 필터
                if 'status' in filters:
                    conditions.append("c.dashboard_status = %s")
                    params.append(filters['status'])
                # 다중 상태 필터
                if 'statuses' in filters and filters['statuses']:
                    status_list = filters['statuses']
                    placeholders = ', '.join(['%s'] * len(status_list))
                    conditions.append(f"c.dashboard_status IN ({placeholders})")
                    params.extend(status_list)
                # 단일 위치 필터
                if 'location' in filters:
                    conditions.append("c.dashboard_location = %s")
                    params.append(filters['location'])
                # 다중 위치 필터
                if 'locations' in filters and filters['locations']:
                    loc_list = filters['locations']
                    placeholders = ', '.join(['%s'] * len(loc_list))
                    conditions.append(f"c.dashboard_location IN ({placeholders})")
                    params.extend(loc_list)
                if 'cylinder_type_key' in filters:
                    conditions.append("c.cylinder_type_key = %s")
                    params.append(filters['cylinder_type_key'])
                if 'enduser' in filters:
                    conditions.append("c.dashboard_enduser = %s")
                    params.append(filters['enduser'])
                if 'valve_spec' in filters:
                    conditions.append("COALESCE(c.dashboard_valve_group_name, c.dashboard_valve_spec_name) = %s")
                    params.append(filters['valve_spec'])
                if 'cylinder_spec' in filters:
                    conditions.append("c.dashboard_cylinder_spec_name = %s")
                    params.append(filters['cylinder_spec'])
            
            if days is not None:
                conditions.append("(c.last_event_at IS NULL OR c.last_event_at >= NOW() - INTERVAL %s)")
                params.append(f'{days} days')
            
            if conditions:
                query += " AND " + " AND ".join(conditions)
            
            cursor.execute(query, params)
            return cursor.fetchone()[0]
    
    @staticmethod
    def get_filter_options() -> Dict[str, List[str]]:
        """
        필터 옵션 조회 (고유값 목록)
        
        Returns:
            Dict: 필터 옵션 (gas_names, locations, valve_specs, cylinder_specs)
        """
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT 
                    c.dashboard_gas_name as gas_name,
                    c.dashboard_location as location,
                    COALESCE(c.dashboard_valve_group_name, c.dashboard_valve_spec_name) as valve_spec,
                    c.dashboard_cylinder_spec_name as cylinder_spec
                FROM cy_cylinder_current c
                INNER JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE c.dashboard_gas_name IS NOT NULL
                  AND c.dashboard_enduser IS NOT NULL
                ORDER BY c.dashboard_gas_name, c.dashboard_location, valve_spec, cylinder_spec
            """)
            
            gas_names = set()
            locations = set()
            valve_specs = set()
            cylinder_specs = set()
            
            for row in cursor.fetchall():
                if row[0]:
                    gas_names.add(row[0])
                if row[1]:
                    locations.add(row[1])
                if row[2]:
                    valve_specs.add(row[2])
                if row[3]:
                    cylinder_specs.add(row[3])
            
            return {
                'gas_names': sorted(gas_names),
                'locations': sorted(locations),
                'valve_specs': sorted(valve_specs)[:20],  # 최대 20개
                'cylinder_specs': sorted(cylinder_specs)[:20],  # 최대 20개
            }
