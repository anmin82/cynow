"""밸브 그룹 설정"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = '밸브 그룹 설정 (COS CGA330 NERIKI/HAMAI 통합)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 저장하지 않고 미리보기만'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN 모드: 실제 저장하지 않습니다."))
        
        with connection.cursor() as cursor:
            # 실제 밸브 스펙 코드 확인
            cursor.execute("""
                SELECT DISTINCT 
                    vs."VALVE_SPEC_CODE",
                    vs."NAME"
                FROM "fcms_cdc"."ma_valve_specs" vs
                WHERE vs."NAME" LIKE '%CGA330%'
                  AND (vs."NAME" LIKE '%NERIKI%' OR vs."NAME" LIKE '%HAMAI%')
                ORDER BY vs."NAME"
            """)
            valve_specs = cursor.fetchall()
            
            if not valve_specs:
                self.stdout.write(self.style.WARNING("CGA330 NERIKI/HAMAI 밸브를 찾을 수 없습니다."))
                return
            
            self.stdout.write(f"발견된 밸브: {len(valve_specs)}개")
            for code, name in valve_specs:
                self.stdout.write(f"  - {code}: {name}")
            
            if dry_run:
                self.stdout.write("\n다음 그룹이 생성됩니다:")
                self.stdout.write("  - 그룹명: COS_CGA330")
                self.stdout.write("  - Primary: NERIKI (첫 번째)")
                self.stdout.write("  - Member: HAMAI")
                return
            
            # 그룹 생성
            cursor.execute("""
                INSERT INTO cy_valve_group (group_name, description, is_active)
                VALUES ('COS_CGA330', 'COS CGA330 통합 그룹 (NERIKI/HAMAI)', TRUE)
                ON CONFLICT (group_name) 
                DO UPDATE SET 
                    description = EXCLUDED.description,
                    is_active = TRUE,
                    updated_at = NOW()
                RETURNING id
            """)
            group_id = cursor.fetchone()[0]
            self.stdout.write(self.style.SUCCESS(f"밸브 그룹 생성 완료 (ID: {group_id})"))
            
            # 밸브 매핑
            for i, (code, name) in enumerate(valve_specs):
                is_primary = (i == 0)  # 첫 번째를 primary로
                cursor.execute("""
                    INSERT INTO cy_valve_group_mapping 
                    (valve_spec_code, valve_spec_name, group_id, is_primary, is_active)
                    VALUES (%s, %s, %s, %s, TRUE)
                    ON CONFLICT (valve_spec_code, valve_spec_name) 
                    DO UPDATE SET 
                        group_id = EXCLUDED.group_id,
                        is_primary = EXCLUDED.is_primary,
                        is_active = TRUE,
                        updated_at = NOW()
                """, [code, name, group_id, is_primary])
                
                primary_text = " (Primary)" if is_primary else ""
                self.stdout.write(f"  - {name}{primary_text}")
            
            self.stdout.write(self.style.SUCCESS("밸브 그룹 매핑 완료"))










