"""cy_cylinder_current 스냅샷 증분 갱신"""
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from core.utils.view_helper import parse_cylinder_spec, parse_valve_spec, parse_usage_place
from core.utils.cylinder_type import generate_cylinder_type_key
import hashlib


class Command(BaseCommand):
    help = 'cy_cylinder_current 스냅샷 증분 갱신 (CDC 이벤트 기반)'
    
    def add_arguments(self, parser):
        parser.add_argument('--full', action='store_true', help='전체 재생성')
        parser.add_argument('--cylinder-no', type=str, help='특정 용기만 갱신')
        parser.add_argument('--batch-size', type=int, default=1000, help='배치 크기')
    
    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            if options['full']:
                self.full_sync(cursor, options['batch_size'])
            elif options['cylinder_no']:
                self.sync_single(cursor, options['cylinder_no'])
            else:
                self.incremental_sync(cursor, options['batch_size'])
    
    def incremental_sync(self, cursor, batch_size):
        """증분 갱신: VIEW와 스냅샷 비교하여 변경된 것만 업데이트"""
        self.stdout.write("증분 갱신 시작...")
        
        # 1. VIEW에서 최신 데이터 조회 (변경된 것만)
        cursor.execute("""
            SELECT 
                c."CYLINDER_NO",
                COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') as gas_name,
                c."CAPACITY",
                COALESCE(vs."NAME", '') as valve_spec,
                COALESCE(cs."NAME", '') as cylinder_spec,
                COALESCE(c."USE_DEPARTMENT_CODE", '') as usage_place,
                COALESCE(ls."POSITION_USER_NAME", '') as location,
                ls."CONDITION_CODE",
                ls."MOVE_DATE",
                c."WITHSTAND_PRESSURE_MAINTE_DATE",
                GREATEST(
                    COALESCE(c."UPDATE_DATETIME", c."ADD_DATETIME"),
                    COALESCE(ls."MOVE_DATE", NOW())
                ) as source_updated_at
            FROM "fcms_cdc"."ma_cylinders" c
            LEFT JOIN "fcms_cdc"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
            LEFT JOIN "fcms_cdc"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
            LEFT JOIN "fcms_cdc"."ma_valve_specs" vs ON c."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
            LEFT JOIN "fcms_cdc"."tr_latest_cylinder_statuses" ls ON c."CYLINDER_NO" = ls."CYLINDER_NO"
            WHERE c."CYLINDER_NO" IN (
                SELECT cylinder_no FROM cy_cylinder_current
                WHERE snapshot_updated_at < NOW() - INTERVAL '5 minutes'
                OR source_updated_at > snapshot_updated_at
            )
            OR c."CYLINDER_NO" NOT IN (SELECT cylinder_no FROM cy_cylinder_current)
            ORDER BY c."CYLINDER_NO"
            LIMIT %s
        """, [batch_size])
        
        rows = cursor.fetchall()
        self.stdout.write(f"갱신 대상: {len(rows)}건")
        
        updated = 0
        for row in rows:
            try:
                cylinder_no = row[0] if row and len(row) > 0 else 'UNKNOWN'
                if not row:
                    self.stdout.write(self.style.WARNING(f"건너뜀 (용기번호: {cylinder_no}): 데이터 없음"))
                    continue
                if len(row) < 11:
                    self.stdout.write(self.style.WARNING(f"건너뜀 (용기번호: {cylinder_no}): 컬럼 부족 (expected 11, got {len(row)})"))
                    continue
                self.upsert_cylinder(cursor, row)
                updated += 1
            except Exception as e:
                cylinder_no = row[0] if row and len(row) > 0 else 'UNKNOWN'
                self.stdout.write(self.style.ERROR(f"오류 (용기번호: {cylinder_no}): {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(f"갱신 완료: {updated}건"))
    
    def full_sync(self, cursor, batch_size):
        """전체 재생성"""
        self.stdout.write("전체 재생성 시작...")
        
        # 기존 데이터 삭제
        cursor.execute("TRUNCATE TABLE cy_cylinder_current;")
        self.stdout.write("기존 데이터 삭제 완료")
        
        # VIEW에서 전체 데이터 조회
        cursor.execute("""
            SELECT 
                c."CYLINDER_NO",
                COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') as gas_name,
                c."CAPACITY",
                COALESCE(vs."NAME", '') as valve_spec,
                COALESCE(cs."NAME", '') as cylinder_spec,
                COALESCE(c."USE_DEPARTMENT_CODE", '') as usage_place,
                COALESCE(ls."POSITION_USER_NAME", '') as location,
                ls."CONDITION_CODE",
                ls."MOVE_DATE",
                c."WITHSTAND_PRESSURE_MAINTE_DATE",
                GREATEST(
                    COALESCE(c."UPDATE_DATETIME", c."ADD_DATETIME"),
                    COALESCE(ls."MOVE_DATE", NOW())
                ) as source_updated_at
            FROM "fcms_cdc"."ma_cylinders" c
            LEFT JOIN "fcms_cdc"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
            LEFT JOIN "fcms_cdc"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
            LEFT JOIN "fcms_cdc"."ma_valve_specs" vs ON c."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
            LEFT JOIN "fcms_cdc"."tr_latest_cylinder_statuses" ls ON c."CYLINDER_NO" = ls."CYLINDER_NO"
            ORDER BY c."CYLINDER_NO"
        """)
        
        total = 0
        while True:
            rows = cursor.fetchmany(batch_size)
            if not rows:
                break
            
            with transaction.atomic():
                for row in rows:
                    try:
                        if row and len(row) >= 11:
                            self.upsert_cylinder(cursor, row)
                            total += 1
                    except Exception as e:
                        cylinder_no = row[0] if row and len(row) > 0 else 'UNKNOWN'
                        self.stdout.write(self.style.ERROR(f"오류 (용기번호: {cylinder_no}): {str(e)}"))
            
            self.stdout.write(f"진행: {total}건 처리됨")
        
        self.stdout.write(self.style.SUCCESS(f"전체 재생성 완료: {total}건"))
    
    def sync_single(self, cursor, cylinder_no):
        """단일 용기 갱신"""
        cursor.execute("""
            SELECT 
                c."CYLINDER_NO",
                COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') as gas_name,
                c."CAPACITY",
                COALESCE(vs."NAME", '') as valve_spec,
                COALESCE(cs."NAME", '') as cylinder_spec,
                COALESCE(c."USE_DEPARTMENT_CODE", '') as usage_place,
                COALESCE(ls."POSITION_USER_NAME", '') as location,
                ls."CONDITION_CODE",
                ls."MOVE_DATE",
                c."WITHSTAND_PRESSURE_MAINTE_DATE",
                GREATEST(
                    COALESCE(c."UPDATE_DATETIME", c."ADD_DATETIME"),
                    COALESCE(ls."MOVE_DATE", NOW())
                ) as source_updated_at
            FROM "fcms_cdc"."ma_cylinders" c
            LEFT JOIN "fcms_cdc"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
            LEFT JOIN "fcms_cdc"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
            LEFT JOIN "fcms_cdc"."ma_valve_specs" vs ON c."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
            LEFT JOIN "fcms_cdc"."tr_latest_cylinder_statuses" ls ON c."CYLINDER_NO" = ls."CYLINDER_NO"
            WHERE c."CYLINDER_NO" = %s
        """, [cylinder_no])
        
        row = cursor.fetchone()
        if row:
            self.upsert_cylinder(cursor, row)
            self.stdout.write(self.style.SUCCESS(f"용기 {cylinder_no} 갱신 완료"))
        else:
            # 용기 삭제된 경우
            cursor.execute("DELETE FROM cy_cylinder_current WHERE cylinder_no = %s", [cylinder_no])
            self.stdout.write(f"용기 {cylinder_no} 삭제됨 (스냅샷에서 제거)")
    
    def upsert_cylinder(self, cursor, raw_data):
        """단일 용기 Upsert (간소화 버전)"""
        # Raw 값 추출
        cylinder_no = raw_data[0]
        raw_gas_name = raw_data[1] or ''
        raw_capacity = raw_data[2]
        raw_valve_spec = raw_data[3] or ''
        raw_cylinder_spec = raw_data[4] or ''
        raw_usage_place = raw_data[5] or ''
        raw_location = raw_data[6] or ''
        raw_condition_code = raw_data[7] or ''
        raw_move_date = raw_data[8]
        raw_withstand_pressure_mainte_date = raw_data[9]
        source_updated_at = raw_data[10]
        
        # 간단한 파싱 (오류 발생 시 빈 문자열)
        try:
            valve_parsed = parse_valve_spec(raw_valve_spec)
            valve_format = valve_parsed.get('format', '') if isinstance(valve_parsed, dict) else ''
            valve_material = valve_parsed.get('material', '') if isinstance(valve_parsed, dict) else ''
        except:
            valve_format = ''
            valve_material = ''
        
        try:
            cylinder_parsed = parse_cylinder_spec(raw_cylinder_spec)
            cylinder_format = cylinder_parsed.get('format', '') if isinstance(cylinder_parsed, dict) else ''
            cylinder_material = cylinder_parsed.get('material', '') if isinstance(cylinder_parsed, dict) else ''
        except:
            cylinder_format = ''
            cylinder_material = ''
        
        # 사용처 (간단 버전)
        dashboard_usage_place = raw_usage_place or ''
        
        # 기본 EndUser
        enduser_code = 'SDC'
        enduser_name = 'SDC'
        
        # 상태 변환
        dashboard_status = self.map_condition_code(raw_condition_code)
        
        # 위치
        dashboard_location = raw_location or ''
        
        # 용기종류 키 (간단 버전)
        dashboard_cylinder_type_key = self.generate_type_key(
            raw_gas_name, raw_capacity, raw_valve_spec,
            raw_cylinder_spec, dashboard_usage_place, enduser_code
        )
        
        # 밸브 스펙 (원본 사용)
        dashboard_valve_spec = raw_valve_spec
        
        # 파생 필드
        is_available = dashboard_status in ('보관', '충전')
        
        # Upsert 실행
        cursor.execute("""
            INSERT INTO cy_cylinder_current (
                cylinder_no,
                raw_gas_name, raw_capacity, raw_valve_spec, raw_cylinder_spec,
                raw_usage_place, raw_location, raw_condition_code,
                raw_position_user_name, raw_move_date, raw_withstand_pressure_mainte_date,
                dashboard_gas_name, dashboard_capacity,
                dashboard_valve_spec, dashboard_valve_format, dashboard_valve_material,
                dashboard_cylinder_spec, dashboard_cylinder_format, dashboard_cylinder_material,
                dashboard_enduser_code, dashboard_enduser_name, dashboard_usage_place,
                dashboard_status, dashboard_location,
                dashboard_cylinder_type_key,
                dashboard_pressure_due_date, dashboard_last_event_at,
                is_available,
                source_updated_at, snapshot_updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            )
            ON CONFLICT (cylinder_no) DO UPDATE SET
                raw_gas_name = EXCLUDED.raw_gas_name,
                raw_capacity = EXCLUDED.raw_capacity,
                raw_valve_spec = EXCLUDED.raw_valve_spec,
                raw_cylinder_spec = EXCLUDED.raw_cylinder_spec,
                raw_usage_place = EXCLUDED.raw_usage_place,
                raw_location = EXCLUDED.raw_location,
                raw_condition_code = EXCLUDED.raw_condition_code,
                raw_move_date = EXCLUDED.raw_move_date,
                raw_withstand_pressure_mainte_date = EXCLUDED.raw_withstand_pressure_mainte_date,
                dashboard_gas_name = EXCLUDED.dashboard_gas_name,
                dashboard_capacity = EXCLUDED.dashboard_capacity,
                dashboard_valve_spec = EXCLUDED.dashboard_valve_spec,
                dashboard_valve_format = EXCLUDED.dashboard_valve_format,
                dashboard_valve_material = EXCLUDED.dashboard_valve_material,
                dashboard_cylinder_spec = EXCLUDED.dashboard_cylinder_spec,
                dashboard_cylinder_format = EXCLUDED.dashboard_cylinder_format,
                dashboard_cylinder_material = EXCLUDED.dashboard_cylinder_material,
                dashboard_enduser_code = EXCLUDED.dashboard_enduser_code,
                dashboard_enduser_name = EXCLUDED.dashboard_enduser_name,
                dashboard_usage_place = EXCLUDED.dashboard_usage_place,
                dashboard_status = EXCLUDED.dashboard_status,
                dashboard_location = EXCLUDED.dashboard_location,
                dashboard_cylinder_type_key = EXCLUDED.dashboard_cylinder_type_key,
                dashboard_pressure_due_date = EXCLUDED.dashboard_pressure_due_date,
                dashboard_last_event_at = EXCLUDED.dashboard_last_event_at,
                is_available = EXCLUDED.is_available,
                source_updated_at = EXCLUDED.source_updated_at,
                snapshot_updated_at = NOW()
        """, [
            cylinder_no,
            raw_gas_name, raw_capacity, raw_valve_spec, raw_cylinder_spec,
            raw_usage_place, raw_location, raw_condition_code,
            raw_location, raw_move_date, raw_withstand_pressure_mainte_date,
            raw_gas_name, raw_capacity,  # dashboard_gas_name (번역은 별도)
            dashboard_valve_spec, valve_format, valve_material,
            raw_cylinder_spec, cylinder_format, cylinder_material,
            enduser_code, enduser_name, dashboard_usage_place,
            dashboard_status, dashboard_location,
            dashboard_cylinder_type_key,
            raw_withstand_pressure_mainte_date, raw_move_date,
            is_available,
            source_updated_at
        ])
    
    def apply_valve_alias(self, cursor, raw_valve_spec):
        """밸브 표준화 정책 적용"""
        if not raw_valve_spec:
            return ''
        try:
            # ValveAlias 테이블이 존재하는지 확인 후 사용
            cursor.execute("""
                SELECT standard_valve_spec 
                FROM core_valvealias
                WHERE raw_valve_spec = %s AND is_active = TRUE
                ORDER BY priority ASC
                LIMIT 1
            """, [raw_valve_spec])
            result = cursor.fetchone()
            if result and len(result) >= 1:
                return result[0]
        except Exception:
            pass
        return raw_valve_spec
    
    def apply_enduser_policy(self, cursor, type_key, gas_name, capacity):
        """EndUser 정책 적용"""
        try:
            # 1. cylinder_type_key로 정확히 매칭되는 예외 찾기
            cursor.execute("""
                SELECT exception_enduser_code, exception_enduser_name
                FROM core_enduserpolicy
                WHERE cylinder_type_key = %s AND is_active = TRUE
                ORDER BY id DESC
                LIMIT 1
            """, [type_key])
            result = cursor.fetchone()
            if result and len(result) >= 2 and result[0]:
                return result[0], result[1]
        except Exception:
            pass
        
        try:
            # 2. 기본값 반환
            cursor.execute("""
                SELECT default_enduser_code, default_enduser_name
                FROM core_enduserpolicy
                WHERE cylinder_type_key IS NULL AND is_active = TRUE
                ORDER BY id DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            if result and len(result) >= 2:
                return result[0], result[1]
        except Exception:
            pass
        
        # 3. 하드코딩 기본값 (테이블이 없으면 이 값 사용)
        return 'SDC', 'SDC'
    
    def generate_type_key(self, gas_name, capacity, valve_spec, cylinder_spec, usage_place, enduser_code):
        """용기종류 키 생성 (enduser 포함)"""
        key_string = f"{gas_name}|{capacity or ''}|{valve_spec or ''}|{cylinder_spec or ''}|{usage_place or ''}|{enduser_code or ''}"
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def map_condition_code(self, code):
        """상태 코드 → 상태명 변환"""
        if not code:
            return '기타'
        mapping = {
            '100': '보관', '102': '보관',
            '210': '충전', '220': '충전',
            '420': '분석',
            '500': '창입',
            '600': '출하',
            '190': '이상',
            '950': '폐기', '952': '폐기',
        }
        return mapping.get(code, '기타')

