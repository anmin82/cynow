"""특정 용기종류 확인"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = '특정 용기종류 확인 (예: CF4 CGA716 용량 360)'

    def add_arguments(self, parser):
        parser.add_argument('--gas', type=str, help='가스명 (예: CF4)')
        parser.add_argument('--valve', type=str, help='밸브 스펙 (예: CGA716)')
        parser.add_argument('--capacity', type=float, help='용량 (예: 360)')

    def handle(self, *args, **options):
        gas_name = options.get('gas', '')
        valve_spec = options.get('valve', '')
        capacity = options.get('capacity')
        
        with connection.cursor() as cursor:
            self.stdout.write("\n=== 용기종류 확인 ===\n")
            
            # 조건 구성
            conditions = []
            params = []
            
            if gas_name:
                conditions.append("dashboard_gas_name LIKE %s")
                params.append(f'%{gas_name}%')
            
            if capacity is not None:
                conditions.append("dashboard_capacity = %s")
                params.append(capacity)
            
            if valve_spec:
                conditions.append("(dashboard_valve_group_name LIKE %s OR dashboard_valve_spec_name LIKE %s)")
                params.append(f'%{valve_spec}%')
                params.append(f'%{valve_spec}%')
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 1. cy_cylinder_current에서 확인
            self.stdout.write("1. cy_cylinder_current 테이블:\n")
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as 총수량,
                    COUNT(DISTINCT cylinder_type_key) as 용기종류수,
                    COUNT(DISTINCT dashboard_enduser) as EndUser수
                FROM cy_cylinder_current
                WHERE {where_clause}
            """, params)
            
            result = cursor.fetchone()
            self.stdout.write(f"   총 수량: {result[0]}개")
            self.stdout.write(f"   용기종류 수: {result[1]}개")
            self.stdout.write(f"   EndUser 수: {result[2]}개")
            
            # 2. 상태별 집계
            self.stdout.write("\n2. 상태별 집계:\n")
            cursor.execute(f"""
                SELECT 
                    dashboard_status as 상태,
                    COUNT(*) as 수량
                FROM cy_cylinder_current
                WHERE {where_clause}
                GROUP BY dashboard_status
                ORDER BY 수량 DESC
            """, params)
            
            for row in cursor.fetchall():
                self.stdout.write(f"   {row[0]}: {row[1]}개")
            
            # 3. EndUser별 집계
            self.stdout.write("\n3. EndUser별 집계:\n")
            cursor.execute(f"""
                SELECT 
                    dashboard_enduser as EndUser,
                    COUNT(*) as 수량
                FROM cy_cylinder_current
                WHERE {where_clause}
                GROUP BY dashboard_enduser
                ORDER BY 수량 DESC
            """, params)
            
            for row in cursor.fetchall():
                self.stdout.write(f"   {row[0]}: {row[1]}개")
            
            # 4. fcms_cdc.ma_cylinders에 존재하는지 확인
            self.stdout.write("\n4. fcms_cdc.ma_cylinders 테이블:\n")
            
            fcms_conditions = []
            fcms_params = []
            
            if gas_name:
                fcms_conditions.append("COALESCE(i.\"DISPLAY_NAME\", i.\"FORMAL_NAME\", '') LIKE %s")
                fcms_params.append(f'%{gas_name}%')
            
            if capacity is not None:
                fcms_conditions.append("c.\"CAPACITY\" = %s")
                fcms_params.append(capacity)
            
            if valve_spec:
                fcms_conditions.append("(COALESCE(vs.\"NAME\", '') LIKE %s OR c.\"VALVE_SPEC_CODE\" LIKE %s)")
                fcms_params.append(f'%{valve_spec}%')
                fcms_params.append(f'%{valve_spec}%')
            
            fcms_where = " AND ".join(fcms_conditions) if fcms_conditions else "1=1"
            
            cursor.execute(f"""
                SELECT COUNT(*) as 수량
                FROM "fcms_cdc"."ma_cylinders" c
                LEFT JOIN "fcms_cdc"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
                LEFT JOIN "fcms_cdc"."ma_valve_specs" vs ON c."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
                WHERE {fcms_where}
            """, fcms_params)
            
            fcms_count = cursor.fetchone()[0]
            self.stdout.write(f"   총 수량: {fcms_count}개")
            
            # 5. 고아 데이터 확인
            self.stdout.write("\n5. 고아 데이터 확인:\n")
            cursor.execute(f"""
                SELECT COUNT(*) as 수량
                FROM cy_cylinder_current c
                LEFT JOIN "fcms_cdc"."ma_cylinders" mc 
                    ON RTRIM(c.cylinder_no) = RTRIM(mc."CYLINDER_NO")
                WHERE mc."CYLINDER_NO" IS NULL
                  AND {where_clause}
            """, params)
            
            orphaned_count = cursor.fetchone()[0]
            if orphaned_count > 0:
                self.stdout.write(self.style.WARNING(f"   [경고] 고아 데이터: {orphaned_count}개"))
            else:
                self.stdout.write(self.style.SUCCESS(f"   [OK] 고아 데이터 없음"))
            
            # 6. 용기종류별 집계 (대시보드와 동일한 방식)
            self.stdout.write("\n6. 용기종류별 집계 (대시보드 방식):\n")
            cursor.execute(f"""
                SELECT 
                    cylinder_type_key,
                    dashboard_gas_name as 가스명,
                    dashboard_capacity as 용량,
                    COALESCE(dashboard_valve_group_name, dashboard_valve_spec_name) as 밸브스펙,
                    dashboard_cylinder_spec_name as 용기스펙,
                    STRING_AGG(DISTINCT dashboard_enduser, ', ' ORDER BY dashboard_enduser) as EndUser,
                    COUNT(*) as 총수량,
                    SUM(CASE WHEN is_available THEN 1 ELSE 0 END) as 가용수량
                FROM cy_cylinder_current
                WHERE {where_clause}
                GROUP BY 
                    cylinder_type_key,
                    dashboard_gas_name,
                    dashboard_capacity,
                    COALESCE(dashboard_valve_group_name, dashboard_valve_spec_name),
                    dashboard_cylinder_spec_name
                ORDER BY dashboard_gas_name, dashboard_capacity
            """, params)
            
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            if not results:
                self.stdout.write("   데이터 없음")
            else:
                for row in results:
                    self.stdout.write(f"\n   용기종류 키: {row['cylinder_type_key']}")
                    self.stdout.write(f"   {row['가스명']} | 용량: {row['용량']} | 밸브: {row['밸브스펙']} | 용기: {row['용기스펙']}")
                    self.stdout.write(f"   EndUser: {row['EndUser']}")
                    self.stdout.write(f"   총: {row['총수량']}개, 가용: {row['가용수량']}개")










