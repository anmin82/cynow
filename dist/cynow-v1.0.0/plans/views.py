from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import PlanForecastMonthly, PlanScheduledMonthly
from core.repositories.cylinder_repository import CylinderRepository
from dashboard.views import extract_valve_type
from datetime import date
from dateutil.relativedelta import relativedelta
import json


def get_cylinder_type_list():
    """용기종류 목록 조회 (대시보드와 동일한 그룹화)"""
    all_inventory = CylinderRepository.get_inventory_summary()
    cylinder_type_options = {}
    
    for row in all_inventory:
        gas_name = row.get('gas_name', '')
        capacity = row.get('capacity') or ''
        valve_spec = row.get('valve_spec', '')
        valve_type = extract_valve_type(valve_spec)
        cylinder_spec = row.get('cylinder_spec', '')
        usage_place = row.get('usage_place') or ''
        
        group_key = f"{gas_name}|{capacity}|{valve_type}|{cylinder_spec}|{usage_place}"
        
        if group_key not in cylinder_type_options:
            cylinder_type_options[group_key] = {
                'gas_name': gas_name,
                'capacity': capacity,
                'valve_type': valve_type,
                'cylinder_spec': cylinder_spec,
                'usage_place': usage_place,
            }
    
    return sorted(cylinder_type_options.items(), key=lambda x: (x[1]['gas_name'], x[1]['capacity'] or ''))


def get_months_list(count=6):
    """향후 N개월 목록 생성"""
    today = date.today()
    months = []
    for i in range(count):
        month_date = today + relativedelta(months=i)
        month_start = date(month_date.year, month_date.month, 1)
        months.append(month_start)
    return months


@login_required
@permission_required('cynow.can_edit_plan', raise_exception=True)
def forecast(request):
    """출하 계획 - 매트릭스 입력"""
    cylinder_types = get_cylinder_type_list()
    months = get_months_list(6)
    
    # 기존 계획 데이터 조회
    existing_plans = {}
    for plan in PlanForecastMonthly.objects.all():
        key = f"{plan.gas_name}|{plan.capacity or ''}|{plan.valve_spec or ''}|{plan.cylinder_spec or ''}|{plan.usage_place or ''}"
        month_key = plan.month.strftime('%Y-%m')
        if key not in existing_plans:
            existing_plans[key] = {}
        existing_plans[key][month_key] = plan.planned_ship_qty
    
    # 매트릭스 데이터 생성
    matrix_data = []
    for type_key, type_info in cylinder_types:
        row = {
            'key': type_key,
            'info': type_info,
            'months': {}
        }
        for month in months:
            month_key = month.strftime('%Y-%m')
            row['months'][month_key] = existing_plans.get(type_key, {}).get(month_key, '')
        matrix_data.append(row)
    
    context = {
        'matrix_data': matrix_data,
        'months': months,
    }
    return render(request, 'plans/forecast.html', context)


@login_required
@permission_required('cynow.can_edit_plan', raise_exception=True)
@require_POST
def forecast_save(request):
    """출하 계획 저장 (AJAX)"""
    try:
        data = json.loads(request.body)
        type_key = data.get('type_key', '')
        month_str = data.get('month', '')
        qty = data.get('qty', '')
        
        # type_key 파싱
        parts = type_key.split('|')
        if len(parts) != 5:
            return JsonResponse({'success': False, 'error': 'Invalid type_key'})
        
        gas_name, capacity, valve_type, cylinder_spec, usage_place = parts
        month_date = date.fromisoformat(month_str + '-01')
        
        if qty == '' or qty is None:
            # 삭제
            PlanForecastMonthly.objects.filter(
                gas_name=gas_name,
                capacity=capacity or None,
                valve_spec=valve_type or None,
                cylinder_spec=cylinder_spec or None,
                usage_place=usage_place or None,
                month=month_date
            ).delete()
        else:
            qty_int = int(qty)
            obj, created = PlanForecastMonthly.objects.update_or_create(
                gas_name=gas_name,
                capacity=capacity or None,
                valve_spec=valve_type or None,
                cylinder_spec=cylinder_spec or None,
                usage_place=usage_place or None,
                month=month_date,
                defaults={
                    'planned_ship_qty': qty_int,
                    'created_by': request.user,
                }
            )
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permission_required('cynow.can_edit_plan', raise_exception=True)
def scheduled(request):
    """투입 계획 - 매트릭스 입력"""
    cylinder_types = get_cylinder_type_list()
    months = get_months_list(6)
    
    # 기존 계획 데이터 조회
    existing_plans = {}
    for plan in PlanScheduledMonthly.objects.all():
        key = f"{plan.gas_name}|{plan.capacity or ''}|{plan.valve_spec or ''}|{plan.cylinder_spec or ''}|{plan.usage_place or ''}"
        month_key = plan.month.strftime('%Y-%m')
        if key not in existing_plans:
            existing_plans[key] = {}
        existing_plans[key][month_key] = {
            'add_purchase_qty': plan.add_purchase_qty or '',
            'add_refurb_qty': plan.add_refurb_qty or '',
            'recover_from_defect_qty': plan.recover_from_defect_qty or '',
            'convert_gas_qty': plan.convert_gas_qty or '',
        }
    
    # 매트릭스 데이터 생성
    matrix_data = []
    for type_key, type_info in cylinder_types:
        row = {
            'key': type_key,
            'info': type_info,
            'months': {}
        }
        for month in months:
            month_key = month.strftime('%Y-%m')
            row['months'][month_key] = existing_plans.get(type_key, {}).get(month_key, {})
        matrix_data.append(row)
    
    context = {
        'matrix_data': matrix_data,
        'months': months,
    }
    return render(request, 'plans/scheduled.html', context)


@login_required
@permission_required('cynow.can_edit_plan', raise_exception=True)
@require_POST
def scheduled_save(request):
    """투입 계획 저장 (AJAX)"""
    try:
        data = json.loads(request.body)
        type_key = data.get('type_key', '')
        month_str = data.get('month', '')
        field = data.get('field', '')
        qty = data.get('qty', '')
        
        # type_key 파싱
        parts = type_key.split('|')
        if len(parts) != 5:
            return JsonResponse({'success': False, 'error': 'Invalid type_key'})
        
        gas_name, capacity, valve_type, cylinder_spec, usage_place = parts
        month_date = date.fromisoformat(month_str + '-01')
        
        # 기존 레코드 조회 또는 생성
        obj, created = PlanScheduledMonthly.objects.get_or_create(
            gas_name=gas_name,
            capacity=capacity or None,
            valve_spec=valve_type or None,
            cylinder_spec=cylinder_spec or None,
            usage_place=usage_place or None,
            month=month_date,
            defaults={'created_by': request.user}
        )
        
        # 필드 업데이트
        qty_val = int(qty) if qty not in ['', None] else None
        if field == 'add_purchase_qty':
            obj.add_purchase_qty = qty_val
        elif field == 'add_refurb_qty':
            obj.add_refurb_qty = qty_val
        elif field == 'recover_from_defect_qty':
            obj.recover_from_defect_qty = qty_val
        elif field == 'convert_gas_qty':
            obj.convert_gas_qty = qty_val
        
        obj.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
