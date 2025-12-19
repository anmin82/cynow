from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
from history.models import HistInventorySnapshot, HistSnapshotRequest, SnapshotType, SnapshotRequestStatus
from core.repositories.view_repository import ViewRepository
from core.utils.cylinder_type import generate_cylinder_type_key


def history(request):
    """변화 이력/분석"""
    # 필터 파라미터
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    snapshot_type = request.GET.get('snapshot_type', '')
    gas_name = request.GET.get('gas_name', '')
    capacity = request.GET.get('capacity', '')
    valve_spec = request.GET.get('valve_spec', '')
    cylinder_spec = request.GET.get('cylinder_spec', '')
    usage_place = request.GET.get('usage_place', '')
    status = request.GET.get('status', '')
    location = request.GET.get('location', '')
    
    # 기본 조회 (최근 30일)
    if not start_date or not end_date:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
    else:
        # 문자열을 date로 변환
        from datetime import datetime
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # 쿼리 필터
    snapshots = HistInventorySnapshot.objects.filter(
        snapshot_datetime__date__gte=start_date,
        snapshot_datetime__date__lte=end_date
    )
    
    if snapshot_type:
        snapshots = snapshots.filter(snapshot_type=snapshot_type)
    if gas_name:
        snapshots = snapshots.filter(gas_name__icontains=gas_name)
    if capacity:
        snapshots = snapshots.filter(capacity__icontains=capacity)
    if valve_spec:
        snapshots = snapshots.filter(valve_spec__icontains=valve_spec)
    if cylinder_spec:
        snapshots = snapshots.filter(cylinder_spec__icontains=cylinder_spec)
    if usage_place:
        snapshots = snapshots.filter(usage_place__icontains=usage_place)
    if status:
        snapshots = snapshots.filter(status=status)
    if location:
        snapshots = snapshots.filter(location__icontains=location)
    
    snapshots = snapshots.order_by('-snapshot_datetime', 'gas_name', 'status', 'location')
    
    # 증감(Δ) 계산을 위한 데이터 준비
    # 전일/전주/전월/기간첫날/직전스냅샷 대비
    snapshot_list = list(snapshots[:1000])  # 최대 1000개
    
    # 증감 계산을 위한 이전 스냅샷 찾기
    for snapshot in snapshot_list:
        # 전일 스냅샷
        prev_day = snapshot.snapshot_datetime.date() - timedelta(days=1)
        prev_day_snapshot = HistInventorySnapshot.objects.filter(
            snapshot_datetime__date=prev_day,
            cylinder_type_key=snapshot.cylinder_type_key,
            status=snapshot.status,
            location=snapshot.location,
            snapshot_type='DAILY'
        ).first()
        
        snapshot.prev_qty = prev_day_snapshot.qty if prev_day_snapshot else None
        if snapshot.prev_qty is not None:
            snapshot.delta = snapshot.qty - snapshot.prev_qty
        else:
            snapshot.delta = None
    
    context = {
        'snapshots': snapshot_list,
        'start_date': start_date,
        'end_date': end_date,
        'snapshot_type': snapshot_type,
        'gas_name': gas_name,
        'capacity': capacity,
        'valve_spec': valve_spec,
        'cylinder_spec': cylinder_spec,
        'usage_place': usage_place,
        'status': status,
        'location': location,
    }
    return render(request, 'history/history.html', context)


