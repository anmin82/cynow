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
    
    queryset = ProductInventory.objects.all()
    
    if gas_name:
        queryset = queryset.filter(gas_name__icontains=gas_name)
    
    # 총 재고
    total_qty = queryset.aggregate(total=Sum('quantity'))['total'] or 0
    
    context = {
        'inventory_list': queryset.order_by('gas_name', 'trade_condition_code'),
        'total_qty': total_qty,
        'filter_gas_name': gas_name,
    }
    return render(request, 'inventory/product.html', context)


def snapshot_list(request):
    """스냅샷 이력"""
    logs = SnapshotLog.objects.all().order_by('-snapshot_date')[:30]
    
    context = {
        'logs': logs,
    }
    return render(request, 'inventory/snapshot.html', context)
