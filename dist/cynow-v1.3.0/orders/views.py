"""
PO 관리 View

기본 CRUD 및 비즈니스 로직 연동
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import PO, POItem, ReservedDocNo, OrphanFcmsDoc
from .services import ReservationService, MatchingService, MonitoringService
from .repositories import PORepository
from .forms import POForm, POItemFormSet


# @login_required  # 임시로 주석 처리 (테스트용)
def po_list(request):
    """PO 리스트"""
    filters = {}
    
    # 필터 파라미터
    if request.GET.get('status'):
        filters['status'] = request.GET.get('status')
    
    if request.GET.get('supplier_user_code'):
        filters['supplier_user_code'] = request.GET.get('supplier_user_code')
    
    if request.GET.get('needs_review') == '1':
        filters['needs_review'] = True
    
    # PO 조회
    pos = PORepository.get_po_list(filters=filters, limit=100)
    
    # 통계
    stats = PORepository.get_po_statistics()
    
    context = {
        'pos': pos,
        'stats': stats,
        'filters': filters,
    }
    
    return render(request, 'orders/po_list.html', context)


# @login_required  # 임시로 주석 처리 (테스트용)
def po_detail(request, customer_order_no):
    """PO 상세"""
    po = get_object_or_404(PO, customer_order_no=customer_order_no)
    
    # 예약번호
    reservations = ReservationService.get_reserved_numbers_for_po(po)
    
    # 진행 현황
    progress = MonitoringService.get_latest_progress(po)
    
    context = {
        'po': po,
        'reservations': reservations,
        'progress': progress,
    }
    
    return render(request, 'orders/po_detail.html', context)


# @login_required  # 임시로 주석 처리 (테스트용)
def po_create(request):
    """PO 생성"""
    if request.method == 'POST':
        form = POForm(request.POST)
        formset = POItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            # PO 저장
            po = form.save(commit=False)
            
            # 생성자 설정
            if request.user.is_authenticated:
                po.created_by = request.user
            
            po.save()
            
            # PO 아이템 저장
            formset.instance = po
            formset.save()
            
            messages.success(request, f'수주 {po.customer_order_no}가 생성되었습니다.')
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


@login_required
def po_edit(request, customer_order_no):
    """PO 수정"""
    po = get_object_or_404(PO, customer_order_no=customer_order_no)
    
    if request.method == 'POST':
        form = POForm(request.POST, instance=po)
        formset = POItemFormSet(request.POST, instance=po)
        
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            
            messages.success(request, f'수주 {po.customer_order_no}가 수정되었습니다.')
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


@login_required
@require_POST
def po_delete(request, customer_order_no):
    """PO 삭제 (상태 변경)"""
    po = get_object_or_404(PO, customer_order_no=customer_order_no)
    po.status = 'CANCELED'
    po.save()
    
    messages.success(request, 'PO가 취소되었습니다.')
    return redirect('orders:list')


@login_required
@require_POST
def reserve_doc_no(request, customer_order_no):
    """예약번호 생성"""
    po = get_object_or_404(PO, customer_order_no=customer_order_no)
    doc_type = request.POST.get('doc_type', 'ARRIVAL_SHIPPING')
    
    try:
        reserved = ReservationService.generate_doc_no(doc_type, po)
        messages.success(request, f'예약번호가 생성되었습니다: {reserved.reserved_no}')
    except ValueError as e:
        messages.error(request, f'예약번호 생성 실패: {e}')
    
    return redirect('orders:detail', customer_order_no=customer_order_no)


@login_required
@require_POST
def release_reservation(request, reservation_id):
    """예약 해제"""
    reserved = get_object_or_404(ReservedDocNo, id=reservation_id)
    ReservationService.release_reservation(reserved)
    
    messages.success(request, '예약이 해제되었습니다.')
    return redirect('orders:detail', customer_order_no=reserved.po.customer_order_no)


@login_required
@require_POST
def check_match(request, customer_order_no):
    """매칭 확인"""
    po = get_object_or_404(PO, customer_order_no=customer_order_no)
    
    result = MatchingService.check_po_match(po)
    
    messages.success(
        request,
        f'매칭 확인 완료: {result["matched_count"]}건 매칭, {result["not_entered_count"]}건 미입력'
    )
    
    return redirect('orders:detail', customer_order_no=customer_order_no)


@login_required
def manual_match(request, customer_order_no):
    """수동 매칭"""
    po = get_object_or_404(PO, customer_order_no=customer_order_no)
    
    if request.method == 'POST':
        fcms_doc_no = request.POST.get('fcms_doc_no')
        doc_type = request.POST.get('doc_type')
        note = request.POST.get('note', '')
        
        MatchingService.manual_match(po, fcms_doc_no, doc_type, request.user, note)
        
        messages.success(request, '수동 매칭이 완료되었습니다.')
        return redirect('orders:detail', customer_order_no=customer_order_no)
    
    # 매칭 후보 추천
    candidates = MatchingService.suggest_mismatch_candidates(po)
    
    context = {
        'po': po,
        'candidates': candidates,
    }
    
    return render(request, 'orders/manual_match.html', context)


@login_required
def po_progress(request, customer_order_no):
    """진행 현황 상세"""
    po = get_object_or_404(PO, customer_order_no=customer_order_no)
    
    progress = MonitoringService.get_latest_progress(po)
    
    context = {
        'po': po,
        'progress': progress,
    }
    
    return render(request, 'orders/po_progress.html', context)


@login_required
@require_POST
def update_progress(request, customer_order_no):
    """진행 현황 갱신"""
    po = get_object_or_404(PO, customer_order_no=customer_order_no)
    
    MonitoringService.update_po_progress(po)
    
    messages.success(request, '진행 현황이 갱신되었습니다.')
    return redirect('orders:detail', customer_order_no=customer_order_no)


@login_required
def backfill_review(request):
    """역수입 데이터 검토"""
    # 검토 필요 PO
    review_pos = PORepository.get_pos_needing_review()
    
    # 고아 문서
    orphans = OrphanFcmsDoc.objects.filter(is_resolved=False)[:50]
    
    context = {
        'review_pos': review_pos,
        'orphans': orphans,
    }
    
    return render(request, 'orders/backfill_review.html', context)


@login_required
@require_POST
def approve_backfill(request, po_id):
    """역수입 PO 승인"""
    po = get_object_or_404(PO, id=po_id)
    
    po.needs_review = False
    po.review_note = request.POST.get('note', '')
    po.save()
    
    messages.success(request, 'PO가 승인되었습니다.')
    return redirect('orders:backfill_review')


@login_required
@require_POST
def match_orphan(request, orphan_id):
    """고아 문서 매칭"""
    orphan = get_object_or_404(OrphanFcmsDoc, id=orphan_id)
    
    action = request.POST.get('action')
    
    if action == 'match':
        # 기존 PO와 매칭
        po_id = request.POST.get('po_id')
        if po_id:
            po = get_object_or_404(PO, id=po_id)
            orphan.suggested_po = po
            orphan.is_resolved = True
            orphan.save()
            
            messages.success(request, '고아 문서가 PO와 매칭되었습니다.')
    
    elif action == 'ignore':
        # 무시
        orphan.is_resolved = True
        orphan.resolved_note = '무시 (정상 문서로 판단)'
        orphan.save()
        
        messages.success(request, '고아 문서가 무시 처리되었습니다.')
    
    return redirect('orders:backfill_review')


@login_required
def manufacturing_schedule(request):
    """제조부 납기/우선순위 화면"""
    days_ahead = int(request.GET.get('days', 30))
    
    pos = PORepository.get_manufacturing_schedule(days_ahead=days_ahead)
    
    # 각 PO의 진행 현황 추가
    po_list = []
    for po in pos:
        progress = MonitoringService.get_latest_progress(po)
        po_list.append({
            'po': po,
            'progress': progress,
        })
    
    context = {
        'po_list': po_list,
        'days_ahead': days_ahead,
    }
    
    return render(request, 'orders/manufacturing_schedule.html', context)

