from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.db import connection
from core.repositories.cylinder_repository import CylinderRepository
from core.utils.view_helper import extract_valve_type, group_cylinder_types
from core.models import HiddenCylinderType


def dashboard(request):
    """대시보드 - 모든 용기종류 한눈에"""
    # 스냅샷 테이블에서 데이터 조회
    inventory_data = CylinderRepository.get_inventory_summary()
    
    # 용기종류별 집계 (헬퍼 함수 사용)
    cylinder_types_dict = group_cylinder_types(inventory_data)
    
    # 숨김 여부 확인을 위한 파라미터
    show_hidden = request.GET.get('show_hidden', '') == '1'
    
    # 숨겨진 용기종류 키 목록 조회
    hidden_keys = set(HiddenCylinderType.objects.values_list('cylinder_type_key', flat=True))
    
    # 가스명 필터
    gas_filter = request.GET.get('gas', '').strip()
    
    # 가스명 목록 (필터용) - 모든 카드에서 추출
    gas_names = sorted(set(t['gas_name'] for t in cylinder_types_dict.values()))
    
    # 필터 적용 (가용 수량이 0이어도 표시)
    filtered_types = []
    hidden_count = 0
    for type_info in cylinder_types_dict.values():
        if gas_filter and type_info['gas_name'] != gas_filter:
            continue
        
        # 숨김 키 = cylinder_type_key 사용 (정확한 매칭 보장)
        hide_key = type_info.get('cylinder_type_key', '')
        type_info['hide_key'] = hide_key
        type_info['is_hidden'] = hide_key in hidden_keys
        
        if type_info['is_hidden']:
            hidden_count += 1
            if not show_hidden:
                continue  # 숨김 표시 모드가 아니면 건너뜀
        
        filtered_types.append(type_info)
    
    # 가스명 기준 정렬
    sorted_types = sorted(filtered_types, key=lambda x: (x['gas_name'], x.get('capacity', '') or ''))

    # 스냅샷 최신 갱신 시각 (실시간 미갱신 원인 확인용)
    last_snapshot_at = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT MAX(snapshot_updated_at) FROM cy_cylinder_current")
            row = cursor.fetchone()
            last_snapshot_at = row[0] if row else None
    except Exception:
        last_snapshot_at = None
    
    context = {
        'cylinder_types': sorted_types,
        'gas_names': gas_names,
        'selected_gas': gas_filter,
        'show_hidden': show_hidden,
        'hidden_count': hidden_count,
        'last_snapshot_at': last_snapshot_at,
    }
    return render(request, 'dashboard/dashboard.html', context)


