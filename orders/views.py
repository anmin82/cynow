"""
수주 페이지 뷰

목적:
A) 고객 이메일로 받은 수주 정보 입력
B) 이동서번호 가이드 표시
C) 진행 현황 모니터링

개선:
- ProductCode 자동완성/검색
- 단가 자동 로딩
- 금액/중량 합계 표시
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Sum, Q
from django.db.utils import ProgrammingError, OperationalError
import logging

from .models import PO, POItem, MoveNoGuide, FCMSMatchStatus, FCMSProductionProgress, PlannedMoveReport
from .forms import POForm, POItemFormSet
from .repositories.fcms_repository import FcmsRepository
from django.utils import timezone

logger = logging.getLogger(__name__)

_EDIT_UNLOCK_TTL_SECONDS = 5 * 60  # 5분: 삭제와 유사한 수준의 "한 번 더" 확인 마찰


def _edit_unlock_session_key(customer_order_no: str) -> str:
    return f"orders:edit-unlock:{customer_order_no}"


@require_POST
def po_edit_unlock(request, customer_order_no):
    """
    수주 수정 '잠금 해제' (삭제처럼 쉽게 못 하게 하기)

    - 상세 화면에서 PO번호 재입력을 요구 (삭제 버튼과 동일한 2-step 확인 UX)
    - 성공 시 세션에 짧은 TTL 토큰 저장 후 edit 화면으로 이동
    - 사용자가 /edit/ URL을 직접 입력해도 토큰 없으면 차단됨 (po_edit에서 검증)
    """
    po = get_object_or_404(PO, customer_order_no=customer_order_no)

    confirm_no = (request.POST.get("confirm_customer_order_no") or "").strip()
    # 사유는 선택 입력 (UI/요청에 따라 제거/비활성화될 수 있음)
    reason = (request.POST.get("edit_reason") or "").strip()

    if confirm_no != po.customer_order_no:
        messages.error(request, "PO번호가 일치하지 않습니다. 수정은 진행할 수 없습니다.")
        return redirect("orders:detail", customer_order_no=customer_order_no)

    request.session[_edit_unlock_session_key(customer_order_no)] = {
        "ts": int(timezone.now().timestamp()),
        "reason": reason,
        "by": request.user.username if getattr(request, "user", None) and request.user.is_authenticated else None,
    }
    request.session.modified = True

    logger.info(
        "orders.po_edit_unlock: customer_order_no=%s by=%s reason=%s",
        customer_order_no,
        request.user.username if getattr(request, "user", None) and request.user.is_authenticated else "anonymous",
        reason,
    )

    return redirect("orders:edit", customer_order_no=customer_order_no)


def po_list(request):
    """
    수주 목록
    
    표시 컬럼:
    - PO번호 (customer_order_no)
    - 고객명
    - 수주일
    - 수주수량
    - 추천이동서번호
    - 상태
    - 진행현황
    """
    # 필터
    status = request.GET.get('status', '')
    supplier = request.GET.get('supplier', '')
    
    # 비로그인 사용자도 목록 조회 가능 (단가/금액만 블라인드 - 템플릿에서 처리)

    try:
        pos = PO.objects.all()

        if status:
            pos = pos.filter(status=status)

        if supplier:
            pos = pos.filter(supplier_user_code__icontains=supplier)

        # 상위 100개만 (페이지네이션 필요 시 추가)
        pos = pos[:100]

        # 각 PO의 추천번호와 진행현황 추가
        po_list = []
        for po in pos:
            # 최신 가이드
            guide = po.move_guides.first()

            # 매칭 상태
            try:
                match_status = po.fcms_match_status
            except FCMSMatchStatus.DoesNotExist:
                match_status = None

            po_list.append({
                'po': po,
                'guide': guide,
                'match_status': match_status,
            })
    except (ProgrammingError, OperationalError):
        # 마이그레이션 미적용 등으로 테이블이 없을 때 500 대신 안내
        context = {
            "po_list": [],
            "current_status": "",
            "current_supplier": "",
            "status_choices": PO.STATUS_CHOICES,
            "error_message": "PO 기능이 아직 초기화되지 않았습니다. (DB 테이블 없음) 관리자에게 문의해주세요.",
        }
        return render(request, "orders/po_list.html", context)
    
    context = {
        'po_list': po_list,
        'current_status': status,
        'current_supplier': supplier,
        'status_choices': PO.STATUS_CHOICES,
    }
    
    return render(request, 'orders/po_list.html', context)


def po_detail(request, customer_order_no):
    """
    수주 상세
    
    - 수주 정보
    - 품목 목록
    - 이동서번호 가이드
    - FCMS 매칭 상태
    - 진행 현황
    """
    po = get_object_or_404(PO, customer_order_no=customer_order_no)
    
    # 품목
    items = po.items.all()
    
    # FCMS 매칭 상태
    try:
        match_status = po.fcms_match_status
    except FCMSMatchStatus.DoesNotExist:
        match_status = None
    
    context = {
        'po': po,
        'items': items,
        'match_status': match_status,
    }
    
    return render(request, 'orders/po_detail.html', context)


def po_create(request):
    """수주 생성"""
    if request.method == 'POST':
        form = POForm(request.POST)
        formset = POItemFormSet(request.POST)
        
        # 디버깅: 폼 유효성 검사 결과 출력
        form_valid = form.is_valid()
        formset_valid = formset.is_valid()
        
        if not form_valid:
            print(f"[PO Create] Form errors: {form.errors}")
        if not formset_valid:
            print(f"[PO Create] Formset errors: {formset.errors}")
            print(f"[PO Create] Formset non_form_errors: {formset.non_form_errors()}")
        
        if form_valid and formset_valid:
            # PO 저장
            po = form.save(commit=False)
            
            # 고객 정보 동기화
            if po.customer:
                po.sync_from_customer()
            
            # 작성자 설정
            if request.user.is_authenticated:
                po.created_by = request.user
            
            po.save()
            
            # 품목 저장 (line_no 자동 채우기)
            formset.instance = po
            items = formset.save(commit=False)
            
            # 삭제 처리
            for obj in formset.deleted_objects:
                obj.delete()
            
            # line_no 자동 부여
            line_no = 1
            for item in items:
                if not item.line_no:
                    item.line_no = line_no
                item.save()
                line_no += 1
            
            # 상태 자동 설정: 품목이 있으면 진행중, 없으면 임시저장
            if items:
                po.status = 'IN_PROGRESS'
            else:
                po.status = 'DRAFT'
            po.save(update_fields=['status'])
            
            messages.success(request, f'수주 {po.customer_order_no}가 등록되었습니다.')
            return redirect('orders:detail', customer_order_no=po.customer_order_no)
    else:
        form = POForm()
        formset = POItemFormSet()
    
    context = {
        'form': form,
        'formset': formset,
        'is_edit': False,
    }
    return render(request, 'orders/po_form.html', context)


def po_edit(request, customer_order_no):
    """수주 수정"""
    po = get_object_or_404(PO, customer_order_no=customer_order_no)

    # 수정은 "잠금 해제" 절차 후에만 허용 (상세 화면에서 POST로 unlock)
    unlock_key = _edit_unlock_session_key(customer_order_no)
    unlock = request.session.get(unlock_key)
    now_ts = int(timezone.now().timestamp())
    unlock_ts = int(unlock.get("ts", 0)) if isinstance(unlock, dict) else 0

    if not unlock_ts:
        messages.warning(request, "수정은 확인 절차(PO번호/사유 입력) 후 진행할 수 있습니다.")
        return redirect("orders:detail", customer_order_no=customer_order_no)

    if now_ts - unlock_ts > _EDIT_UNLOCK_TTL_SECONDS:
        request.session.pop(unlock_key, None)
        messages.warning(request, "수정 확인 시간이 만료되었습니다. 다시 시도해 주세요.")
        return redirect("orders:detail", customer_order_no=customer_order_no)
    
    if request.method == 'POST':
        form = POForm(request.POST, instance=po)
        formset = POItemFormSet(request.POST, instance=po)
        
        if form.is_valid() and formset.is_valid():
            po = form.save()
            formset.save()
            
            # 상태 자동 업데이트 (COMPLETED가 아닌 경우만)
            if po.status != 'COMPLETED':
                if po.items.exists():
                    po.status = 'IN_PROGRESS'
                else:
                    po.status = 'DRAFT'
                po.save(update_fields=['status'])
            
            messages.success(request, f'수주 {po.customer_order_no}가 수정되었습니다.')
            # 수정 완료 후 토큰 제거 (한 번 더 확인 요구)
            request.session.pop(unlock_key, None)
            return redirect('orders:detail', customer_order_no=customer_order_no)
    else:
        form = POForm(instance=po)
        formset = POItemFormSet(instance=po)
    
    context = {
        'form': form,
        'formset': formset,
        'po': po,
        'is_edit': True,
    }
    return render(request, 'orders/po_form.html', context)


@require_POST
def po_delete(request, customer_order_no):
    """수주 삭제 (상태 변경)"""
    po = get_object_or_404(PO, customer_order_no=customer_order_no)
    po.delete()
    
    messages.success(request, 'PO가 삭제되었습니다.')
    return redirect('orders:list')


@require_POST
def generate_guide(request, customer_order_no):
    """
    이동서번호 가이드 생성
    
    FCMS 최신 번호 조회 → +1 계산 → 추천값 표시
    """
    po = get_object_or_404(PO, customer_order_no=customer_order_no)
    
    # TODO: FCMS CDC에서 최신 번호 조회하여 계산
    # 현재는 임시로 더미 번호 생성
    from datetime import datetime
    year = datetime.now().strftime('%y')
    
    # 기존 가이드가 있으면 재사용
    existing_guide = po.move_guides.first()
    if existing_guide:
        messages.info(request, f'이미 가이드가 생성되었습니다: {existing_guide.suggested_move_no}')
    else:
        # 새 가이드 생성
        # TODO: 실제 FCMS MAX 번호 조회 로직 구현 필요
        suggested_no = f"FP{year}000001"  # 임시
        
        guide = MoveNoGuide.objects.create(
            po=po,
            suggested_move_no=suggested_no
        )
        
        po.status = 'GUIDED'
        po.save()
        
        messages.success(request, f'이동서번호 가이드가 생성되었습니다: {suggested_no}')
    
    return redirect('orders:detail', customer_order_no=customer_order_no)


@require_POST
def check_fcms_match(request, customer_order_no):
    """
    FCMS 매칭 검증
    
    CDC에서 실제 FCMS 데이터 조회하여 비교
    """
    po = get_object_or_404(PO, customer_order_no=customer_order_no)
    
    try:
        # FCMS CDC에서 해당 PO번호로 데이터 조회
        progress_summary = FcmsRepository.get_production_summary_by_customer_order_no(
            customer_order_no
        )
        
        fcms_count = progress_summary.get('total_arrival_count', 0)
        
        # 매칭 상태 업데이트
        if fcms_count > 0:
            match_state = 'MATCHED'
            note = f'FCMS에서 {fcms_count}건의 이동서 확인됨'
            
            # PO 상태도 업데이트
            if po.status in ('DRAFT', 'IN_PROGRESS', 'GUIDED'):
                po.status = 'MATCHED'
                po.save(update_fields=['status'])
        else:
            match_state = 'NOT_ENTERED'
            note = 'FCMS에 아직 등록된 이동서가 없습니다'
        
        match_status, created = FCMSMatchStatus.objects.update_or_create(
            po=po,
            defaults={
                'match_state': match_state,
                'note': note
            }
        )
        
        messages.info(request, f'FCMS 매칭 확인 완료: {note}')
        
    except Exception as e:
        messages.error(request, f'FCMS 조회 실패: {e}')
    
    return redirect('orders:detail', customer_order_no=customer_order_no)


# ============================================
# 고객 정보 API
# ============================================

@require_GET
def api_get_customer(request, customer_id):
    """
    고객 정보 조회 API
    
    GET /orders/api/customers/<customer_id>/
    """
    from voucher.models import CompanyInfo
    
    try:
        customer = CompanyInfo.objects.get(pk=customer_id, is_customer=True, is_active=True)
        
        return JsonResponse({
            'id': customer.pk,
            'code': customer.code,
            'name': customer.name,
            'name_en': customer.name_en or '',
            'address': customer.address or '',
            'tel': customer.tel or '',
            'email': customer.email or '',
            'manager_name': customer.manager_name or '',
        })
    
    except CompanyInfo.DoesNotExist:
        return JsonResponse({'error': '고객을 찾을 수 없습니다.'}, status=404)


@require_GET
def api_list_products(request):
    """
    전체 제품 목록 API (드롭다운용)
    
    GET /orders/api/products/
    """
    from products.models import ProductCode
    
    try:
        products = ProductCode.objects.filter(
            is_active=True
        ).order_by('trade_condition_no')
        
        currency_symbols = {'KRW': '₩', 'JPY': '¥', 'USD': '$', 'CNY': '¥'}
        
        results = []
        for p in products:
            # 현재 단가 조회
            current_price = p.get_current_price()
            unit_price = float(current_price.price_per_kg) if current_price else None
            
            # 표시 텍스트 구성
            display_text = f"{p.trade_condition_no}"
            if p.gas_name:
                display_text += f" - {p.gas_name}"
            if p.cylinder_spec_name:
                display_text += f" ({p.cylinder_spec_name}"
                if p.valve_spec_name:
                    display_text += f"/{p.valve_spec_name}"
                display_text += ")"
            
            results.append({
                'pk': p.selection_pattern_code,
                'code': p.trade_condition_no,
                'display': display_text,
                'name': p.display_name or p.gas_name or p.trade_condition_no,
                'gas_name': p.gas_name or '',
                'cylinder_spec': p.cylinder_spec_name or '',
                'valve_spec': p.valve_spec_name or '',
                'capacity': float(p.capacity) if p.capacity else None,
                'filling_weight': float(p.filling_weight) if p.filling_weight else None,
                'unit_price': unit_price,
                'currency': p.default_currency,
                'currency_symbol': currency_symbols.get(p.default_currency, ''),
            })
        
        return JsonResponse(results, safe=False)
    
    except (ProgrammingError, OperationalError):
        return JsonResponse([], safe=False)


# ============================================
# 제품코드 검색 API (자동완성용)
# ============================================

@require_GET
def api_search_products(request):
    """
    제품코드 검색 API
    
    GET /orders/api/products/search/?q=KF
    
    Returns:
        [
            {
                "pk": "SEL001",
                "code": "KF001",
                "name": "COS 25kg CGA330",
                "gas_name": "COS",
                "cylinder_spec": "47L",
                "valve_spec": "CGA330",
                "filling_weight": 25.0,
                "unit_price": 15000.0,
                "currency": "KRW",
                "currency_symbol": "₩"
            },
            ...
        ]
    """
    from products.models import ProductCode
    
    q = request.GET.get('q', '').strip()
    
    if len(q) < 1:
        return JsonResponse([], safe=False)
    
    try:
        products = ProductCode.objects.filter(
            is_active=True
        ).filter(
            Q(trade_condition_no__icontains=q) |
            Q(gas_name__icontains=q) |
            Q(display_name__icontains=q)
        ).order_by('trade_condition_no')[:20]
        
        currency_symbols = {'KRW': '₩', 'JPY': '¥', 'USD': '$', 'CNY': '¥'}
        
        results = []
        for p in products:
            # 현재 단가 조회
            current_price = p.get_current_price()
            unit_price = float(current_price.price_per_kg) if current_price else None
            
            results.append({
                'pk': p.selection_pattern_code,
                'code': p.trade_condition_no,
                'name': p.display_name or p.gas_name or p.trade_condition_no,
                'gas_name': p.gas_name or '',
                'cylinder_spec': p.cylinder_spec_name or '',
                'valve_spec': p.valve_spec_name or '',
                'capacity': float(p.capacity) if p.capacity else None,
                'filling_weight': float(p.filling_weight) if p.filling_weight else None,
                'unit_price': unit_price,
                'currency': p.default_currency,
                'currency_symbol': currency_symbols.get(p.default_currency, ''),
            })
        
        return JsonResponse(results, safe=False)
    
    except (ProgrammingError, OperationalError):
        return JsonResponse([], safe=False)


@require_GET
def api_get_product(request, product_code):
    """
    특정 제품코드 정보 조회 API
    
    GET /orders/api/products/<product_code>/
    """
    from products.models import ProductCode
    
    try:
        p = ProductCode.objects.get(trade_condition_no=product_code, is_active=True)
        
        currency_symbols = {'KRW': '₩', 'JPY': '¥', 'USD': '$', 'CNY': '¥'}
        current_price = p.get_current_price()
        unit_price = float(current_price.price_per_kg) if current_price else None
        
        return JsonResponse({
            'pk': p.selection_pattern_code,
            'code': p.trade_condition_no,
            'name': p.display_name or p.gas_name or p.trade_condition_no,
            'gas_name': p.gas_name or '',
            'cylinder_spec': p.cylinder_spec_name or '',
            'valve_spec': p.valve_spec_name or '',
            'capacity': float(p.capacity) if p.capacity else None,
            'filling_weight': float(p.filling_weight) if p.filling_weight else None,
            'unit_price': unit_price,
            'currency': p.default_currency,
            'currency_symbol': currency_symbols.get(p.default_currency, ''),
        })
    
    except ProductCode.DoesNotExist:
        return JsonResponse({'error': '제품코드를 찾을 수 없습니다.'}, status=404)
    except (ProgrammingError, OperationalError):
        return JsonResponse({'error': 'DB 오류'}, status=500)


# ============================================
# 수주관리표 (생산 진척 현황)
# ============================================

def order_management_list(request):
    """
    수주관리표 목록
    
    CYNOW PO와 FCMS CDC 데이터를 매칭하여 
    생산 진척 현황을 종합적으로 보여주는 대시보드
    """
    
    # CYNOW에 등록된 수주 조회
    try:
        pos = PO.objects.all().order_by('-received_at')[:100]
    except (ProgrammingError, OperationalError):
        pos = []
    
    # FCMS CDC에서 진척 정보 조회
    order_list = []
    for po in pos:
        # FCMS에서 해당 PO의 생산 진척 조회
        try:
            progress_summary = FcmsRepository.get_production_summary_by_customer_order_no(
                po.customer_order_no
            )
        except Exception as e:
            progress_summary = {
                'customer_order_no': po.customer_order_no,
                'products': {},
                'total_arrival_count': 0,
            }
        
        # 제품코드별 합계 계산 (새 구조)
        products_data = progress_summary.get('products', {})
        instruction_count = 0
        arrival_count = progress_summary.get('total_arrival_count', 0)
        
        for trade_code, product_info in products_data.items():
            instruction_count += product_info.get('total_instruction_count', 0)
        
        # 진척률 계산
        order_qty = po.total_qty
        
        if order_qty > 0:
            progress_percent = round((instruction_count / order_qty) * 100, 1)
            progress_percent = min(progress_percent, 100)  # 100% 초과 방지
        else:
            progress_percent = 0
        
        order_list.append({
            'po': po,
            'order_qty': order_qty,
            'arrival_count': arrival_count,
            'instruction_count': instruction_count,
            'progress_percent': progress_percent,
            'products': products_data,
        })
    
    # 통계 계산
    stats = {
        'total': len(order_list),
        'in_progress': sum(1 for item in order_list if 0 < item['progress_percent'] < 100),
        'completed': sum(1 for item in order_list if item['progress_percent'] >= 100),
        'linked': sum(1 for item in order_list if item['arrival_count'] > 0),
        'unlinked': sum(1 for item in order_list if item['arrival_count'] == 0),
    }
    
    context = {
        'order_list': order_list,
        'stats': stats,
    }
    
    return render(request, 'orders/order_management.html', context)


def order_management_detail(request, customer_order_no):
    """
    수주관리표 상세 (단일 수주의 생산 진척)
    
    핵심 구조:
    - PO 품목(제품코드)별 수주수량과 발행현황 비교
    - 각 제품코드 아래에 FCMS 이동서 목록
    - 각 이동서의 진척 상태 (충전/입고/출하)
    """
    po = get_object_or_404(PO, customer_order_no=customer_order_no)
    
    # FCMS에서 해당 PO의 상세 진척 조회 (제품코드별 그룹화)
    try:
        progress_summary = FcmsRepository.get_production_summary_by_customer_order_no(
            customer_order_no
        )
    except Exception as e:
        progress_summary = {
            'customer_order_no': customer_order_no,
            'products': {},
            'total_arrival_count': 0,
        }
    
    # PO 품목별 진척률 계산
    items_with_progress = []
    products_data = progress_summary.get('products', {})
    
    for item in po.items.all():
        item_data = {
            'item': item,
            'ordered_qty': item.qty,
            'issued_qty': 0,
            'filled_qty': 0,
            'warehoused_qty': 0,
            'shipped_qty': 0,
            'remaining_qty': item.qty,
            'progress_percent': 0,
            'orders': [],
        }
        
        # 해당 제품코드의 FCMS 데이터가 있는 경우
        if item.trade_condition_code in products_data:
            product_info = products_data[item.trade_condition_code]
            item_data['issued_qty'] = product_info.get('total_instruction_count', 0)
            item_data['orders'] = product_info.get('orders', [])
            
            # 잔여수량 계산
            item_data['remaining_qty'] = max(0, item.qty - item_data['issued_qty'])
            
            # 진척률 계산 (발행 기준)
            if item.qty > 0:
                item_data['progress_percent'] = min(100, int(item_data['issued_qty'] / item.qty * 100))
        
        items_with_progress.append(item_data)
    
    context = {
        'po': po,
        'progress_summary': progress_summary,
        'items_with_progress': items_with_progress,
    }
    
    return render(request, 'orders/order_management_detail.html', context)


@require_POST
def sync_fcms_progress(request, customer_order_no):
    """
    FCMS 생산 진척 정보 동기화
    
    CDC에서 데이터 조회하여 FCMSProductionProgress 모델에 저장
    """
    po = get_object_or_404(PO, customer_order_no=customer_order_no)
    
    try:
        # FCMS에서 진척 정보 조회
        progress_summary = FcmsRepository.get_production_summary_by_customer_order_no(
            customer_order_no
        )
        
        # 기존 데이터 삭제 후 재생성
        FCMSProductionProgress.objects.filter(po=po).delete()
        
        sync_count = 0
        for order in progress_summary.get('orders', []):
            # TR_ORDERS에 품목 정보가 포함되어 있음 (별도 items 없음)
            FCMSProductionProgress.objects.create(
                po=po,
                arrival_shipping_no=order.get('arrival_shipping_no', ''),
                item_name=order.get('item_name', ''),
                packing_name=order.get('packing_name', ''),
                trade_condition_code=order.get('trade_condition_code', ''),
                selection_pattern_code=order.get('selection_pattern_code', ''),
                instruction_quantity=order.get('instruction_quantity'),
                instruction_count=order.get('instruction_count', 0),
                filling_threshold=order.get('filling_threshold'),
                filled_count=0,
            )
            sync_count += 1
        
        # 상태 자동 업데이트
        if sync_count > 0 and po.status in ('DRAFT', 'IN_PROGRESS', 'GUIDED'):
            po.status = 'MATCHED'
            po.save(update_fields=['status'])
            messages.success(request, f'FCMS 생산 진척 정보가 동기화되었습니다. ({sync_count}건) - 상태: FCMS매칭완료')
        else:
            messages.success(request, f'FCMS 생산 진척 정보가 동기화되었습니다. ({sync_count}건)')
    except Exception as e:
        messages.error(request, f'FCMS 동기화 실패: {e}')
    
    return redirect('orders:management_detail', customer_order_no=customer_order_no)


@require_POST
def sync_all_fcms_progress(request):
    """
    모든 수주의 FCMS 생산 진척 정보 일괄 동기화
    """
    # 모든 수주 동기화
    pos = PO.objects.all()
    
    total_synced = 0
    matched_count = 0
    completed_count = 0
    error_count = 0
    
    for po in pos:
        try:
            progress_summary = FcmsRepository.get_production_summary_by_customer_order_no(
                po.customer_order_no
            )
            
            # 기존 데이터 삭제 후 재생성
            FCMSProductionProgress.objects.filter(po=po).delete()
            
            sync_count = 0
            total_ordered = 0
            total_issued = 0
            products_data = progress_summary.get('products', {})
            
            for trade_code, product_info in products_data.items():
                total_issued += product_info.get('total_instruction_count', 0)
                for order in product_info.get('orders', []):
                    FCMSProductionProgress.objects.create(
                        po=po,
                        arrival_shipping_no=order.get('arrival_shipping_no', ''),
                        item_name=order.get('item_name', ''),
                        packing_name=order.get('packing_name', ''),
                        trade_condition_code=order.get('trade_condition_code', ''),
                        selection_pattern_code=order.get('selection_pattern_code', ''),
                        instruction_quantity=order.get('instruction_quantity'),
                        instruction_count=order.get('instruction_count', 0),
                        filling_threshold=order.get('filling_threshold'),
                        filled_count=0,
                    )
                    sync_count += 1
            
            total_synced += sync_count
            
            # 수주량 계산
            total_ordered = sum(item.qty for item in po.items.all())
            
            # 상태 자동 업데이트
            if sync_count > 0:
                if total_ordered > 0 and total_issued >= total_ordered:
                    # 수주량 이상 발행되면 완료
                    if po.status != 'COMPLETED':
                        po.status = 'COMPLETED'
                        po.save(update_fields=['status'])
                        completed_count += 1
                elif po.status in ('DRAFT', 'IN_PROGRESS', 'GUIDED'):
                    po.status = 'MATCHED'
                    po.save(update_fields=['status'])
                    matched_count += 1
                
        except Exception as e:
            error_count += 1
            last_error = f"{po.customer_order_no}: {str(e)[:100]}"
            print(f"[Sync Error] {po.customer_order_no}: {e}")
    
    result_parts = [f'{len(pos)}건 수주']
    if matched_count > 0:
        result_parts.append(f'{matched_count}건 매칭')
    if completed_count > 0:
        result_parts.append(f'{completed_count}건 완료')
    result_parts.append(f'{total_synced}건 이동서')
    if error_count > 0:
        result_parts.append(f'{error_count}건 오류')
    
    result_msg = ', '.join(result_parts)
    
    if error_count > 0:
        messages.warning(request, f'FCMS 동기화 완료: {result_msg}')
        if 'last_error' in locals():
            messages.error(request, f'마지막 오류: {last_error}')
    else:
        messages.success(request, f'FCMS 전체 동기화 완료: {result_msg}')
    
    return redirect('orders:management')


# ============================================
# FCMS 진척 API (AJAX용)
# ============================================

@require_GET
def api_fcms_progress(request, customer_order_no):
    """
    FCMS 생산 진척 API
    
    GET /orders/api/fcms-progress/<customer_order_no>/
    """
    try:
        progress_summary = FcmsRepository.get_production_summary_by_customer_order_no(
            customer_order_no
        )
        
        # 각 도착출하번호별 충전 진척도 추가
        for order in progress_summary.get('orders', []):
            filling_progress = FcmsRepository.get_filling_progress_by_arrival_shipping_no(
                order['arrival_shipping_no']
            )
            order['filled_count'] = filling_progress.get('filled_count', 0)
        
        # Decimal을 float로 변환
        progress_summary['total_instruction_quantity'] = float(
            progress_summary.get('total_instruction_quantity', 0)
        )
        
        return JsonResponse(progress_summary)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================
# 가발행 이동서 관리
# ============================================

def planned_move_list(request, customer_order_no):
    """
    가발행 이동서 목록 (수주별)
    """
    po = get_object_or_404(PO, customer_order_no=customer_order_no)
    
    # URL 파라미터로 미리 선택할 품목
    preselect_item_id = request.GET.get('item')
    preselect_code = request.GET.get('code')
    
    # 가발행 목록
    planned_moves = po.planned_moves.all()
    
    # 제품코드별 진척 계산
    items_progress = []
    for item in po.items.all():
        # 해당 제품코드의 가발행 수량 합계
        item_planned = sum(
            pm.planned_qty for pm in planned_moves 
            if pm.trade_condition_code == item.trade_condition_code
        )
        remaining = item.qty - item_planned
        progress = int(item_planned / item.qty * 100) if item.qty > 0 else 0
        
        items_progress.append({
            'item': item,
            'order_qty': item.qty,
            'planned_qty': item_planned,
            'remaining_qty': remaining,
            'progress': min(progress, 100),
        })
    
    # FCMS 최신 번호 및 다음 번호 추천
    try:
        latest_no = FcmsRepository.get_latest_arrival_shipping_no()
        next_no = FcmsRepository.get_next_move_no()
        year_range = FcmsRepository.get_move_no_range_for_year()
    except Exception:
        latest_no = None
        next_no = None
        year_range = {'min': None, 'max': None, 'count': 0}
    
    context = {
        'po': po,
        'planned_moves': planned_moves,
        'items_progress': items_progress,
        'latest_no': latest_no,
        'next_no': next_no,
        'year_range': year_range,
        'preselect_item_id': preselect_item_id,
        'preselect_code': preselect_code,
    }
    
    return render(request, 'orders/planned_move_list.html', context)


@require_POST
def planned_move_create(request, customer_order_no):
    """
    가발행 이동서 등록 (일괄 생성 지원)
    """
    import re
    
    po = get_object_or_404(PO, customer_order_no=customer_order_no)
    
    # 폼 데이터
    planned_move_no = request.POST.get('planned_move_no', '').strip()
    planned_qty = request.POST.get('planned_qty', 0)
    batch_count = request.POST.get('batch_count', 1)
    po_item_id = request.POST.get('po_item_id')
    trade_condition_code = request.POST.get('trade_condition_code', '')
    gas_name = request.POST.get('gas_name', '')
    filling_plan_date = request.POST.get('filling_plan_date')
    shipping_plan_date = request.POST.get('shipping_plan_date')
    remarks = request.POST.get('remarks', '')
    
    if not planned_move_no:
        messages.error(request, '이동서번호를 입력해주세요.')
        return redirect('orders:planned_moves', customer_order_no=customer_order_no)
    
    try:
        batch_count = int(batch_count)
        batch_count = min(max(batch_count, 1), 20)  # 1~20 제한
    except (ValueError, TypeError):
        batch_count = 1
    
    try:
        planned_qty = int(planned_qty) if planned_qty else 0
    except (ValueError, TypeError):
        planned_qty = 0
    
    # 수주품목 연결
    po_item = None
    if po_item_id:
        try:
            po_item = POItem.objects.get(pk=po_item_id, po=po)
            trade_condition_code = po_item.trade_condition_code
            gas_name = po_item.gas_name
        except POItem.DoesNotExist:
            pass
    
    # 중량 계산
    planned_weight = None
    if po_item and po_item.filling_weight and planned_qty:
        try:
            planned_weight = po_item.filling_weight * planned_qty
        except (ValueError, TypeError):
            pass
    
    # 순번 계산
    last_seq = po.planned_moves.order_by('-sequence').first()
    next_seq = (last_seq.sequence + 1) if last_seq else 1
    
    # 번호 파싱 (FP25XXXXXX 형식)
    match = re.match(r'^([A-Z]+)(\d+)$', planned_move_no)
    if match:
        prefix = match.group(1)
        start_num = int(match.group(2))
        num_len = len(match.group(2))
    else:
        # 파싱 실패 시 단일 생성
        prefix = None
        start_num = 0
        num_len = 0
        batch_count = 1
    
    created_count = 0
    created_nos = []
    
    for i in range(batch_count):
        if prefix:
            current_no = f"{prefix}{str(start_num + i).zfill(num_len)}"
        else:
            current_no = planned_move_no if i == 0 else f"{planned_move_no}_{i+1}"
        
        # 중복 확인 (CYNOW 내)
        if PlannedMoveReport.objects.filter(planned_move_no=current_no).exists():
            messages.warning(request, f'이미 가발행된 번호 건너뜀: {current_no}')
            continue
        
        # 생성
        PlannedMoveReport.objects.create(
            po=po,
            planned_move_no=current_no,
            sequence=next_seq + i,
            po_item=po_item,
            trade_condition_code=trade_condition_code,
            gas_name=gas_name,
            planned_qty=planned_qty,
            planned_weight=planned_weight,
            filling_plan_date=filling_plan_date if filling_plan_date else None,
            shipping_plan_date=shipping_plan_date if shipping_plan_date else None,
            remarks=remarks,
            created_by=request.user if request.user.is_authenticated else None,
        )
        created_count += 1
        created_nos.append(current_no)
    
    if created_count > 1:
        messages.success(request, f'{created_count}건 가발행 완료: {created_nos[0]} ~ {created_nos[-1]}')
    elif created_count == 1:
        messages.success(request, f'가발행 등록: {created_nos[0]}')
    else:
        messages.error(request, '가발행 등록 실패')
    
    return redirect('orders:planned_moves', customer_order_no=customer_order_no)


@require_POST
def planned_move_delete(request, pk):
    """
    가발행 이동서 삭제
    """
    planned_move = get_object_or_404(PlannedMoveReport, pk=pk)
    customer_order_no = planned_move.po.customer_order_no
    move_no = planned_move.planned_move_no
    
    planned_move.delete()
    
    messages.success(request, f'가발행 이동서가 삭제되었습니다: {move_no}')
    return redirect('orders:planned_moves', customer_order_no=customer_order_no)


@require_POST
def planned_move_match(request, pk):
    """
    가발행 이동서 FCMS 매칭 확인
    """
    planned_move = get_object_or_404(PlannedMoveReport, pk=pk)
    
    try:
        # FCMS에서 해당 번호 조회
        fcms_order = FcmsRepository.get_order_by_arrival_shipping_no(
            planned_move.planned_move_no
        )
        
        if fcms_order:
            planned_move.status = 'MATCHED'
            planned_move.fcms_matched_no = fcms_order.get('arrival_shipping_no', '')
            planned_move.fcms_matched_at = timezone.now()
            planned_move.fcms_instruction_count = fcms_order.get('total_instruction_count', 0)
            planned_move.save()
            
            messages.success(
                request, 
                f'FCMS 매칭 완료: {planned_move.planned_move_no} '
                f'(지시수량: {planned_move.fcms_instruction_count}병)'
            )
        else:
            planned_move.status = 'PENDING'
            planned_move.save()
            messages.info(request, f'FCMS에 아직 입력되지 않았습니다: {planned_move.planned_move_no}')
    
    except Exception as e:
        messages.error(request, f'매칭 확인 실패: {e}')
    
    return redirect('orders:planned_moves', customer_order_no=planned_move.po.customer_order_no)


@require_POST
def planned_move_match_all(request, customer_order_no):
    """
    수주의 모든 가발행 이동서 FCMS 매칭 확인
    """
    po = get_object_or_404(PO, customer_order_no=customer_order_no)
    
    matched_count = 0
    pending_count = 0
    
    for planned_move in po.planned_moves.filter(status__in=['PLANNED', 'PENDING']):
        try:
            fcms_order = FcmsRepository.get_order_by_arrival_shipping_no(
                planned_move.planned_move_no
            )
            
            if fcms_order:
                planned_move.status = 'MATCHED'
                planned_move.fcms_matched_no = fcms_order.get('arrival_shipping_no', '')
                planned_move.fcms_matched_at = timezone.now()
                planned_move.fcms_instruction_count = fcms_order.get('total_instruction_count', 0)
                planned_move.save()
                matched_count += 1
            else:
                planned_move.status = 'PENDING'
                planned_move.save()
                pending_count += 1
        except Exception:
            pending_count += 1
    
    messages.success(
        request, 
        f'매칭 확인 완료: {matched_count}건 매칭, {pending_count}건 대기'
    )
    
    return redirect('orders:planned_moves', customer_order_no=customer_order_no)


# ============================================
# 가발행 이동서 API
# ============================================

@require_GET
def api_next_move_no(request):
    """
    다음 이동서번호 추천 API
    
    GET /orders/api/next-move-no/
    """
    try:
        next_no = FcmsRepository.get_next_move_no()
        latest_no = FcmsRepository.get_latest_arrival_shipping_no()
        
        # 중복 확인 (CYNOW 가발행)
        is_used = PlannedMoveReport.objects.filter(planned_move_no=next_no).exists()
        
        return JsonResponse({
            'next_no': next_no,
            'latest_no': latest_no,
            'is_used': is_used,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
def api_check_move_no(request):
    """
    이동서번호 중복 확인 API
    
    GET /orders/api/check-move-no/?no=FP250001
    """
    move_no = request.GET.get('no', '').strip()
    
    if not move_no:
        return JsonResponse({'error': '번호를 입력해주세요.'}, status=400)
    
    try:
        # CYNOW 가발행 확인
        cynow_exists = PlannedMoveReport.objects.filter(planned_move_no=move_no).exists()
        
        # FCMS 확인
        fcms_exists = FcmsRepository.check_move_no_exists(move_no)
        
        return JsonResponse({
            'move_no': move_no,
            'cynow_exists': cynow_exists,
            'fcms_exists': fcms_exists,
            'available': not cynow_exists and not fcms_exists,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_GET
def api_move_report_detail(request, move_report_no):
    """
    이동서 상세 정보 및 용기번호 리스트 API
    
    GET /orders/api/move-report/<move_report_no>/
    """
    try:
        result = FcmsRepository.get_move_report_detail(move_report_no)
        
        if not result:
            return JsonResponse({'error': '이동서를 찾을 수 없습니다.'}, status=404)
        
        # 날짜 필드 직렬화
        move_report = result['move_report']
        for key in ['filling_date', 'shipping_date', 'delivery_date', 
                    'filling_plan_date', 'warehousing_plan_date', 'shipping_plan_date']:
            if move_report.get(key):
                move_report[key] = move_report[key].strftime('%Y-%m-%d')
        
        for cyl in result['cylinders']:
            if cyl.get('last_move_date'):
                cyl['last_move_date'] = cyl['last_move_date'].strftime('%Y-%m-%d')
        
        return JsonResponse(result)
    except Exception as e:
        logger.error(f"이동서 상세 API 오류: {e}")
        return JsonResponse({'error': str(e)}, status=500)


