"""SQLite 모의 테이블 및 VIEW 생성"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'SQLite 모의 테이블 및 VIEW 생성'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # 기존 테이블/VIEW 삭제 (있는 경우)
            cursor.execute("DROP VIEW IF EXISTS vw_cynow_cylinder_list")
            cursor.execute("DROP VIEW IF EXISTS vw_cynow_inventory")
            cursor.execute("DROP TABLE IF EXISTS fcms_cylinders")
            
            # 모의 소스 테이블 생성 (capacity, usage_place 추가)
            self.stdout.write("Creating mock source table...")
            cursor.execute("""
                CREATE TABLE fcms_cylinders (
                    CYLINDER_NO TEXT PRIMARY KEY,
                    CYLINDER_NO_RAW TEXT,
                    POSITION_USER_NAME TEXT,
                    CONDITION_CODE TEXT,
                    CONDITION_NAME TEXT,
                    SHIPPING_COUNT INTEGER,
                    ITEM_CODE TEXT,
                    GAS_NAME TEXT,
                    CAPACITY TEXT,
                    USAGE_PLACE TEXT,
                    CYLINDER_SPEC_CODE TEXT,
                    CYLINDER_SPEC_NAME TEXT,
                    VALVE_SPEC_CODE TEXT,
                    VALVE_SPEC_NAME TEXT,
                    MANUFACTURE_DATE DATETIME,
                    LAST_PRESSURE_TEST_DATE DATETIME,
                    NEXT_PRESSURE_TEST_DUE_DATE DATETIME
                )
            """)
            
            # 인덱스 생성
            cursor.execute("CREATE INDEX idx_fcms_cylinders_gas_name ON fcms_cylinders(GAS_NAME)")
            cursor.execute("CREATE INDEX idx_fcms_cylinders_condition_code ON fcms_cylinders(CONDITION_CODE)")
            cursor.execute("CREATE INDEX idx_fcms_cylinders_position ON fcms_cylinders(POSITION_USER_NAME)")
            
            # vw_cynow_cylinder_list VIEW 생성
            self.stdout.write("Creating vw_cynow_cylinder_list VIEW...")
            cursor.execute("""
                CREATE VIEW vw_cynow_cylinder_list AS
                SELECT 
                    c.CYLINDER_NO as cylinder_no,
                    c.GAS_NAME as gas_name,
                    c.CAPACITY as capacity,
                    c.VALVE_SPEC_NAME as valve_spec,
                    c.CYLINDER_SPEC_NAME as cylinder_spec,
                    c.USAGE_PLACE as usage_place,
                    CASE 
                        WHEN c.CONDITION_CODE IN ('100', '102') THEN '보관'
                        WHEN c.CONDITION_CODE IN ('210', '220') THEN '충전'
                        WHEN c.CONDITION_CODE = '420' THEN '분석'
                        WHEN c.CONDITION_CODE = '500' THEN '창입'
                        WHEN c.CONDITION_CODE = '600' THEN '출하'
                        WHEN c.CONDITION_CODE = '190' THEN '이상'
                        WHEN c.CONDITION_CODE IN ('950', '952') THEN '정비'
                        WHEN c.CONDITION_CODE = '990' THEN '폐기'
                        ELSE '기타'
                    END as status,
                    c.POSITION_USER_NAME as location,
                    c.NEXT_PRESSURE_TEST_DUE_DATE as pressure_due_date,
                    c.LAST_PRESSURE_TEST_DATE as last_event_at,
                    datetime('now') as source_updated_at
                FROM fcms_cylinders c
            """)
            
            # vw_cynow_inventory VIEW 생성
            self.stdout.write("Creating vw_cynow_inventory VIEW...")
            cursor.execute("""
                CREATE VIEW vw_cynow_inventory AS
                SELECT 
                    '' as cylinder_type_key,
                    c.GAS_NAME as gas_name,
                    c.CAPACITY as capacity,
                    c.VALVE_SPEC_NAME as valve_spec,
                    c.CYLINDER_SPEC_NAME as cylinder_spec,
                    c.USAGE_PLACE as usage_place,
                    CASE 
                        WHEN c.CONDITION_CODE IN ('100', '102') THEN '보관'
                        WHEN c.CONDITION_CODE IN ('210', '220') THEN '충전'
                        WHEN c.CONDITION_CODE = '420' THEN '분석'
                        WHEN c.CONDITION_CODE = '500' THEN '창입'
                        WHEN c.CONDITION_CODE = '600' THEN '출하'
                        WHEN c.CONDITION_CODE = '190' THEN '이상'
                        WHEN c.CONDITION_CODE IN ('950', '952') THEN '정비'
                        WHEN c.CONDITION_CODE = '990' THEN '폐기'
                        ELSE '기타'
                    END as status,
                    c.POSITION_USER_NAME as location,
                    COUNT(DISTINCT c.CYLINDER_NO) as qty,
                    datetime('now') as updated_at
                FROM fcms_cylinders c
                GROUP BY 
                    c.GAS_NAME,
                    c.CAPACITY,
                    c.VALVE_SPEC_NAME,
                    c.CYLINDER_SPEC_NAME,
                    c.USAGE_PLACE,
                    status,
                    c.POSITION_USER_NAME
            """)
            
            self.stdout.write(self.style.SUCCESS('Successfully created mock tables and views!'))
