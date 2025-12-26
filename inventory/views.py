"""
재고 현황 뷰
"""
from django.shortcuts import render
from django.db.models import Sum, Count
from django.utils import timezone

from .models import (
    CylinderInventory,
    ProductInventory,
    CylinderInventorySnapshot,
    ProductInventorySnapshot,
    SnapshotLog,
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
    
    queryset = CylinderInventory.objects.all()
    
    if gas_name:
        queryset = queryset.filter(gas_name__icontains=gas_name)
    if status:
        queryset = queryset.filter(status=status)
    
    # 가스명별 집계
    gas_summary = CylinderInventory.objects.values(
        'gas_name'
    ).annotate(
        total=Sum('quantity')
    ).order_by('gas_name')
    
    # 상태별 집계
    status_summary = CylinderInventory.objects.values(
        'status'
    ).annotate(
        total=Sum('quantity')
    ).order_by('status')
    
    # 상태 선택 목록
    status_choices = CylinderInventory.STATUS_CHOICES
    
    context = {
        'inventory_list': queryset.order_by('gas_name', 'status'),
        'gas_summary': gas_summary,
        'status_summary': status_summary,
        'status_choices': status_choices,
        'filter_gas_name': gas_name,
        'filter_status': status,
    }
    return render(request, 'inventory/cylinder.html', context)


def product_inventory(request):
    """제품 재고 현황"""
    # 필터
    gas_name = request.GET.get('gas_name', '')
    product_code_filter = request.GET.get('product_code', '')
    
    queryset = ProductInventory.objects.select_related('product_code').all()
    
    if gas_name:
        queryset = queryset.filter(gas_name__icontains=gas_name)
    if product_code_filter:
        queryset = queryset.filter(trade_condition_code__icontains=product_code_filter)
    
    # 총 재고
    total_qty = queryset.aggregate(total=Sum('quantity'))['total'] or 0
    total_products = queryset.count()
    
    # 재고 리스트에 ProductCode 상세 정보 추가
    inventory_list = []
    for item in queryset.order_by('trade_condition_code'):
        pc = item.product_code
        inventory_list.append({
            'trade_condition_code': item.trade_condition_code,
            'gas_name': item.gas_name,
            'warehouse': item.warehouse,
            'quantity': item.quantity,
            'updated_at': item.updated_at,
            # ProductCode 상세 정보
            'display_name': pc.display_name if pc else item.gas_name,
            'capacity': pc.capacity if pc else None,
            'filling_weight': pc.filling_weight if pc else None,
            'valve_spec_name': pc.valve_spec_name if pc else None,
            'cylinder_spec_name': pc.cylinder_spec_name if pc else None,
            'customer_user_name': pc.customer_user_name if pc else None,
            'current_price': pc.current_price_per_kg if pc else None,
            'has_product_code': pc is not None,
        })
    
    context = {
        'inventory_list': inventory_list,
        'total_qty': total_qty,
        'total_products': total_products,
        'filter_gas_name': gas_name,
        'filter_product_code': product_code_filter,
    }
    return render(request, 'inventory/product.html', context)


def snapshot_list(request):
    """스냅샷 이력"""
    logs = SnapshotLog.objects.all().order_by('-snapshot_date')[:30]
    
    context = {
        'logs': logs,
    }
    return render(request, 'inventory/snapshot.html', context)
