"""CYNOW 정책 초기 데이터 입력"""
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from core.models import EndUserPolicy, ValveAlias
from core.utils.cylinder_type import generate_cylinder_type_key
import hashlib


class Command(BaseCommand):
    help = 'CYNOW 정책 초기 데이터 입력'
    
    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='기존 데이터 삭제 후 재생성')
    
    def handle(self, *args, **options):
        if options['force']:
            self.stdout.write("기존 정책 데이터 삭제 중...")
            EndUserPolicy.objects.all().delete()
            ValveAlias.objects.all().delete()
        
        # 1. 기본 EndUser 정책
        self.stdout.write("기본 EndUser 정책 입력 중...")
        default_policy, created = EndUserPolicy.objects.get_or_create(
            cylinder_type_key__isnull=True,
            defaults={
                'default_enduser_code': 'SDC',
                'default_enduser_name': 'SDC',
                'is_active': True,
                'notes': '기본 EndUser (대부분 용기)'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"  기본 EndUser 정책 생성: {default_policy.default_enduser_code}"))
        else:
            self.stdout.write(f"  기본 EndUser 정책 이미 존재: {default_policy.default_enduser_code}")
        
        # 2. CF4 YC 440L LGD 전용 예외 규칙
        self.stdout.write("\nCF4 YC 440L LGD 전용 예외 규칙 입력 중...")
        
        # 실제 데이터에서 CF4 YC 440L 용기 찾기
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT
                    COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') as gas_name,
                    c."CAPACITY",
                    COALESCE(vs."NAME", '') as valve_spec,
                    COALESCE(cs."NAME", '') as cylinder_spec,
                    COALESCE(c."USE_DEPARTMENT_CODE", '') as usage_place
                FROM "fcms_cdc"."ma_cylinders" c
                LEFT JOIN "fcms_cdc"."ma_items" i ON c."ITEM_CODE" = i."ITEM_CODE"
                LEFT JOIN "fcms_cdc"."ma_cylinder_specs" cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
                LEFT JOIN "fcms_cdc"."ma_valve_specs" vs ON c."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
                WHERE COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME", '') = 'CF4'
                AND c."CAPACITY" = 440
                LIMIT 1
            """)
            row = cursor.fetchone()
            
            if row:
                gas_name, capacity, valve_spec, cylinder_spec, usage_place = row
                # 밸브 표준화 적용 (임시로 raw 사용)
                temp_type_key = generate_cylinder_type_key(
                    gas_name or '', capacity, valve_spec or '', 
                    cylinder_spec or '', usage_place or ''
                )
                
                # LGD 예외 규칙 생성
                exception_policy, created = EndUserPolicy.objects.get_or_create(
                    cylinder_type_key=temp_type_key,
                    defaults={
                        'gas_name': gas_name,
                        'capacity': capacity,
                        'valve_spec': valve_spec,
                        'cylinder_spec': cylinder_spec,
                        'usage_place': usage_place,
                        'exception_enduser_code': 'LGD',
                        'exception_enduser_name': 'LGD',
                        'is_active': True,
                        'notes': 'CF4 YC 440L LGD 전용 29병'
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"  CF4 LGD 예외 규칙 생성: {exception_policy.cylinder_type_key}"))
                else:
                    self.stdout.write(f"  CF4 LGD 예외 규칙 이미 존재")
            else:
                self.stdout.write(self.style.WARNING("  CF4 YC 440L 용기를 찾을 수 없습니다. 수동으로 입력하세요."))
        
        # 3. 밸브 표준화 정책 (COS CGA330 NERIKI/HAMAI 통합)
        self.stdout.write("\n밸브 표준화 정책 입력 중...")
        
        valve_aliases = [
            {
                'raw_valve_spec': 'SUS general Y CGA330 Y NERIKI',
                'standard_valve_spec': 'SUS general Y CGA330',
                'valve_group_code': 'CGA330',
                'notes': 'NERIKI/HAMAI 통합'
            },
            {
                'raw_valve_spec': 'SUS general Y CGA330 Y HAMAI',
                'standard_valve_spec': 'SUS general Y CGA330',
                'valve_group_code': 'CGA330',
                'notes': 'NERIKI/HAMAI 통합'
            },
        ]
        
        for alias_data in valve_aliases:
            alias, created = ValveAlias.objects.get_or_create(
                raw_valve_spec=alias_data['raw_valve_spec'],
                defaults={
                    'standard_valve_spec': alias_data['standard_valve_spec'],
                    'valve_group_code': alias_data['valve_group_code'],
                    'is_active': True,
                    'notes': alias_data['notes']
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"  밸브 별칭 생성: {alias.raw_valve_spec} → {alias.standard_valve_spec}"))
            else:
                self.stdout.write(f"  밸브 별칭 이미 존재: {alias.raw_valve_spec}")
        
        # 4. 실제 데이터에서 밸브 스펙 확인하여 추가 정책 제안
        self.stdout.write("\n실제 데이터에서 밸브 스펙 확인 중...")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DISTINCT vs."NAME"
                FROM "fcms_cdc"."ma_valve_specs" vs
                INNER JOIN "fcms_cdc"."ma_cylinders" c ON c."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
                WHERE vs."NAME" LIKE '%CGA330%'
                ORDER BY vs."NAME"
            """)
            valve_specs = cursor.fetchall()
            
            if valve_specs:
                self.stdout.write("  발견된 CGA330 밸브 스펙:")
                for spec in valve_specs:
                    self.stdout.write(f"    - {spec[0]}")
        
        self.stdout.write(self.style.SUCCESS("\n정책 초기 데이터 입력 완료!"))
        self.stdout.write("\n다음 단계:")
        self.stdout.write("  1. Django Admin에서 정책 확인/수정: /admin/core/enduserpolicy/")
        self.stdout.write("  2. 스냅샷 테이블 초기 데이터 적재: python manage.py sync_cylinder_snapshot --full")

