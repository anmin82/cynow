"""
재고 현황 뷰
"""
from django.shortcuts import render
from django.db.models import Sum, Count
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import connection

from .models import (
    CylinderInventory,
    ProductInventory,
    CylinderInventorySnapshot,
    ProductInventorySnapshot,
    SnapshotLog,
    CylinderMaintenanceLog,
)


def index(request):
    """재고 현황 메인 (요약)"""
    # 용기 재고 요약
    cylinder_summary = CylinderInventory.objects.values(
        'gas_name', 'status'
    ).annotate(
        total=Sum('quantity')
    ).order_by('gas_name', 'status')
    
    # 제품 재고 요약
    product_summary = ProductInventory.objects.all().order_by('gas_name')
    
    # 최근 스냅샷
    latest_snapshot = SnapshotLog.objects.filter(
        status='SUCCESS'
    ).order_by('-snapshot_date').first()
    
    context = {
        'cylinder_summary': cylinder_summary,
        'product_summary': product_summary,
        'latest_snapshot': latest_snapshot,
    }
    return render(request, 'inventory/index.html', context)


def cylinder_inventory(request):
    """용기 재고 현황"""
    # 필터
    gas_name = request.GET.get('gas_name', '')
    status = request.GET.get('status', '')
    show_all = request.GET.get('show_all', '')  # '1'이면 전체보기
    
    queryset = CylinderInventory.objects.all()
    
    if gas_name:
        queryset = queryset.filter(gas_name__icontains=gas_name)
    if status:
        queryset = queryset.filter(status=status)

    core_gases = ['COS', 'CF4', 'CLF3']
    if show_all != '1' and not gas_name:
        queryset = queryset.filter(gas_name__in=core_gases)
    
    # 가스명별 집계
    gas_summary = queryset.values(
        'gas_name'
    ).annotate(
        total=Sum('quantity')
    ).order_by('gas_name')
    
    # 상태별 집계
    status_summary = queryset.values(
        'status'
    ).annotate(
        total=Sum('quantity')
    ).order_by('status')

    total_qty = queryset.aggregate(total=Sum('quantity'))['total'] or 0
    
    # 상태 선택 목록
    status_choices = CylinderInventory.STATUS_CHOICES
    
    context = {
        'inventory_list': queryset.order_by('gas_name', 'status'),
        'gas_summary': gas_summary,
        'status_summary': status_summary,
        'status_choices': status_choices,
        'filter_gas_name': gas_name,
        'filter_status': status,
        'show_all': show_all,
        'core_gases': core_gases,
        'total_qty': total_qty,
    }
    return render(request, 'inventory/cylinder.html', context)


def product_inventory(request):
    """제품 재고 현황"""
    # 필터
    gas_name = request.GET.get('gas_name', '')
    product_code_filter = request.GET.get('product_code', '')
    show_all = request.GET.get('show_all', '')  # '1'이면 전체보기
    
    queryset = ProductInventory.objects.select_related('product_code').all()
    
    if gas_name:
        queryset = queryset.filter(gas_name__icontains=gas_name)
    if product_code_filter:
        queryset = queryset.filter(trade_condition_code__icontains=product_code_filter)
    
    core_gases = ['COS', 'CF4', 'CLF3']

    # 재고 리스트에 ProductCode 상세 정보 추가
    inventory_list = []
    for item in queryset.order_by('trade_condition_code'):
        pc = item.product_code
        base_gas = (pc.gas_name if pc else '') or ''
        display_name = (pc.display_name if pc else '') or item.gas_name

        row = {
            'trade_condition_code': item.trade_condition_code,
            'warehouse': item.warehouse,
            'quantity': item.quantity,
            'updated_at': item.updated_at,
            # ProductCode 상세 정보
            'product_display_name': display_name,
            'gas_name': base_gas or item.gas_name,
            'capacity': pc.capacity if pc else None,
            'filling_weight': pc.filling_weight if pc else None,
            'valve_spec_name': pc.valve_spec_name if pc else None,
            'cylinder_spec_name': pc.cylinder_spec_name if pc else None,
            'customer_user_name': pc.customer_user_name if pc else None,
            'current_price': pc.current_price_per_kg if pc else None,
            'has_product_code': pc is not None,
        }

        # 기본은 우리 취급 가스만 표시 (필요 시 전체보기)
        if show_all != '1':
            gas_upper = (base_gas or '').upper()
            display_upper = (display_name or '').upper()
            if not any(g in gas_upper or display_upper.startswith(g) for g in core_gases):
                continue

        inventory_list.append(row)

    # 총 재고 (표시 리스트 기준)
    total_qty = sum(int(x.get('quantity') or 0) for x in inventory_list)
    total_products = len(inventory_list)
    
    context = {
        'inventory_list': inventory_list,
        'total_qty': total_qty,
        'total_products': total_products,
        'filter_gas_name': gas_name,
        'filter_product_code': product_code_filter,
        'show_all': show_all,
        'core_gases': core_gases,
    }
    return render(request, 'inventory/product.html', context)


