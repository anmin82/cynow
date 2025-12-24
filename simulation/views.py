"""
용기 사이클 시뮬레이션 뷰
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.db import connection
import json

from .services import SimulationService
from core.repositories.cylinder_repository import CylinderRepository
from dashboard.views import extract_valve_type


def get_cylinder_type_list():
    """용기종류 목록 조회 (대시보드와 동일한 그룹화)"""
    all_inventory = CylinderRepository.get_inventory_summary()
    cylinder_type_options = {}
    
    for row in all_inventory:
        cylinder_type_key = row.get('cylinder_type_key', '')
        if not cylinder_type_key:
            continue
            
        gas_name = row.get('gas_name', '')
        capacity = row.get('capacity') or ''
        valve_spec = row.get('valve_spec', '')
        valve_type = extract_valve_type(valve_spec)
        cylinder_spec = row.get('cylinder_spec', '')
        usage_place = row.get('usage_place') or ''
        
        if cylinder_type_key not in cylinder_type_options:
            cylinder_type_options[cylinder_type_key] = {
                'cylinder_type_key': cylinder_type_key,
                'gas_name': gas_name,
                'capacity': capacity,
                'valve_type': valve_type,
                'cylinder_spec': cylinder_spec,
                'usage_place': usage_place,
                'display_name': f"{gas_name} / {capacity}L / {valve_type}" if capacity else f"{gas_name} / {valve_type}",
            }
    
    return sorted(cylinder_type_options.values(), key=lambda x: (x['gas_name'], x['capacity'] or ''))


def simulation_view(request):
    """시뮬레이션 메인 페이지"""
    cylinder_types = get_cylinder_type_list()
    
    context = {
        'cylinder_types': cylinder_types,
    }
    return render(request, 'simulation/index.html', context)


@require_GET
def get_cylinder_types(request):
    """용기종류 목록 API"""
    cylinder_types = get_cylinder_type_list()
    return JsonResponse({'cylinder_types': cylinder_types})


@require_POST
def calculate_simulation(request):
    """시뮬레이션 계산 API"""
    try:
        data = json.loads(request.body)
        
        cylinder_type_key = data.get('cylinder_type_key', '')
        if not cylinder_type_key:
            return JsonResponse({'success': False, 'error': '용기종류를 선택해주세요.'})
        
        # 파라미터 추출
        recovery_method = data.get('recovery_method', 'fixed_rate')
        recovery_rate = float(data.get('recovery_rate', 80)) / 100  # % → 소수
        recovery_lead_months = int(data.get('recovery_lead_months', 2))
        manual_recovery = data.get('manual_recovery', None)
        purchase_multiplier = float(data.get('purchase_multiplier', 1.0))
        repair_multiplier = float(data.get('repair_multiplier', 1.0))
        
        # 시뮬레이션 실행
        result = SimulationService.simulate(
            cylinder_type_key=cylinder_type_key,
            months=12,
            recovery_method=recovery_method,
            recovery_rate=recovery_rate,
            recovery_lead_months=recovery_lead_months,
            manual_recovery=manual_recovery,
            purchase_multiplier=purchase_multiplier,
            repair_multiplier=repair_multiplier,
        )
        
        return JsonResponse({'success': True, 'data': result})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})
