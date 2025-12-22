"""
수주 페이지 뷰

목적:
A) 고객 이메일로 받은 수주 정보 입력
B) 이동서번호 가이드 표시
C) 진행 현황 모니터링
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Sum
from django.db.utils import ProgrammingError, OperationalError

from .models import PO, POItem, MoveNoGuide, FCMSMatchStatus
from .forms import POForm, POItemFormSet


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
    
    # 비로그인 사용자는 에러 대신 빈 화면(안내)로 처리
    # - 메뉴 클릭 시 서버에러(500) 방지
    if not request.user.is_authenticated:
        context = {
            "po_list": [],
            "current_status": "",
            "current_supplier": "",
            "status_choices": PO.STATUS_CHOICES,
            "error_message": "PO 관리는 로그인 후 사용 가능합니다.",
        }
        return render(request, "orders/po_list.html", context)

    try:
        pos = PO.objects.all()
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
    
    # 이동서번호 가이드
    guides = po.move_guides.all()
    
    # FCMS 매칭 상태
    try:
        match_status = po.fcms_match_status
    except FCMSMatchStatus.DoesNotExist:
        match_status = None
    
    context = {
        'po': po,
        'items': items,
        'guides': guides,
        'match_status': match_status,
    }
    
    return render(request, 'orders/po_detail.html', context)


def po_create(request):
    """수주 생성"""
    if request.method == 'POST':
        form = POForm(request.POST)
        formset = POItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            # PO 저장
            po = form.save(commit=False)
            
            # 작성자 설정
            if request.user.is_authenticated:
                po.created_by = request.user
            
            po.save()
            
            # 품목 저장
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


def po_edit(request, customer_order_no):
    """수주 수정"""
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
    
    # TODO: FCMS CDC 조회 로직 구현
    # TR_ORDERS.ARRIVAL_SHIPPING_NO 확인
    # TR_MOVE_REPORTS.MOVE_REPORT_NO 확인
    
    # 임시: 매칭 상태 생성/업데이트
    match_status, created = FCMSMatchStatus.objects.get_or_create(
        po=po,
        defaults={
            'match_state': 'NOT_ENTERED',
            'note': 'CDC 조회 기능 구현 예정'
        }
    )
    
    if not created:
        match_status.match_state = 'NOT_ENTERED'
        match_status.note = 'CDC 조회 기능 구현 예정'
        match_status.save()
    
    messages.info(request, 'FCMS 매칭 확인이 완료되었습니다. (CDC 조회 기능 구현 예정)')
    return redirect('orders:detail', customer_order_no=customer_order_no)


