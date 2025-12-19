"""VIEW 접근 추상화 레이어 (Repository 패턴)"""
from django.db import connection
from typing import List, Dict, Optional
from core.utils.status_mapper import map_condition_code_to_status
from core.utils.cylinder_type import generate_cylinder_type_key
from core.utils.translation import translate_list


class ViewRepository:
    """VIEW 조회를 위한 Repository 클래스"""
    
    @staticmethod
    def get_inventory_view(filters: Optional[Dict] = None) -> List[Dict]:
        """
        vw_cynow_inventory VIEW 조회
        
        Returns:
            List[Dict]: 용기종류 × 상태 × 위치별 수량 집계 결과
        """
        with connection.cursor() as cursor:
            query = """
                SELECT 
                    cylinder_type_key,
                    gas_name,
                    capacity,
                    valve_spec,
                    cylinder_spec,
                    usage_place,
                    status,
                    location,
                    qty,
                    updated_at
                FROM vw_cynow_inventory
            """
            
            params = []
            # Django는 DB별 플레이스홀더를 자동 변환하지만, 명시적으로 %s 사용 (PostgreSQL/SQLite 모두 호환)
            param_placeholder = '%s' if connection.vendor == 'postgresql' else '?'
            
            if filters:
                conditions = []
                if 'gas_name' in filters:
                    conditions.append(f"gas_name = {param_placeholder}")
                    params.append(filters['gas_name'])
                if 'status' in filters:
                    conditions.append(f"status = {param_placeholder}")
                    params.append(filters['status'])
                if 'location' in filters:
                    conditions.append(f"location = {param_placeholder}")
                    params.append(filters['location'])
                if 'cylinder_type_key' in filters:
                    conditions.append(f"cylinder_type_key = {param_placeholder}")
                    params.append(filters['cylinder_type_key'])
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY gas_name, status, location"
            
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # cylinder_type_key가 비어있으면 Python에서 생성 (PostgreSQL에서는 SQL에서 생성됨)
            for row in results:
                if not row.get('cylinder_type_key'):
                    row['cylinder_type_key'] = generate_cylinder_type_key(
                        row.get('gas_name', ''),
                        row.get('capacity'),
                        row.get('valve_spec'),
                        row.get('cylinder_spec'),
                        row.get('usage_place')
                    )
            
            # 일본어 → 한국어 번역 적용
            results = translate_list(results, ['gas_name', 'valve_spec', 'cylinder_spec', 'usage_place', 'location'])
            
            return results
    
    @staticmethod
    def get_cylinder_list_view(filters: Optional[Dict] = None, limit: Optional[int] = None) -> List[Dict]:
        """
        vw_cynow_cylinder_list VIEW 조회
        
        Returns:
            List[Dict]: 개별 용기 리스트
        """
        with connection.cursor() as cursor:
            query = """
                SELECT 
                    cylinder_no,
                    gas_name,
                    capacity,
                    valve_spec,
                    cylinder_spec,
                    usage_place,
                    status,
                    location,
                    pressure_due_date,
                    last_event_at,
                    source_updated_at
                FROM vw_cynow_cylinder_list
            """
            
            params = []
            # Django는 DB별 플레이스홀더를 자동 변환하지만, 명시적으로 %s 사용 (PostgreSQL/SQLite 모두 호환)
            param_placeholder = '%s' if connection.vendor == 'postgresql' else '?'
            
            if filters:
                conditions = []
                if 'cylinder_no' in filters:
                    conditions.append(f"cylinder_no = {param_placeholder}")
                    params.append(filters['cylinder_no'])
                if 'gas_name' in filters:
                    conditions.append(f"gas_name = {param_placeholder}")
                    params.append(filters['gas_name'])
                if 'status' in filters:
                    conditions.append(f"status = {param_placeholder}")
                    params.append(filters['status'])
                if 'location' in filters:
                    conditions.append(f"location = {param_placeholder}")
                    params.append(filters['location'])
                if 'valve_spec' in filters:
                    conditions.append(f"valve_spec = {param_placeholder}")
                    params.append(filters['valve_spec'])
                if 'cylinder_spec' in filters:
                    conditions.append(f"cylinder_spec = {param_placeholder}")
                    params.append(filters['cylinder_spec'])
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY cylinder_no"
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # cylinder_type_key를 Python에서 생성
            for row in results:
                if 'cylinder_type_key' not in row:
                    row['cylinder_type_key'] = generate_cylinder_type_key(
                        row.get('gas_name', ''),
                        row.get('capacity'),
                        row.get('valve_spec'),
                        row.get('cylinder_spec'),
                        row.get('usage_place')
                    )
            
            # 일본어 → 한국어 번역 적용
            results = translate_list(results, ['gas_name', 'valve_spec', 'cylinder_spec', 'usage_place', 'location'])
            
            return results

