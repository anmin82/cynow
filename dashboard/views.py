from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.db import connection
from core.repositories.cylinder_repository import CylinderRepository
from core.utils.view_helper import extract_valve_type, group_cylinder_types
from core.models import HiddenCylinderType
from collections import defaultdict


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

    # 스냅샷/CDC 최신 시각 (실시간 미갱신 원인 확인용)
    last_snapshot_at = None
    cdc_last_move_at = None
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT MAX(snapshot_updated_at) FROM cy_cylinder_current")
            row = cursor.fetchone()
            last_snapshot_at = row[0] if row else None

            # CDC 테이블 최신 MOVE_DATE (원천 데이터 유입 확인용)
            cursor.execute('SELECT MAX("MOVE_DATE") FROM fcms_cdc.tr_latest_cylinder_statuses')
            row2 = cursor.fetchone()
            cdc_last_move_at = row2[0] if row2 else None
    except Exception:
        last_snapshot_at = None
        cdc_last_move_at = None
    
    context = {
        'cylinder_types': sorted_types,
        'gas_names': gas_names,
        'selected_gas': gas_filter,
        'show_hidden': show_hidden,
        'hidden_count': hidden_count,
        'last_snapshot_at': last_snapshot_at,
        'cdc_last_move_at': cdc_last_move_at,
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


@require_GET
def api_move_report_cylinders(request):
    """
    특정 상태의 용기들을 이동서별로 그룹화하여 반환하는 API
    - 보관: 이동서 없이 용기 리스트만 반환
    - 충전중~제품: 이동서 정보 + 예정일/확정일 + 용기 리스트
    """
    cylinder_type_keys = request.GET.get('cylinder_type_keys', '')
    status = request.GET.get('status', '')
    
    if not cylinder_type_keys or not status:
        return JsonResponse({'ok': False, 'error': '필수 파라미터 누락'}, status=400)
    
    keys_list = [k.strip() for k in cylinder_type_keys.split(',') if k.strip()]
    
    # 지원하는 상태 목록
    supported_statuses = ['충전중', '충전완료', '분석중', '분석완료', '제품']
    if status not in supported_statuses:
        return JsonResponse({'ok': False, 'error': f'지원하지 않는 상태: {status}'}, status=400)
    
    try:
        with connection.cursor() as cursor:
            # 해당 상태의 용기들을 이동서별로 그룹화하여 조회
            # cy_cylinder_current에서 현재 상태가 해당 상태인 용기들의 최신 이동서 정보 조회
            placeholders_keys = ', '.join(['%s'] * len(keys_list))
            
            # tr_move_report_details에서 용기-이동서 연결 조회 (가장 정확한 소스)
            # 없으면 tr_cylinder_status_histories에서 최신 이동서 조회
            query = f'''
                WITH current_cylinders AS (
                    -- 현재 해당 상태인 용기들
                    SELECT 
                        cc.cylinder_no,
                        cc.cylinder_type_key,
                        cc.dashboard_gas_name as gas_name,
                        cc.dashboard_capacity as capacity,
                        cc.dashboard_valve_spec_name as valve_spec,
                        cc.dashboard_status as status,
                        cc.pressure_expire_date
                    FROM cy_cylinder_current cc
                    WHERE cc.cylinder_type_key IN ({placeholders_keys})
                      AND cc.dashboard_status = %s
                ),
                -- tr_move_report_details에서 연결된 이동서 조회 (최신 것)
                detail_links AS (
                    SELECT DISTINCT ON (TRIM(d."CYLINDER_NO"))
                        TRIM(d."CYLINDER_NO") as cylinder_no,
                        TRIM(d."MOVE_REPORT_NO") as move_report_no
                    FROM fcms_cdc.tr_move_report_details d
                    WHERE TRIM(d."CYLINDER_NO") IN (SELECT cylinder_no FROM current_cylinders)
                    ORDER BY TRIM(d."CYLINDER_NO"), d."ADD_DATETIME" DESC NULLS LAST
                ),
                -- tr_cylinder_status_histories에서 최신 이동서 조회 (detail에 없는 경우 백업용)
                history_links AS (
                    SELECT DISTINCT ON (TRIM(h."CYLINDER_NO"))
                        TRIM(h."CYLINDER_NO") as cylinder_no,
                        TRIM(h."MOVE_REPORT_NO") as move_report_no,
                        h."MOVE_DATE" as move_date,
                        h."MOVE_CODE" as move_code
                    FROM fcms_cdc.tr_cylinder_status_histories h
                    WHERE TRIM(h."CYLINDER_NO") IN (SELECT cylinder_no FROM current_cylinders)
                      AND h."MOVE_REPORT_NO" IS NOT NULL 
                      AND TRIM(h."MOVE_REPORT_NO") != ''
                    ORDER BY TRIM(h."CYLINDER_NO"), h."MOVE_DATE" DESC NULLS LAST, h."HISTORY_SEQ" DESC NULLS LAST
                ),
                -- 이동서 연결 통합 (detail 우선, 없으면 history)
                combined_links AS (
                    SELECT 
                        COALESCE(dl.cylinder_no, hl.cylinder_no) as cylinder_no,
                        COALESCE(dl.move_report_no, hl.move_report_no) as move_report_no,
                        hl.move_date,
                        hl.move_code
                    FROM current_cylinders cc
                    LEFT JOIN detail_links dl ON cc.cylinder_no = dl.cylinder_no
                    LEFT JOIN history_links hl ON cc.cylinder_no = hl.cylinder_no
                )
                SELECT 
                    cc.cylinder_no,
                    cc.gas_name,
                    cc.capacity,
                    cc.valve_spec,
                    cc.pressure_expire_date,
                    cl.move_report_no,
                    cl.move_date,
                    cl.move_code,
                    -- 주문 정보
                    TRIM(o."CUSTOMER_ORDER_NO") as customer_order_no,
                    TRIM(o."SUPPLIER_USER_NAME") as customer_name,
                    TRIM(o."TRADE_CONDITION_CODE") as trade_condition_code,
                    TRIM(o."ITEM_NAME") as item_name,
                    o."INSTRUCTION_COUNT" as instruction_count,
                    -- 예정일 (tr_order_informations)
                    oi."FILLING_PLAN_DATE" as filling_plan_date,
                    oi."WAREHOUSING_PLAN_DATE" as warehousing_plan_date,
                    oi."SHIPPING_PLAN_DATE" as shipping_plan_date,
                    -- 확정일 (tr_move_reports)
                    m."FILLING_DATE" as filling_date,
                    m."SHIPPING_DATE" as shipping_date
                FROM current_cylinders cc
                LEFT JOIN combined_links cl ON cc.cylinder_no = cl.cylinder_no
                LEFT JOIN fcms_cdc.tr_orders o ON TRIM(cl.move_report_no) = TRIM(o."ARRIVAL_SHIPPING_NO")
                LEFT JOIN fcms_cdc.tr_order_informations oi ON TRIM(cl.move_report_no) = TRIM(oi."MOVE_REPORT_NO")
                LEFT JOIN fcms_cdc.tr_move_reports m ON TRIM(cl.move_report_no) = TRIM(m."MOVE_REPORT_NO")
                ORDER BY cl.move_report_no NULLS LAST, cc.cylinder_no
            '''
            
            params = keys_list + [status]
            cursor.execute(query, params)
            
            columns = [col[0] for col in cursor.description]
            rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        # 이동서별로 그룹화
        move_reports = defaultdict(lambda: {
            'move_report_no': None,
            'customer_order_no': None,
            'customer_name': None,
            'trade_condition_code': None,
            'item_name': None,
            'instruction_count': 0,
            'filling_plan_date': None,
            'warehousing_plan_date': None,
            'shipping_plan_date': None,
            'filling_date': None,
            'shipping_date': None,
            'cylinders': [],
            'cylinder_count': 0,
        })
        
        no_move_report_cylinders = []  # 이동서 없는 용기들
        
        for row in rows:
            mr_no = row.get('move_report_no')
            
            cylinder_info = {
                'cylinder_no': row.get('cylinder_no', ''),
                'gas_name': row.get('gas_name', ''),
                'capacity': row.get('capacity', ''),
                'valve_spec': row.get('valve_spec', ''),
                'pressure_expire_date': row.get('pressure_expire_date').isoformat() if row.get('pressure_expire_date') else None,
                'move_date': row.get('move_date').isoformat() if row.get('move_date') else None,
            }
            
            if mr_no:
                mr = move_reports[mr_no]
                if mr['move_report_no'] is None:
                    mr['move_report_no'] = mr_no
                    mr['customer_order_no'] = row.get('customer_order_no') or ''
                    mr['customer_name'] = row.get('customer_name') or ''
                    mr['trade_condition_code'] = row.get('trade_condition_code') or ''
                    mr['item_name'] = row.get('item_name') or ''
                    mr['instruction_count'] = row.get('instruction_count') or 0
                    # 예정일
                    mr['filling_plan_date'] = row.get('filling_plan_date').isoformat() if row.get('filling_plan_date') else None
                    mr['warehousing_plan_date'] = row.get('warehousing_plan_date').isoformat() if row.get('warehousing_plan_date') else None
                    mr['shipping_plan_date'] = row.get('shipping_plan_date').isoformat() if row.get('shipping_plan_date') else None
                    # 확정일
                    mr['filling_date'] = row.get('filling_date').isoformat() if row.get('filling_date') else None
                    mr['shipping_date'] = row.get('shipping_date').isoformat() if row.get('shipping_date') else None
                
                mr['cylinders'].append(cylinder_info)
                mr['cylinder_count'] += 1
            else:
                no_move_report_cylinders.append(cylinder_info)
        
        # 리스트로 변환
        result = {
            'ok': True,
            'status': status,
            'move_reports': list(move_reports.values()),
            'no_move_report_cylinders': no_move_report_cylinders,
            'total_cylinder_count': len(rows),
        }
        
        return JsonResponse(result)
        
    except Exception as e:
        import traceback
        return JsonResponse({
            'ok': False, 
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)