def snapshot_list(request):
    """스냅샷 이력"""
    logs = SnapshotLog.objects.all().order_by('-snapshot_date')[:30]
    
    context = {
        'logs': logs,
    }
    return render(request, 'inventory/snapshot.html', context)


def maintenance(request):
    """
    정비 입출고(FCMS 외) 관리
    - 조회: 누구나 가능
    - 등록: 로그인 필요 (POST)
    """
    # 등록 처리 (로그인 필요)
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "로그인이 필요합니다.")
            return render(request, "inventory/maintenance.html", _maintenance_context(request))

        cylinder_no = (request.POST.get("cylinder_no") or "").strip()
        event_type = (request.POST.get("event_type") or "").strip().upper()
        event_date_s = (request.POST.get("event_date") or "").strip()
        vendor_name = (request.POST.get("vendor_name") or "").strip()
        reference_no = (request.POST.get("reference_no") or "").strip()
        remarks = (request.POST.get("remarks") or "").strip()

        if not cylinder_no:
            messages.error(request, "용기번호는 필수입니다.")
            return render(request, "inventory/maintenance.html", _maintenance_context(request))
        if event_type not in ("OUT", "IN"):
            messages.error(request, "구분(정비출고/정비입고)을 선택해주세요.")
            return render(request, "inventory/maintenance.html", _maintenance_context(request))

        from datetime import datetime
        from django.utils import timezone as dj_tz
        try:
            event_date = datetime.strptime(event_date_s, "%Y-%m-%d").date() if event_date_s else dj_tz.localdate()
        except ValueError:
            messages.error(request, "일자 형식이 올바르지 않습니다. (YYYY-MM-DD)")
            return render(request, "inventory/maintenance.html", _maintenance_context(request))

        CylinderMaintenanceLog.objects.create(
            cylinder_no=cylinder_no,
            event_type=event_type,
            event_date=event_date,
            vendor_name=vendor_name,
            reference_no=reference_no,
            remarks=remarks,
            created_by=request.user,
        )
        messages.success(request, "정비 기록이 등록되었습니다.")

    return render(request, "inventory/maintenance.html", _maintenance_context(request))


def _maintenance_context(request):
    """정비 화면 공통 컨텍스트 (목록/필터)"""
    open_only = request.GET.get("open_only", "1")  # 기본: 정비중만
    cylinder_no = (request.GET.get("cylinder_no") or "").strip()
    vendor = (request.GET.get("vendor") or "").strip()

    # 최신 이벤트(용기별)만 보여주기
    # latest OUT = 정비중, latest IN = 복귀
    query = """
        WITH latest AS (
            SELECT DISTINCT ON (l.cylinder_no)
                l.id,
                l.cylinder_no,
                l.event_type,
                l.event_date,
                l.vendor_name,
                l.reference_no,
                l.remarks,
                l.created_at
            FROM cylinder_maintenance_log l
            ORDER BY l.cylinder_no, l.event_date DESC, l.id DESC
        )
        SELECT
            lt.*,
            cc.dashboard_gas_name,
            cc.dashboard_capacity,
            cc.dashboard_valve_spec_name,
            cc.dashboard_cylinder_spec_name
        FROM latest lt
        LEFT JOIN cy_cylinder_current cc
            ON TRIM(cc.cylinder_no) = TRIM(lt.cylinder_no)
        WHERE 1=1
    """
    params = []

    if open_only == "1":
        query += " AND lt.event_type = 'OUT'"
    if cylinder_no:
        query += " AND lt.cylinder_no ILIKE %s"
        params.append(f"%{cylinder_no}%")
    if vendor:
        query += " AND lt.vendor_name ILIKE %s"
        params.append(f"%{vendor}%")

    query += " ORDER BY lt.event_type DESC, lt.event_date DESC, lt.cylinder_no"

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        cols = [c[0] for c in cursor.description]
        rows = [dict(zip(cols, r)) for r in cursor.fetchall()]

    total_open = sum(1 for r in rows if r.get("event_type") == "OUT")

    return {
        "rows": rows,
        "open_only": open_only,
        "filter_cylinder_no": cylinder_no,
        "filter_vendor": vendor,
        "total_open": total_open,
        "today": timezone.localdate(),
    }
