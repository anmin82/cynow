"""cy_cylinder_current 스냅샷 증분 갱신"""
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from core.utils.view_helper import parse_cylinder_spec, parse_valve_spec, parse_usage_place
from core.utils.cylinder_type import generate_cylinder_type_key
from datetime import timedelta
import hashlib
from core.utils.status_mapper import map_condition_code_to_status


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
                COALESCE(c."VALVE_SPEC_CODE", '') as valve_spec_code,
                COALESCE(vs."NAME", '') as valve_spec_name,
                COALESCE(c."CYLINDER_SPEC_CODE", '') as cylinder_spec_code,
                COALESCE(cs."NAME", '') as cylinder_spec_name,
                COALESCE(c."USE_DEPARTMENT_CODE", '') as usage_place,
                COALESCE(ls."POSITION_USER_NAME", '') as location,
                ls."CONDITION_CODE",
                ls."MOVE_DATE",
                c."WITHSTAND_PRESSURE_MAINTE_DATE",
                c."MANUFACTURE_DATE",
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
                if len(row) < 14:
                    self.stdout.write(self.style.WARNING(f"건너뜀 (용기번호: {cylinder_no}): 컬럼 부족 (expected 14, got {len(row)})"))
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
        
        # VIEW에서 전체 데이터 조회 (모두 가져옴)
        cursor.execute("""
            SELECT 
                c."CYLINDER_NO",
                COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') as gas_name,
                c."CAPACITY",
                COALESCE(c."VALVE_SPEC_CODE", '') as valve_spec_code,
                COALESCE(vs."NAME", '') as valve_spec_name,
                COALESCE(c."CYLINDER_SPEC_CODE", '') as cylinder_spec_code,
                COALESCE(cs."NAME", '') as cylinder_spec_name,
                COALESCE(c."USE_DEPARTMENT_CODE", '') as usage_place,
                COALESCE(ls."POSITION_USER_NAME", '') as location,
                ls."CONDITION_CODE",
                ls."MOVE_DATE",
                c."WITHSTAND_PRESSURE_MAINTE_DATE",
                c."MANUFACTURE_DATE",
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
        
        # 모든 데이터를 먼저 가져옴 (INSERT로 cursor가 덮어쓰이는 것을 방지)
        all_rows = cursor.fetchall()
        self.stdout.write(f"조회 완료: {len(all_rows)}건")
        
        total = 0
        for i in range(0, len(all_rows), batch_size):
            batch = all_rows[i:i+batch_size]
            
            with transaction.atomic():
                for row in batch:
                    try:
                        if row and len(row) >= 14:
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
                COALESCE(c."VALVE_SPEC_CODE", '') as valve_spec_code,
                COALESCE(vs."NAME", '') as valve_spec_name,
                COALESCE(c."CYLINDER_SPEC_CODE", '') as cylinder_spec_code,
                COALESCE(cs."NAME", '') as cylinder_spec_name,
                COALESCE(c."USE_DEPARTMENT_CODE", '') as usage_place,
                COALESCE(ls."POSITION_USER_NAME", '') as location,
                ls."CONDITION_CODE",
                ls."MOVE_DATE",
                c."WITHSTAND_PRESSURE_MAINTE_DATE",
                c."MANUFACTURE_DATE",
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
        """단일 용기 Upsert (실제 테이블 구조에 맞춤)"""
        # Raw 값 추출 (인덱스 변경됨)
        cylinder_no = raw_data[0]
        raw_gas_name = raw_data[1] or ''
        raw_capacity = raw_data[2]
        raw_valve_spec_code = raw_data[3] or ''
        raw_valve_spec_name = raw_data[4] or ''
        raw_cylinder_spec_code = raw_data[5] or ''
        raw_cylinder_spec_name = raw_data[6] or ''
        raw_usage_place = raw_data[7] or ''
        raw_location = raw_data[8] or ''
        raw_condition_code = raw_data[9] or ''
        raw_move_date = raw_data[10]
        raw_withstand_pressure_mainte_date = raw_data[11]
        manufacture_date = raw_data[12]
        source_updated_at = raw_data[13]
        
        # 폐기/정비 상태가 잘못 기록된 경우, 히스토리 테이블의 최신 상태로 보정
        if raw_condition_code in ('950', '952'):
            latest_code = self.get_latest_condition_code(cursor, cylinder_no)
            if latest_code and latest_code not in ('950', '952'):
                raw_condition_code = latest_code
        
        # 상태 변환 (status_mapper 표준 매핑 사용)
        dashboard_status = self.map_condition_code(raw_condition_code)
        
        # EndUser 결정 (1. 예외 확인 -> 2. 기본값 조회)
        dashboard_enduser = self.get_enduser_with_exception(
            cursor, cylinder_no, raw_gas_name, raw_capacity, 
            raw_valve_spec_code, raw_cylinder_spec_code
        )
        
        # 밸브 그룹 조회
        dashboard_valve_group_name = self.get_valve_group(
            cursor, raw_valve_spec_code, raw_valve_spec_name
        )
        
        # 용기종류 키 생성 (밸브 그룹 있으면 그룹명 사용, 없으면 밸브 코드 사용)
        valve_key = dashboard_valve_group_name if dashboard_valve_group_name else raw_valve_spec_code
        cylinder_type_key = self.generate_type_key(
            raw_gas_name, raw_capacity, valve_key, raw_cylinder_spec_code, dashboard_enduser
        )
        
        # 파생 필드: 가용 용기 상태
        # 가용 = 보관 상태(미회수/회수)만
        available_statuses = {'보관:미회수', '보관:회수'}
        is_available = dashboard_status in available_statuses
        
        # 압력시험 만료일 계산
        if raw_withstand_pressure_mainte_date:
            pressure_test_date = raw_withstand_pressure_mainte_date
            pressure_test_term = 5  # 기본 5년
            # 압력시험 만료일 = 압력시험일 + 5년 (Python으로 계산)
            try:
                pressure_expire_date = pressure_test_date + timedelta(days=365*5)
            except:
                pressure_expire_date = None
        else:
            pressure_test_date = None
            pressure_test_term = None
            pressure_expire_date = None
        
        # Upsert 실행 (실제 테이블 구조에 맞춤)
        cursor.execute("""
            INSERT INTO cy_cylinder_current (
                cylinder_no,
                raw_gas_name, raw_capacity,
                raw_valve_spec_code, raw_valve_spec_name,
                raw_cylinder_spec_code, raw_cylinder_spec_name,
                raw_usage_place, raw_location, raw_condition_code, raw_position_user_name,
                dashboard_gas_name, dashboard_capacity,
                dashboard_valve_spec_code, dashboard_valve_spec_name, dashboard_valve_group_name,
                dashboard_cylinder_spec_code, dashboard_cylinder_spec_name,
                dashboard_usage_place, dashboard_location,
                dashboard_status, dashboard_enduser,
                cylinder_type_key, cylinder_type_key_raw,
                condition_code, move_date, pressure_due_date, last_event_at,
                source_updated_at, snapshot_updated_at,
                status_category, is_available,
                manufacture_date, pressure_test_date, pressure_test_term, pressure_expire_date,
                needs_fcms_fix
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s,
                %s, %s, %s, %s, FALSE
            )
            ON CONFLICT (cylinder_no) DO UPDATE SET
                raw_gas_name = EXCLUDED.raw_gas_name,
                raw_capacity = EXCLUDED.raw_capacity,
                raw_valve_spec_code = EXCLUDED.raw_valve_spec_code,
                raw_valve_spec_name = EXCLUDED.raw_valve_spec_name,
                raw_cylinder_spec_code = EXCLUDED.raw_cylinder_spec_code,
                raw_cylinder_spec_name = EXCLUDED.raw_cylinder_spec_name,
                raw_usage_place = EXCLUDED.raw_usage_place,
                raw_location = EXCLUDED.raw_location,
                raw_condition_code = EXCLUDED.raw_condition_code,
                raw_position_user_name = EXCLUDED.raw_position_user_name,
                dashboard_gas_name = EXCLUDED.dashboard_gas_name,
                dashboard_capacity = EXCLUDED.dashboard_capacity,
                dashboard_valve_spec_code = EXCLUDED.dashboard_valve_spec_code,
                dashboard_valve_spec_name = EXCLUDED.dashboard_valve_spec_name,
                dashboard_valve_group_name = EXCLUDED.dashboard_valve_group_name,
                dashboard_cylinder_spec_code = EXCLUDED.dashboard_cylinder_spec_code,
                dashboard_cylinder_spec_name = EXCLUDED.dashboard_cylinder_spec_name,
                dashboard_usage_place = EXCLUDED.dashboard_usage_place,
                dashboard_location = EXCLUDED.dashboard_location,
                dashboard_status = EXCLUDED.dashboard_status,
                dashboard_enduser = EXCLUDED.dashboard_enduser,
                cylinder_type_key = EXCLUDED.cylinder_type_key,
                cylinder_type_key_raw = EXCLUDED.cylinder_type_key_raw,
                condition_code = EXCLUDED.condition_code,
                move_date = EXCLUDED.move_date,
                pressure_due_date = EXCLUDED.pressure_due_date,
                last_event_at = EXCLUDED.last_event_at,
                source_updated_at = EXCLUDED.source_updated_at,
                snapshot_updated_at = NOW(),
                status_category = EXCLUDED.status_category,
                is_available = EXCLUDED.is_available,
                manufacture_date = EXCLUDED.manufacture_date,
                pressure_test_date = EXCLUDED.pressure_test_date,
                pressure_test_term = EXCLUDED.pressure_test_term,
                pressure_expire_date = EXCLUDED.pressure_expire_date
        """, [
            # 1: cylinder_no
            cylinder_no,
            # 2-3: raw 가스
            raw_gas_name, raw_capacity,
            # 4-7: raw 밸브 & 용기
            raw_valve_spec_code, raw_valve_spec_name,
            raw_cylinder_spec_code, raw_cylinder_spec_name,
            # 8-11: raw 사용처, 위치, 상태
            raw_usage_place, raw_location, raw_condition_code, raw_location,
            # 12-13: dashboard 가스
            raw_gas_name, raw_capacity,
            # 14-16: dashboard 밸브
            raw_valve_spec_code, raw_valve_spec_name, dashboard_valve_group_name,
            # 17-18: dashboard 용기
            raw_cylinder_spec_code, raw_cylinder_spec_name,
            # 19-20: dashboard 사용처, 위치
            raw_usage_place, raw_location,
            # 21-22: dashboard 상태, enduser
            dashboard_status, dashboard_enduser,
            # 23-24: cylinder_type_key
            cylinder_type_key, cylinder_type_key,
            # 25-28: condition, dates
            raw_condition_code, raw_move_date, raw_withstand_pressure_mainte_date, raw_move_date,
            # 29: source_updated_at
            source_updated_at,
            # 30-31: status_category, is_available
            dashboard_status, is_available,
            # 32-35: 제조일, 압력시험일, 주기, 만료일
            manufacture_date, pressure_test_date, pressure_test_term, pressure_expire_date
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
    
    def generate_type_key(self, gas_name, capacity, valve_key, cylinder_spec_code, enduser_code):
        """
        용기종류 키 생성 (밸브 그룹 + EndUser 기반)
        - valve_key: 밸브 그룹명 (있으면) 또는 밸브 코드
        - 이렇게 하면 NERIKI와 HAMAI가 같은 그룹이면 하나의 카드로 통합됨
        """
        key_string = f"{gas_name}|{capacity or ''}|{valve_key or ''}|{cylinder_spec_code or ''}|{enduser_code or ''}"
        return hashlib.md5(key_string.encode('utf-8')).hexdigest()
    
    def get_latest_condition_code(self, cursor, cylinder_no):
        """tr_cylinder_status_histories에서 최신 CONDITION_CODE 조회"""
        try:
            cursor.execute("""
                SELECT "CONDITION_CODE"
                FROM "fcms_cdc"."tr_cylinder_status_histories"
                WHERE RTRIM("CYLINDER_NO") = RTRIM(%s)
                ORDER BY "MOVE_DATE" DESC
                LIMIT 1
            """, [cylinder_no])
            row = cursor.fetchone()
            return row[0] if row else None
        except Exception:
            return None
    
    def get_enduser_with_exception(self, cursor, cylinder_no, gas_name, capacity, valve_spec_code, cylinder_spec_code):
        """EndUser 결정 (예외 우선, 그 다음 기본값)"""
        # 1. 개별 용기 예외 확인 (RTRIM으로 공백 제거)
        try:
            cursor.execute("""
                SELECT enduser
                FROM cy_enduser_exception
                WHERE RTRIM(cylinder_no) = RTRIM(%s) AND is_active = TRUE
                LIMIT 1
            """, [cylinder_no])
            
            result = cursor.fetchone()
            if result:
                return result[0]
        except Exception as e:
            # 디버그용: 오류 출력
            print(f"Warning: EndUserException lookup failed for {cylinder_no}: {str(e)}")
            pass
        
        # 2. 기본값 조회
        return self.get_enduser_from_default(cursor, gas_name, capacity, valve_spec_code, cylinder_spec_code)
    
    def get_valve_group(self, cursor, valve_spec_code, valve_spec_name):
        """밸브 그룹 조회"""
        try:
            cursor.execute("""
                SELECT vg.group_name
                FROM cy_valve_group_mapping vgm
                JOIN cy_valve_group vg ON vgm.group_id = vg.id
                WHERE vgm.valve_spec_code = %s
                AND vgm.valve_spec_name = %s
                AND vgm.is_active = TRUE
                AND vg.is_active = TRUE
                LIMIT 1
            """, [valve_spec_code, valve_spec_name])
            
            result = cursor.fetchone()
            if result:
                return result[0]
        except Exception:
            pass
        
        return ''
    
    def get_enduser_from_default(self, cursor, gas_name, capacity, valve_spec_code, cylinder_spec_code):
        """EndUserDefault 테이블에서 EndUser 조회"""
        try:
            # 정확히 매칭되는 설정 찾기
            cursor.execute("""
                SELECT default_enduser
                FROM cy_enduser_default
                WHERE gas_name = %s
                AND capacity = %s
                AND valve_spec_code = %s
                AND cylinder_spec_code = %s
                AND is_active = TRUE
                LIMIT 1
            """, [gas_name, capacity, valve_spec_code or '', cylinder_spec_code or ''])
            
            result = cursor.fetchone()
            if result:
                return result[0]
            
            # 밸브/용기 코드 없이 가스명+용량만으로 매칭
            cursor.execute("""
                SELECT default_enduser
                FROM cy_enduser_default
                WHERE gas_name = %s
                AND capacity = %s
                AND (valve_spec_code IS NULL OR valve_spec_code = '')
                AND (cylinder_spec_code IS NULL OR cylinder_spec_code = '')
                AND is_active = TRUE
                LIMIT 1
            """, [gas_name, capacity])
            
            result = cursor.fetchone()
            if result:
                return result[0]
            
            # 전체 기본값 조회 (가스명, 용량 모두 매칭 안 될 때)
            cursor.execute("""
                SELECT default_enduser
                FROM cy_enduser_default
                WHERE (gas_name IS NULL OR gas_name = '')
                AND capacity IS NULL
                AND (valve_spec_code IS NULL OR valve_spec_code = '')
                AND (cylinder_spec_code IS NULL OR cylinder_spec_code = '')
                AND is_active = TRUE
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            if result:
                return result[0]
            
        except Exception as e:
            # 오류 발생 시 기본값 반환
            pass
        
        # 매칭 실패 시 최종 기본값
        return 'FPK'
    
    def map_condition_code(self, code):
        """상태 코드 → 상태명 변환"""
        if not code:
            return '기타'
        status = map_condition_code_to_status(code)
        return status or '기타'

