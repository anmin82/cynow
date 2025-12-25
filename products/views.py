"""
제품코드 관리 뷰
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from decimal import Decimal
from datetime import date

from .models import ProductCode, ProductPriceHistory, ProductCodeSync
from .services import sync_product_codes_from_cdc, get_cdc_product_count


def product_list(request):
    """제품코드 목록 (누구나 조회 가능)"""
    queryset = ProductCode.objects.all()
    
    # 검색
    search = request.GET.get('search', '').strip()
    if search:
        queryset = queryset.filter(
            Q(trade_condition_no__icontains=search) |
            Q(display_name__icontains=search) |
            Q(gas_name__icontains=search) |
            Q(customer_user_code__icontains=search)
        )
    
    # 활성화 필터
    show_inactive = request.GET.get('show_inactive') == '1'
    if not show_inactive:
        queryset = queryset.filter(is_active=True)
    
    # 정렬
    queryset = queryset.order_by('trade_condition_no')
    
    # 페이징
    paginator = Paginator(queryset, 50)
    page = request.GET.get('page', 1)
    products = paginator.get_page(page)
    
    # CDC 상태
    cdc_count = get_cdc_product_count()
    cynow_count = ProductCode.objects.count()
    last_sync = ProductCodeSync.objects.filter(status='SUCCESS').first()
    
    context = {
        'products': products,
        'search': search,
        'show_inactive': show_inactive,
        'cdc_count': cdc_count,
        'cynow_count': cynow_count,
        'last_sync': last_sync,
    }
    return render(request, 'products/list.html', context)


def product_detail(request, pk):
    """제품코드 상세"""
    product = get_object_or_404(ProductCode, pk=pk)
    price_history = product.price_history.all()[:10]
    current_price = product.get_current_price()
    
    context = {
        'product': product,
        'price_history': price_history,
        'current_price': current_price,
    }
    return render(request, 'products/detail.html', context)


@login_required
@require_POST
def sync_from_cdc(request):
    """CDC에서 제품코드 동기화 (AJAX)"""
    result = sync_product_codes_from_cdc()
    
    if result['success']:
        return JsonResponse({
            'success': True,
            'message': f"동기화 완료: {result['created']}건 생성, {result['updated']}건 업데이트"
        })
    else:
        return JsonResponse({
            'success': False,
            'error': result['error']
        }, status=500)


@login_required
def product_edit(request, pk):
    """제품코드 수정 (용기종류 매핑, 메모 등)"""
    product = get_object_or_404(ProductCode, pk=pk)
    
    if request.method == 'POST':
        product.cylinder_type_key = request.POST.get('cylinder_type_key', '').strip() or None
        product.display_name = request.POST.get('display_name', '').strip() or None
        product.default_currency = request.POST.get('default_currency', 'KRW')
        product.is_active = request.POST.get('is_active') == '1'
        product.note = request.POST.get('note', '').strip() or None
        product.save()
        
        messages.success(request, f'{product.trade_condition_no} 수정 완료')
        return redirect('products:detail', pk=pk)
    
    # 용기종류 목록 (매핑용)
    from plans.views import get_cylinder_type_list
    try:
        cylinder_types = get_cylinder_type_list()
    except:
        cylinder_types = []
    
    context = {
        'product': product,
        'cylinder_types': cylinder_types,
    }
    return render(request, 'products/edit.html', context)


@login_required
@require_POST
def price_add(request, pk):
    """단가 추가 (AJAX)"""
    product = get_object_or_404(ProductCode, pk=pk)
    
    try:
        effective_date = request.POST.get('effective_date')
        price_per_kg = request.POST.get('price_per_kg')
        currency = request.POST.get('currency', 'KRW')
        note = request.POST.get('note', '').strip()
        
        if not effective_date or not price_per_kg:
            return JsonResponse({'success': False, 'error': '필수 항목을 입력하세요'})
        
        # 통화 유효성 검사
        if currency not in ['KRW', 'JPY', 'USD', 'CNY']:
            currency = 'KRW'
        
        price = ProductPriceHistory.objects.create(
            product_code=product,
            effective_date=date.fromisoformat(effective_date),
            price_per_kg=Decimal(price_per_kg),
            currency=currency,
            note=note or None,
            created_by=request.user
        )
        
        # 통화별 메시지
        currency_units = {'KRW': '원', 'JPY': '円', 'USD': '$', 'CNY': '元'}
        unit = currency_units.get(currency, '원')
        
        return JsonResponse({
            'success': True,
            'message': f'{effective_date}부터 {price_per_kg}{unit}/kg 적용'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@require_POST
def price_delete(request, price_id):
    """단가 삭제 (AJAX)"""
    price = get_object_or_404(ProductPriceHistory, pk=price_id)
    product_pk = price.product_code.pk
    price.delete()
    
    return JsonResponse({'success': True})
