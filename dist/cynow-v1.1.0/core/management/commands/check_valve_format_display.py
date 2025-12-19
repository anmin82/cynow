"""대시보드에서 밸브 형식 표시 확인"""
from django.core.management.base import BaseCommand
from django.db import connection
from core.repositories.cylinder_repository import CylinderRepository
from core.utils.view_helper import group_cylinder_types, extract_valve_type, parse_valve_spec


class Command(BaseCommand):
    help = '대시보드에서 밸브 형식 표시 확인'

    def handle(self, *args, **options):
        # 대시보드 데이터 조회
        inventory_data = CylinderRepository.get_inventory_summary()
        cylinder_types_dict = group_cylinder_types(inventory_data)
        
        # 밸브 형식이 전체 밸브 스펙명으로 표시되는 카드 찾기
        self.stdout.write("=== 밸브 형식이 전체 스펙명으로 표시되는 카드 ===\n")
        found_issues = False
        
        for type_key, type_info in cylinder_types_dict.items():
            valve_format = type_info.get('valve_format', '')
            valve_spec = type_info.get('valve_spec', '')
            
            # 밸브 형식이 전체 스펙명과 같거나, CGA/DISS/DIN 패턴이 아닌 경우
            if valve_format and valve_format == valve_spec:
                found_issues = True
                self.stdout.write(f"\n  카드: {type_info['gas_name']} {type_info['capacity']}L\n")
                self.stdout.write(f"    valve_spec: '{valve_spec}'\n")
                self.stdout.write(f"    valve_format: '{valve_format}'\n")
                self.stdout.write(f"    valve_material: '{type_info.get('valve_material', '')}'\n")
                
                # extract_valve_type 결과 확인
                extracted = extract_valve_type(valve_spec)
                self.stdout.write(f"    extract_valve_type 결과: '{extracted}'\n")
                
                # parse_valve_spec 결과 확인
                parsed = parse_valve_spec(valve_spec)
                self.stdout.write(f"    parse_valve_spec 결과: format='{parsed['format']}', material='{parsed['material']}'\n")
        
        if not found_issues:
            self.stdout.write("  [없음] 모든 카드의 밸브 형식이 올바르게 표시됩니다.\n")
        
        # 샘플 데이터 확인
        self.stdout.write("\n=== 샘플 카드 데이터 (처음 5개) ===\n")
        count = 0
        for type_key, type_info in list(cylinder_types_dict.items())[:5]:
            count += 1
            self.stdout.write(f"\n  카드 {count}: {type_info['gas_name']} {type_info['capacity']}L\n")
            self.stdout.write(f"    valve_spec: '{type_info.get('valve_spec', '')}'\n")
            self.stdout.write(f"    valve_format: '{type_info.get('valve_format', '')}'\n")
            self.stdout.write(f"    valve_material: '{type_info.get('valve_material', '')}'\n")

