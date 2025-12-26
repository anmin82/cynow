"""특정 용기의 데이터를 상세히 확인"""
from django.core.management.base import BaseCommand
from core.repositories.cylinder_repository import CylinderRepository
from django.db import connection
import json


class Command(BaseCommand):
    help = '특정 용기의 데이터 상세 확인'

    def add_arguments(self, parser):
        parser.add_argument(
            'cylinder_no',
            type=str,
            help='확인할 용기 번호'
        )

    def handle(self, *args, **options):
        cylinder_no = options['cylinder_no'].strip()
        
        self.stdout.write('=' * 80)
        self.stdout.write(f'용기번호: {cylinder_no}')
        self.stdout.write('=' * 80)
        
        # Repository를 통한 조회
        self.stdout.write('\n[1] Repository를 통한 조회:')
        filters = {'cylinder_no': cylinder_no}
        cylinders = CylinderRepository.get_cylinder_list(filters=filters, limit=1)
        
        if not cylinders:
            self.stdout.write(self.style.ERROR('용기를 찾을 수 없습니다.'))
            return
        
        cylinder = cylinders[0]
        
        # 모든 필드 출력
        self.stdout.write('\n주요 필드:')
        self.stdout.write(f'  - cylinder_no: "{cylinder.get("cylinder_no")}"')
        self.stdout.write(f'  - gas_name: "{cylinder.get("gas_name")}"')
        self.stdout.write(f'  - capacity: {cylinder.get("capacity")}')
        self.stdout.write(f'  - valve_spec: "{cylinder.get("valve_spec")}"')
        self.stdout.write(f'  - cylinder_spec: "{cylinder.get("cylinder_spec")}"')
        self.stdout.write(f'  - usage_place: "{cylinder.get("usage_place")}"')
        self.stdout.write(f'  - status: "{cylinder.get("status")}"')
        self.stdout.write(f'  - location: "{cylinder.get("location")}"')
        
        # valve_spec이 비어있는지 확인
        valve_spec = cylinder.get("valve_spec")
        if valve_spec is None:
            self.stdout.write(self.style.WARNING('\n⚠️  valve_spec이 NULL입니다!'))
        elif valve_spec == '':
            self.stdout.write(self.style.WARNING('\n⚠️  valve_spec이 빈 문자열입니다!'))
        elif valve_spec.strip() == '':
            self.stdout.write(self.style.WARNING(f'\n⚠️  valve_spec이 공백만 있습니다! (길이: {len(valve_spec)})'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✓ valve_spec 값 있음: "{valve_spec}"'))
        
        # VIEW에서 직접 조회
        self.stdout.write('\n\n[2] VIEW에서 직접 조회:')
        with connection.cursor() as cursor:
            # 용기번호로 검색 (공백 trim 포함)
            cursor.execute("""
                SELECT 
                    cylinder_no,
                    gas_name,
                    capacity,
                    valve_spec,
                    cylinder_spec,
                    usage_place,
                    status,
                    location
                FROM vw_cynow_cylinder_list
                WHERE TRIM(cylinder_no) = %s
                LIMIT 1
            """, [cylinder_no.strip()])
            
            row = cursor.fetchone()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                self.stdout.write('\n원본 VIEW 데이터:')
                for col, val in zip(columns, row):
                    if val is None:
                        display_val = "NULL"
                    elif isinstance(val, str):
                        if val == '':
                            display_val = '(빈 문자열)'
                        elif val.strip() == '':
                            display_val = f'(공백만 {len(val)}자)'
                        else:
                            display_val = f'"{val}"'
                    else:
                        display_val = str(val)
                    
                    self.stdout.write(f'  - {col}: {display_val}')
                
                # valve_spec 특별 체크
                valve_spec_raw = row[3]  # valve_spec은 4번째 컬럼
                if valve_spec_raw is None:
                    self.stdout.write(self.style.ERROR('\n⚠️  VIEW의 valve_spec이 NULL입니다!'))
                elif valve_spec_raw == '':
                    self.stdout.write(self.style.ERROR('\n⚠️  VIEW의 valve_spec이 빈 문자열입니다!'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'\n✓ VIEW의 valve_spec: "{valve_spec_raw}"'))
            else:
                self.stdout.write(self.style.ERROR('VIEW에서 용기를 찾을 수 없습니다.'))
        
        # fcms_cdc 스키마의 원본 테이블 조회 (PostgreSQL인 경우)
        if connection.vendor == 'postgresql':
            self.stdout.write('\n\n[3] CDC 원본 테이블 조회:')
            try:
                with connection.cursor() as cursor:
                    # CF4_YC 테이블에서 조회
                    cursor.execute("""
                        SELECT 
                            "CYLINDER_NO",
                            "GAS_NAME",
                            "VALVE_SPEC_NAME",
                            "CYLINDER_SPEC_NAME",
                            "CONDITION_CODE",
                            "POSITION_USER_NAME"
                        FROM fcms_cdc."CF4_YC"
                        WHERE TRIM("CYLINDER_NO") = %s
                        LIMIT 1
                    """, [cylinder_no.strip()])
                    
                    row = cursor.fetchone()
                    
                    if row:
                        self.stdout.write('\nCDC 원본 데이터:')
                        self.stdout.write(f'  - CYLINDER_NO: "{row[0]}"')
                        self.stdout.write(f'  - GAS_NAME: "{row[1]}"')
                        self.stdout.write(f'  - VALVE_SPEC_NAME: "{row[2]}" {"⚠️ NULL" if row[2] is None else ""}')
                        self.stdout.write(f'  - CYLINDER_SPEC_NAME: "{row[3]}"')
                        self.stdout.write(f'  - CONDITION_CODE: "{row[4]}"')
                        self.stdout.write(f'  - POSITION_USER_NAME: "{row[5]}"')
                        
                        if row[2] is None or row[2] == '':
                            self.stdout.write(self.style.ERROR('\n⚠️  원본 FCMS 데이터에 VALVE_SPEC_NAME이 없습니다!'))
                            self.stdout.write('\n해결 방법:')
                            self.stdout.write('  1. FCMS에서 해당 용기의 밸브 스펙을 입력하세요.')
                            self.stdout.write('  2. Debezium이 변경사항을 감지하여 동기화합니다.')
                    else:
                        self.stdout.write(self.style.ERROR('CDC 테이블에서 용기를 찾을 수 없습니다.'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'CDC 테이블 조회 실패: {e}'))
        
        self.stdout.write('\n' + '=' * 80)

