@login_required
@require_POST
def toggle_hide_cylinder_type(request):
    """용기종류 숨김/표시 토글 API"""
    import json
    
    try:
        data = json.loads(request.body)
        hide_key = data.get('hide_key', '')  # cylinder_type_key (MD5 해시)
        gas_name = data.get('gas_name', '')  # 클라이언트에서 함께 전송
        action = data.get('action', 'hide')  # 'hide' or 'show'
        
        if not hide_key:
            return JsonResponse({'success': False, 'error': '키가 없습니다.'}, status=400)
        
        if action == 'hide':
            # 숨김 추가
            obj, created = HiddenCylinderType.objects.get_or_create(
                cylinder_type_key=hide_key,
                defaults={
                    'gas_name': gas_name,
                    'hidden_by': request.user,
                }
            )
            return JsonResponse({
                'success': True,
                'action': 'hidden',
                'message': f'{gas_name} 카드가 숨겨졌습니다.' if gas_name else '카드가 숨겨졌습니다.'
            })
        else:
            # 숨김 해제
            deleted_count, _ = HiddenCylinderType.objects.filter(cylinder_type_key=hide_key).delete()
            return JsonResponse({
                'success': True,
                'action': 'shown',
                'message': f'{gas_name} 카드가 다시 표시됩니다.' if gas_name else '카드가 다시 표시됩니다.'
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '잘못된 요청입니다.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def detail(request):
    """현황 - 선택 용기종류의 상세 데이터"""
    selected_type = request.GET.get('type', '')
    
    # 모든 용기종류 목록 (드롭다운용) - 대시보드와 동일한 그룹화 로직
    all_inventory = CylinderRepository.get_inventory_summary()
    cylinder_types_dict = group_cylinder_types(all_inventory)
    
    # cylinder_type_key를 키로 하는 딕셔너리 생성 (가용 수량이 0이어도 포함)
    cylinder_type_options = {}
    for type_info in cylinder_types_dict.values():
        key = type_info.get('cylinder_type_key', '')
        if key:
            cylinder_type_options[key] = {
                'gas_name': type_info['gas_name'],
                'capacity': type_info['capacity'],
                'valve_type': type_info['valve_type'],
                'cylinder_spec': type_info['cylinder_spec'],
                'enduser': type_info.get('usage_place', ''),  # usage_place에 enduser가 저장됨
            }
    
    cylinder_type_list = sorted(cylinder_type_options.items(), key=lambda x: (x[1]['gas_name'], x[1]['capacity'] or ''))
    
    # 선택된 용기종류 정보 가져오기
    selected_info = None
    if selected_type and selected_type in cylinder_type_options:
        selected_info = cylinder_type_options[selected_type]
    
    # 스냅샷 테이블에서 전체 데이터 조회 후 Python에서 필터링
    inventory_data = []
    if selected_info:
        all_data = CylinderRepository.get_inventory_summary({'cylinder_type_key': selected_type})
        inventory_data = all_data
    
    # 용기종류별 집계
    type_info = None
    status_summary = {}
    location_summary = {}
    cylinders_by_status = {}  # 상태별 용기 리스트
    
    if selected_info:
        type_info = {
            'gas_name': selected_info['gas_name'],
            'capacity': selected_info['capacity'],
            'valve_type': selected_info['valve_type'],
            'cylinder_spec': selected_info['cylinder_spec'],
            'enduser': selected_info.get('enduser', ''),
        }
        
        for row in inventory_data:
            status = row.get('status', '')
            qty = row.get('qty', 0)
            
            status_summary[status] = status_summary.get(status, 0) + qty
        
        # 위치별 집계는 용기 리스트에서 가져오기
        all_cylinders = CylinderRepository.get_cylinder_list({'cylinder_type_key': selected_type})
        for cyl in all_cylinders:
            location = cyl.get('location', '')
            if location:
                location_summary[location] = location_summary.get(location, 0) + 1
        
        # 용기 리스트 조회 (상태별 그룹화)
        # cylinder_type_key로 필터링
        all_cylinders = CylinderRepository.get_cylinder_list({'cylinder_type_key': selected_type})
        for cyl in all_cylinders:
            status = cyl.get('status', '')
            if status not in cylinders_by_status:
                cylinders_by_status[status] = []
            cylinders_by_status[status].append(cyl)
    
    # 최근 추이 (History가 있을 경우)
    from history.models import HistInventorySnapshot
    from django.utils import timezone
    from datetime import timedelta
    
    trend_data = []
    if selected_type:
        # 최근 7일간의 스냅샷 데이터
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=7)
        
        snapshots = HistInventorySnapshot.objects.filter(
            cylinder_type_key=selected_type,
            snapshot_datetime__date__gte=start_date,
            snapshot_datetime__date__lte=end_date,
            snapshot_type='DAILY'
        ).order_by('snapshot_datetime')
        
        # 일별 집계
        daily_trend = {}
        for snapshot in snapshots:
            date_key = snapshot.snapshot_datetime.date()
            if date_key not in daily_trend:
                daily_trend[date_key] = {}
            status = snapshot.status
            daily_trend[date_key][status] = daily_trend[date_key].get(status, 0) + snapshot.qty
        
        trend_data = sorted(daily_trend.items())
    
    context = {
        'type_info': type_info,
        'status_summary': status_summary,
        'location_summary': location_summary,
        'inventory_data': inventory_data,
        'trend_data': trend_data,
        'cylinder_type_list': cylinder_type_list,
        'selected_type': selected_type,
        'cylinders_by_status': cylinders_by_status,
    }
    return render(request, 'dashboard/detail.html', context)

def summary(request):
    """요약 - 용기종류별 그래프/표/통계"""
    # 기간 파라미터
    days_param = request.GET.get('days', '30')
    if days_param == 'custom':
        custom_days = request.GET.get('custom_days', '30')
        try:
            days = int(custom_days)
        except:
            days = 30
    else:
        try:
            days = int(days_param)
        except:
            days = 30
    
    inventory_data = CylinderRepository.get_inventory_summary()
    
    # 전체 통계
    total_qty = sum(row.get('qty', 0) for row in inventory_data)
    
    # 상태별 집계
    status_stats = {}
    for row in inventory_data:
        status = row.get('status', '')
        qty = row.get('qty', 0)
        status_stats[status] = status_stats.get(status, 0) + qty
    
    # 가스명별 집계
    gas_stats = {}
    for row in inventory_data:
        gas_name = row.get('gas_name', '')
        qty = row.get('qty', 0)
        gas_stats[gas_name] = gas_stats.get(gas_name, 0) + qty
    
    # Top 10 가스명
    top_gases = sorted(gas_stats.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # 변동 랭킹 (History 기반)
    from history.models import HistInventorySnapshot
    from django.utils import timezone
    from datetime import timedelta
    
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)
    
    # 기간 첫날과 마지막날 스냅샷 비교
    first_snapshots = HistInventorySnapshot.objects.filter(
        snapshot_datetime__date=start_date,
        snapshot_type='DAILY'
    )
    
    last_snapshots = HistInventorySnapshot.objects.filter(
        snapshot_datetime__date=end_date,
        snapshot_type='DAILY'
    )
    
    # 변동량 계산 - 가스명별 집계
    first_summary = {}
    last_summary = {}
    
    for snapshot in first_snapshots:
        key = snapshot.gas_name
        first_summary[key] = first_summary.get(key, 0) + snapshot.qty
    
    for snapshot in last_snapshots:
        key = snapshot.gas_name
        last_summary[key] = last_summary.get(key, 0) + snapshot.qty
    
    # 변동량 계산
    top_changes = []
    all_gas_names = set(first_summary.keys()) | set(last_summary.keys())
    for gas_name in all_gas_names:
        first_qty = first_summary.get(gas_name, 0)
        last_qty = last_summary.get(gas_name, 0)
        delta = last_qty - first_qty
        if delta != 0:  # 변동이 있는 것만
            top_changes.append({
                'gas_name': gas_name,
                'first_qty': first_qty,
                'last_qty': last_qty,
                'delta': delta,
            })
    
    # 변동량 절대값 기준 정렬
    top_changes.sort(key=lambda x: abs(x['delta']), reverse=True)
    top_changes = top_changes[:10]  # Top 10
    
    context = {
        'days': days,
        'total_qty': total_qty,
        'status_stats': status_stats,
        'gas_stats': gas_stats,
        'top_gases': top_gases,
        'top_changes': top_changes,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'dashboard/summary.html', context)
