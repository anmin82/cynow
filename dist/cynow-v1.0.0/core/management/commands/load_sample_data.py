"""V_CYLCY_CDC_MIN 파일 파싱 및 샘플 데이터 적재"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
import os
from pathlib import Path


class Command(BaseCommand):
    help = 'V_CYLCY_CDC_MIN 파일을 파싱하여 샘플 데이터 적재'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='V_CYLCY_CDC_MIN_202512141804.md',
            help='로드할 마크다운 파일 경로'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='로드할 최대 행 수 (테스트용)'
        )

    def _get_capacity_and_usage(self, gas_name, cylinder_no):
        """
        가스명과 용기번호에 따라 용량과 사용처 결정
        - COS: 용량 47L, 사용처 SEC
        - CLF3: 용기번호가 SUS로 시작하면 용량 40L, 사용처 SEC
        """
        capacity = None
        usage_place = None
        
        gas_name_upper = (gas_name or '').upper().strip()
        cylinder_no_upper = (cylinder_no or '').upper().strip()
        
        if gas_name_upper == 'COS':
            capacity = '47L'
            usage_place = 'SEC'
        elif gas_name_upper == 'CLF3':
            if cylinder_no_upper.startswith('SUS'):
                capacity = '40L'
                usage_place = 'SEC'
        
        return capacity, usage_place

    def handle(self, *args, **options):
        file_path = options['file']
        limit = options['limit']
        
        # 파일 경로 확인
        if not os.path.isabs(file_path):
            file_path = Path(settings.BASE_DIR) / file_path
        
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f'File not found: {file_path}'))
            return
        
        self.stdout.write(f'Loading data from: {file_path}')
        
        # 먼저 모의 VIEW 생성
        from django.core.management import call_command
        call_command('create_mock_views')
        
        # 파일 파싱
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 헤더 찾기 (첫 번째 줄)
        if len(lines) < 2:
            self.stdout.write(self.style.ERROR('Invalid file format'))
            return
        
        # 헤더 파싱
        header_line = lines[0].strip()
        if not header_line.startswith('|'):
            self.stdout.write(self.style.ERROR('Invalid header format'))
            return
        
        headers = [col.strip() for col in header_line.split('|')[1:-1]]
        
        # 구분선 건너뛰기 (두 번째 줄)
        data_lines = lines[2:]
        
        if limit:
            data_lines = data_lines[:limit]
        
        # 데이터 삽입
        import sqlite3
        db_path = connection.settings_dict['NAME']
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        inserted = 0
        skipped = 0
        
        for line_num, line in enumerate(data_lines, start=3):
            line = line.strip()
            if not line or not line.startswith('|'):
                continue
            
            values = [col.strip() for col in line.split('|')[1:-1]]
            
            if len(values) != len(headers):
                skipped += 1
                continue
            
            # 데이터 매핑
            data_dict = dict(zip(headers, values))
            
            # 빈 값 처리
            cylinder_no = data_dict.get('CYLINDER_NO', '').strip()
            if not cylinder_no:
                skipped += 1
                continue
            
            gas_name = data_dict.get('GAS_NAME', '').strip()
            
            # 용량과 사용처 결정
            capacity, usage_place = self._get_capacity_and_usage(gas_name, cylinder_no)
            
            # SQL 삽입
            try:
                def clean_value(v):
                    v = v.strip() if v else ''
                    return v if v else None
                
                params = [
                    cylinder_no,
                    clean_value(data_dict.get('CYLINDER_NO_RAW', '')),
                    clean_value(data_dict.get('POSITION_USER_NAME', '')),
                    clean_value(data_dict.get('CONDITION_CODE', '')),
                    clean_value(data_dict.get('CONDITION_NAME', '')),
                    int(data_dict.get('SHIPPING_COUNT', '0') or '0'),
                    clean_value(data_dict.get('ITEM_CODE', '')),
                    gas_name or None,
                    capacity,  # 계산된 용량
                    usage_place,  # 계산된 사용처
                    clean_value(data_dict.get('CYLINDER_SPEC_CODE', '')),
                    clean_value(data_dict.get('CYLINDER_SPEC_NAME', '')),
                    clean_value(data_dict.get('VALVE_SPEC_CODE', '')),
                    clean_value(data_dict.get('VALVE_SPEC_NAME', '')),
                    self._parse_datetime(data_dict.get('MANUFACTURE_DATE', '')),
                    self._parse_datetime(data_dict.get('LAST_PRESSURE_TEST_DATE', '')),
                    self._parse_datetime(data_dict.get('NEXT_PRESSURE_TEST_DUE_DATE', '')),
                ]
                
                sql = """INSERT INTO fcms_cylinders (
                    CYLINDER_NO, CYLINDER_NO_RAW, POSITION_USER_NAME,
                    CONDITION_CODE, CONDITION_NAME, SHIPPING_COUNT,
                    ITEM_CODE, GAS_NAME, CAPACITY, USAGE_PLACE,
                    CYLINDER_SPEC_CODE, CYLINDER_SPEC_NAME,
                    VALVE_SPEC_CODE, VALVE_SPEC_NAME,
                    MANUFACTURE_DATE, LAST_PRESSURE_TEST_DATE, NEXT_PRESSURE_TEST_DUE_DATE
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
                
                cursor.execute(sql, tuple(params))
                inserted += 1
                
                if inserted % 500 == 0:
                    self.stdout.write(f'Inserted {inserted} records...')
                    
            except Exception as e:
                if line_num <= 5:
                    self.stdout.write(self.style.WARNING(f'Line {line_num}: Error - {str(e)}'))
                skipped += 1
                continue
        
        conn.commit()
        conn.close()
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully loaded {inserted} records. Skipped: {skipped}'
        ))
    
    def _parse_datetime(self, value):
        """날짜 문자열 파싱"""
        if not value or value.strip() == '':
            return None
        
        value = value.strip()
        if '.' in value:
            value = value.split('.')[0]
        
        return value
