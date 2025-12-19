"""CYNOW 테이블 생성 (cy_cylinder_current)"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'cy_cylinder_current 스냅샷 테이블 생성'
    
    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            self.stdout.write("cy_cylinder_current 테이블 생성 중...")
            
            # 기존 테이블 삭제 (있으면)
            cursor.execute("DROP TABLE IF EXISTS cy_cylinder_current CASCADE;")
            
            # 테이블 생성
            cursor.execute("""
                CREATE TABLE cy_cylinder_current (
                    -- 식별자
                    cylinder_no VARCHAR(12) PRIMARY KEY,
                    
                    -- ===== FCMS Raw 값 (감사/이력용, 변경 불가) =====
                    raw_gas_name VARCHAR(100),
                    raw_capacity NUMERIC,
                    raw_valve_spec VARCHAR(180),
                    raw_cylinder_spec VARCHAR(180),
                    raw_usage_place VARCHAR(100),
                    raw_location VARCHAR(90),
                    raw_condition_code VARCHAR(10),
                    raw_position_user_name VARCHAR(90),
                    raw_move_date TIMESTAMP,
                    raw_withstand_pressure_mainte_date TIMESTAMP,
                    
                    -- ===== CYNOW Dashboard 값 (정책 적용) =====
                    -- 가스 정보
                    dashboard_gas_name VARCHAR(100),
                    dashboard_capacity NUMERIC,
                    
                    -- 밸브 정보 (표준화 적용)
                    dashboard_valve_spec VARCHAR(180),
                    dashboard_valve_format VARCHAR(50),
                    dashboard_valve_material VARCHAR(50),
                    
                    -- 용기 정보
                    dashboard_cylinder_spec VARCHAR(180),
                    dashboard_cylinder_format VARCHAR(50),
                    dashboard_cylinder_material VARCHAR(50),
                    
                    -- EndUser 정보 (정책 적용)
                    dashboard_enduser_code VARCHAR(50),
                    dashboard_enduser_name VARCHAR(100),
                    dashboard_usage_place VARCHAR(100),
                    
                    -- 상태 정보
                    dashboard_status VARCHAR(20),
                    dashboard_location VARCHAR(90),
                    
                    -- 용기종류 키 (정책 적용 후)
                    dashboard_cylinder_type_key VARCHAR(32),
                    
                    -- 날짜 정보
                    dashboard_pressure_due_date TIMESTAMP,
                    dashboard_last_event_at TIMESTAMP,
                    
                    -- ===== 집계/예측용 파생 필드 =====
                    is_available BOOLEAN,
                    available_days INTEGER,
                    risk_level VARCHAR(10),
                    
                    -- ===== 메타데이터 =====
                    source_updated_at TIMESTAMP,
                    snapshot_updated_at TIMESTAMP DEFAULT NOW(),
                    policy_version INTEGER DEFAULT 1
                );
            """)
            
            # 인덱스 생성
            indexes = [
                ("idx_cy_current_type_key", "dashboard_cylinder_type_key"),
                ("idx_cy_current_gas", "LOWER(dashboard_gas_name)"),
                ("idx_cy_current_status", "LOWER(dashboard_status)"),
                ("idx_cy_current_enduser", "dashboard_enduser_code"),
                ("idx_cy_current_location", "dashboard_location"),
                ("idx_cy_current_updated", "snapshot_updated_at"),
            ]
            
            for idx_name, idx_col in indexes:
                try:
                    cursor.execute(f"""
                        CREATE INDEX IF NOT EXISTS {idx_name} 
                        ON cy_cylinder_current({idx_col});
                    """)
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"  인덱스 {idx_name} 생성 실패: {str(e)}"))
            
            # 부분 인덱스
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_cy_current_available 
                    ON cy_cylinder_current(is_available) 
                    WHERE is_available = TRUE;
                """)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  인덱스 idx_cy_current_available 생성 실패: {str(e)}"))
            
            # 집계 쿼리 최적화용 복합 인덱스
            try:
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_cy_current_agg 
                    ON cy_cylinder_current(
                        dashboard_cylinder_type_key, 
                        dashboard_status, 
                        is_available
                    ) WHERE is_available = TRUE;
                """)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  인덱스 idx_cy_current_agg 생성 실패: {str(e)}"))
            
            self.stdout.write(self.style.SUCCESS("cy_cylinder_current 테이블 생성 완료!"))
            
            # 테이블 확인
            cursor.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'cy_cylinder_current';
            """)
            exists = cursor.fetchone()[0]
            
            if exists:
                self.stdout.write(self.style.SUCCESS("테이블 확인: 존재함"))
            else:
                self.stdout.write(self.style.ERROR("테이블 확인: 존재하지 않음"))