@login_required
@permission_required('cynow.can_edit_plan', raise_exception=True)
def manual_snapshot(request):
    """수동 스냅샷 저장"""
    # 최근 스냅샷 요청 기록
    snapshot_requests = HistSnapshotRequest.objects.filter(
        requested_by=request.user
    ).order_by('-requested_at')[:10]
    
    if request.method == 'POST':
        snapshot_datetime = timezone.now()
        
        try:
            # VIEW에서 현재 인벤토리 데이터 조회
            inventory_data = ViewRepository.get_inventory_view()
            
            inserted_count = 0
            skipped_count = 0
            
            for row in inventory_data:
                try:
                    # source_view_updated_at을 timezone aware로 변환
                    source_updated_at = row.get('updated_at')
                    if source_updated_at and isinstance(source_updated_at, str):
                        try:
                            from datetime import datetime
                            dt = datetime.strptime(source_updated_at, '%Y-%m-%d %H:%M:%S')
                            source_updated_at = timezone.make_aware(dt)
                        except:
                            source_updated_at = None
                    elif source_updated_at and not timezone.is_aware(source_updated_at):
                        source_updated_at = timezone.make_aware(source_updated_at)
                    
                    HistInventorySnapshot.objects.create(
                        snapshot_datetime=snapshot_datetime,
                        snapshot_type=SnapshotType.MANUAL,
                        cylinder_type_key=row.get('cylinder_type_key', ''),
                        gas_name=row.get('gas_name', ''),
                        capacity=row.get('capacity'),
                        valve_spec=row.get('valve_spec'),
                        cylinder_spec=row.get('cylinder_spec'),
                        usage_place=row.get('usage_place'),
                        status=row.get('status', ''),
                        location=row.get('location', ''),
                        qty=row.get('qty', 0),
                        source_view_updated_at=source_updated_at,
                        created_by=request.user,
                    )
                    inserted_count += 1
                except Exception as e:
                    skipped_count += 1
            
            # 성공 기록
            HistSnapshotRequest.objects.create(
                requested_at=snapshot_datetime,
                requested_by=request.user,
                reason=request.POST.get('reason', '수동 스냅샷'),
                status=SnapshotRequestStatus.SUCCESS,
                message=f'{inserted_count} records inserted, {skipped_count} skipped'
            )
            
            messages.success(request, f'스냅샷이 저장되었습니다. ({inserted_count}건)')
            return redirect('history:history')
        except Exception as e:
            # 실패 기록
            HistSnapshotRequest.objects.create(
                requested_at=snapshot_datetime,
                requested_by=request.user,
                reason=request.POST.get('reason', '수동 스냅샷'),
                status=SnapshotRequestStatus.FAILED,
                message=str(e)
            )
            messages.error(request, f'스냅샷 저장 실패: {e}')
    
    context = {
        'snapshot_requests': snapshot_requests,
    }
    return render(request, 'history/manual_snapshot.html', context)


def export_excel(request):
    """엑셀 다운로드"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment
    from django.http import HttpResponse
    from datetime import datetime
    
    # 필터 파라미터
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    snapshot_type = request.GET.get('snapshot_type', '')
    gas_name = request.GET.get('gas_name', '')
    capacity = request.GET.get('capacity', '')
    valve_spec = request.GET.get('valve_spec', '')
    cylinder_spec = request.GET.get('cylinder_spec', '')
    usage_place = request.GET.get('usage_place', '')
    status = request.GET.get('status', '')
    location = request.GET.get('location', '')
    
    if not start_date or not end_date:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    snapshots = HistInventorySnapshot.objects.filter(
        snapshot_datetime__date__gte=start_date,
        snapshot_datetime__date__lte=end_date
    )
    
    if snapshot_type:
        snapshots = snapshots.filter(snapshot_type=snapshot_type)
    if gas_name:
        snapshots = snapshots.filter(gas_name__icontains=gas_name)
    if capacity:
        snapshots = snapshots.filter(capacity__icontains=capacity)
    if valve_spec:
        snapshots = snapshots.filter(valve_spec__icontains=valve_spec)
    if cylinder_spec:
        snapshots = snapshots.filter(cylinder_spec__icontains=cylinder_spec)
    if usage_place:
        snapshots = snapshots.filter(usage_place__icontains=usage_place)
    if status:
        snapshots = snapshots.filter(status=status)
    if location:
        snapshots = snapshots.filter(location__icontains=location)
    
    snapshots = snapshots.order_by('-snapshot_datetime', 'gas_name', 'status', 'location')
    
    # 엑셀 생성
    wb = Workbook()
    ws = wb.active
    ws.title = "이력 데이터"
    
    # 헤더
    headers = ['스냅샷 일시', '유형', '가스명', '용량', '밸브', '스펙', '사용처', '상태', '위치', '수량', '전일 수량', '증감']
    ws.append(headers)
    
    # 헤더 스타일
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
    
    # 데이터
    for snapshot in snapshots:
        # 전일 스냅샷 찾기
        prev_day = snapshot.snapshot_datetime.date() - timedelta(days=1)
        prev_day_snapshot = HistInventorySnapshot.objects.filter(
            snapshot_datetime__date=prev_day,
            cylinder_type_key=snapshot.cylinder_type_key,
            status=snapshot.status,
            location=snapshot.location,
            snapshot_type='DAILY'
        ).first()
        
        prev_qty = prev_day_snapshot.qty if prev_day_snapshot else None
        delta = (snapshot.qty - prev_qty) if prev_qty is not None else None
        
        ws.append([
            snapshot.snapshot_datetime.strftime('%Y-%m-%d %H:%M:%S'),
            snapshot.get_snapshot_type_display(),
            snapshot.gas_name,
            snapshot.capacity or '',
            snapshot.valve_spec or '',
            snapshot.cylinder_spec or '',
            snapshot.usage_place or '',
            snapshot.status,
            snapshot.location,
            snapshot.qty,
            prev_qty or '',
            delta if delta is not None else '',
        ])
    
    # 응답 생성
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="cynow_history_{start_date}_{end_date}.xlsx"'
    wb.save(response)
    
    return response
