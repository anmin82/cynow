"""PostgreSQL에서 VIEW 생성 (실제 CDC 테이블 구조 기반)"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings


class Command(BaseCommand):
    help = 'PostgreSQL에서 vw_cynow_inventory 및 vw_cynow_cylinder_list VIEW 생성 (실제 CDC 테이블 기반)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--schema',
            type=str,
            default='fcms_cdc',
            help='CDC 테이블이 있는 스키마 (기본값: fcms_cdc)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='기존 VIEW를 강제로 삭제하고 재생성'
        )

    def handle(self, *args, **options):
        db_config = settings.DATABASES['default']
        source_schema = options['schema']
        force = options['force']
        
        # PostgreSQL인지 확인
        if 'postgresql' not in db_config['ENGINE']:
            self.stdout.write(self.style.ERROR("PostgreSQL이 아닙니다. DB_ENGINE=postgresql로 설정하세요."))
            return
        
        try:
            with connection.cursor() as cursor:
                self.stdout.write(f"CDC 테이블 확인 중 (스키마: {source_schema})...")
                
                # 필수 테이블 존재 확인
                required_tables = [
                    'ma_cylinders',
                    'ma_items',
                    'ma_cylinder_specs',
                    'ma_valve_specs',
                    'tr_latest_cylinder_statuses',
                ]
                
                missing_tables = []
                for table in required_tables:
                    cursor.execute("""
                        SELECT COUNT(*) 
                        FROM information_schema.tables 
                        WHERE table_schema = %s 
                        AND table_name = %s;
                    """, (source_schema, table))
                    if cursor.fetchone()[0] == 0:
                        missing_tables.append(table)
                
                if missing_tables:
                    self.stdout.write(self.style.ERROR(f"필수 테이블이 없습니다: {', '.join(missing_tables)}"))
                    return
                
                self.stdout.write(self.style.SUCCESS("필수 테이블 확인 완료"))
                
                # 테이블별 데이터 개수 확인
                for table in required_tables:
                    cursor.execute(f'SELECT COUNT(*) FROM "{source_schema}"."{table}";')
                    count = cursor.fetchone()[0]
                    self.stdout.write(f"  {table}: {count:,}개 행")
                
                # 기존 VIEW 삭제
                if force:
                    self.stdout.write("\n기존 VIEW 삭제 중...")
                    cursor.execute("DROP VIEW IF EXISTS vw_cynow_cylinder_list CASCADE;")
                    cursor.execute("DROP VIEW IF EXISTS vw_cynow_inventory CASCADE;")
                    self.stdout.write(self.style.SUCCESS("  삭제 완료"))
                
                # 1. vw_cynow_cylinder_list VIEW 생성
                self.stdout.write("\nvw_cynow_cylinder_list VIEW 생성 중...")
                
                create_cylinder_list_view_sql = f"""
                    CREATE OR REPLACE VIEW vw_cynow_cylinder_list AS
                    SELECT 
                        RTRIM(c."CYLINDER_NO") as cylinder_no,
                        COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') as gas_name,
                        c."CAPACITY" as capacity,
                        COALESCE(vs."NAME", '') as valve_spec,
                        COALESCE(cs."NAME", '') as cylinder_spec,
                        COALESCE(c."USE_DEPARTMENT_CODE", '') as usage_place,
                        CASE 
                            WHEN ls."CONDITION_CODE" IN ('100', '102') THEN '보관'
                            WHEN ls."CONDITION_CODE" IN ('210', '220') THEN '충전'
                            WHEN ls."CONDITION_CODE" = '420' THEN '분석'
                            WHEN ls."CONDITION_CODE" = '500' THEN '창입'
                            WHEN ls."CONDITION_CODE" = '600' THEN '출하'
                            WHEN ls."CONDITION_CODE" = '190' THEN '이상'
                            WHEN ls."CONDITION_CODE" IN ('950', '952') THEN '정비'
                            WHEN ls."CONDITION_CODE" = '990' THEN '폐기'
                            ELSE '기타'
                        END as status,
                        COALESCE(ls."POSITION_USER_NAME", '') as location,
                        c."WITHSTAND_PRESSURE_MAINTE_DATE" as pressure_due_date,
                        ls."MOVE_DATE" as last_event_at,
                        GREATEST(
                            COALESCE(c."UPDATE_DATETIME", c."ADD_DATETIME"),
                            COALESCE(ls."MOVE_DATE", NOW())
                        ) as source_updated_at
                    FROM "{source_schema}"."ma_cylinders" c
                    LEFT JOIN "{source_schema}"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
                    LEFT JOIN "{source_schema}"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
                    LEFT JOIN "{source_schema}"."ma_valve_specs" vs ON c."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
                    LEFT JOIN "{source_schema}"."tr_latest_cylinder_statuses" ls ON RTRIM(c."CYLINDER_NO") = RTRIM(ls."CYLINDER_NO");
                """
                
                cursor.execute(create_cylinder_list_view_sql)
                self.stdout.write(self.style.SUCCESS("  vw_cynow_cylinder_list 생성 완료"))
                
                # 2. vw_cynow_inventory VIEW 생성 (cylinder_type_key 포함)
                self.stdout.write("vw_cynow_inventory VIEW 생성 중...")
                
                create_inventory_view_sql = f"""
                    CREATE OR REPLACE VIEW vw_cynow_inventory AS
                    SELECT 
                        MD5(
                            COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') || '|' ||
                            COALESCE(CAST(c."CAPACITY" AS TEXT), '') || '|' ||
                            COALESCE(vs."NAME", '') || '|' ||
                            COALESCE(cs."NAME", '') || '|' ||
                            COALESCE(c."USE_DEPARTMENT_CODE", '')
                        ) as cylinder_type_key,
                        COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') as gas_name,
                        c."CAPACITY" as capacity,
                        COALESCE(vs."NAME", '') as valve_spec,
                        COALESCE(cs."NAME", '') as cylinder_spec,
                        COALESCE(c."USE_DEPARTMENT_CODE", '') as usage_place,
                        CASE 
                            WHEN ls."CONDITION_CODE" IN ('100', '102') THEN '보관'
                            WHEN ls."CONDITION_CODE" IN ('210', '220') THEN '충전'
                            WHEN ls."CONDITION_CODE" = '420' THEN '분석'
                            WHEN ls."CONDITION_CODE" = '500' THEN '창입'
                            WHEN ls."CONDITION_CODE" = '600' THEN '출하'
                            WHEN ls."CONDITION_CODE" = '190' THEN '이상'
                            WHEN ls."CONDITION_CODE" IN ('950', '952') THEN '정비'
                            WHEN ls."CONDITION_CODE" = '990' THEN '폐기'
                            ELSE '기타'
                        END as status,
                        COALESCE(ls."POSITION_USER_NAME", '') as location,
                        COUNT(DISTINCT RTRIM(c."CYLINDER_NO")) as qty,
                        NOW() as updated_at
                    FROM "{source_schema}"."ma_cylinders" c
                    LEFT JOIN "{source_schema}"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
                    LEFT JOIN "{source_schema}"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
                    LEFT JOIN "{source_schema}"."ma_valve_specs" vs ON c."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
                    LEFT JOIN "{source_schema}"."tr_latest_cylinder_statuses" ls ON RTRIM(c."CYLINDER_NO") = RTRIM(ls."CYLINDER_NO")
                    GROUP BY 
                        cylinder_type_key,
                        gas_name,
                        c."CAPACITY",
                        valve_spec,
                        cylinder_spec,
                        usage_place,
                        status,
                        location;
                """
                
                cursor.execute(create_inventory_view_sql)
                self.stdout.write(self.style.SUCCESS("  vw_cynow_inventory 생성 완료"))
                
                # 3. VIEW 확인
                self.stdout.write("\nVIEW 확인 중...")
                cursor.execute("SELECT COUNT(*) FROM vw_cynow_inventory;")
                inventory_count = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM vw_cynow_cylinder_list;")
                cylinder_count = cursor.fetchone()[0]
                
                # 샘플 데이터 확인
                cursor.execute("SELECT gas_name, status, location, qty FROM vw_cynow_inventory LIMIT 5;")
                samples = cursor.fetchall()
                
                self.stdout.write(self.style.SUCCESS(f"\nVIEW 생성 완료!"))
                self.stdout.write(f"  vw_cynow_inventory: {inventory_count:,}개 행")
                self.stdout.write(f"  vw_cynow_cylinder_list: {cylinder_count:,}개 행")
                
                if samples:
                    self.stdout.write("\n샘플 데이터:")
                    for sample in samples:
                        self.stdout.write(f"  - {sample[0]} | {sample[1]} | {sample[2]} | {sample[3]}개")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"오류 발생: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())
            raise


