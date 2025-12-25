"""
견적서/전표 뷰

DOCX 파일 생성 및 다운로드를 처리합니다.
"""
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.shortcuts import render, get_object_or_404, redirect
from django.http import FileResponse, HttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.db import models

from .models import Quote, QuoteItem, Customer, DocumentTemplate, CompanyInfo
from .services.docx_generator import (
    DocxGenerator,
    QuoteDocxGenerator,
    build_quote_context_from_db,
    generate_price_list_from_products,
)


@login_required
def quote_list(request):
    """견적서 목록"""
    quotes = Quote.objects.select_related('customer', 'created_by').all()
    
    # 상태 필터
    status = request.GET.get('status')
    if status:
        quotes = quotes.filter(status=status)
    
    # 검색
    search = request.GET.get('q')
    if search:
        quotes = quotes.filter(
            models.Q(quote_no__icontains=search) |
            models.Q(title__icontains=search) |
            models.Q(customer__name__icontains=search)
        )
    
    context = {
        'quotes': quotes[:50],
        'status_choices': Quote.STATUS_CHOICES,
    }
    return render(request, 'voucher/quote_list.html', context)


@login_required
def quote_detail(request, pk):
    """견적서 상세"""
    quote = get_object_or_404(
        Quote.objects.prefetch_related('items'),
        pk=pk
    )
    context = {
        'quote': quote,
        'items': quote.items.all(),
    }
    return render(request, 'voucher/quote_detail.html', context)


@login_required
def quote_download(request, pk):
    """
    견적서 DOCX 다운로드
    
    1. DB에서 견적서 조회
    2. 템플릿 컨텍스트 구성
    3. DOCX 생성
    4. FileResponse로 다운로드
    """
    quote = get_object_or_404(Quote.objects.prefetch_related('items'), pk=pk)
    
    try:
        # 템플릿 조회
        template = DocumentTemplate.get_default_template('QUOTE')
        template_name = template.filename if template else 'offer_template.docx'
        
        # 컨텍스트 구성
        context_data = build_quote_context_from_db(pk)
        
        # DOCX 생성
        generator = QuoteDocxGenerator(template_name)
        output_path = generator.generate_quote(
            quote_info=context_data['quote_info'],
            supplier_info=context_data['supplier_info'],
            customer_info=context_data['customer_info'],
            items=context_data['items'],
            footer_info=context_data['footer_info'],
            output_filename=f"견적서_{quote.quote_no}.docx"
        )
        
        # 파일 응답
        response = FileResponse(
            open(output_path, 'rb'),
            as_attachment=True,
            filename=f"견적서_{quote.quote_no}.docx"
        )
        response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        
        return response
        
    except FileNotFoundError as e:
        messages.error(request, f"템플릿 파일을 찾을 수 없습니다: {e}")
        return redirect('voucher:quote_detail', pk=pk)
    except Exception as e:
        messages.error(request, f"문서 생성 오류: {e}")
        return redirect('voucher:quote_detail', pk=pk)


@login_required
def price_list_download(request):
    """
    단가표 DOCX 다운로드
    
    쿼리 파라미터:
    - year: 대상 년도 (기본: 현재년도)
    """
    year = request.GET.get('year')
    if year:
        try:
            year = int(year)
        except ValueError:
            year = date.today().year
    else:
        year = date.today().year
    
    try:
        # DOCX 생성
        output_path = generate_price_list_from_products(year)
        
        # 파일 응답
        filename = f"{year}년단가표_KDKK.docx"
        response = FileResponse(
            open(output_path, 'rb'),
            as_attachment=True,
            filename=filename
        )
        response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        
        return response
        
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f"문서 생성 오류: {e}"}, status=500)


@login_required
def generate_quote_preview(request, pk):
    """
    견적서 미리보기 (JSON 반환)
    
    DOCX 생성 전 데이터 확인용
    """
    quote = get_object_or_404(Quote.objects.prefetch_related('items'), pk=pk)
    
    context = build_quote_context_from_db(pk)
    
    # JSON 직렬화 가능하게 변환
    return JsonResponse({
        'quote_no': quote.quote_no,
        'title': quote.title,
        'item_count': len(context['items']),
        'preview': context,
    })


# ============================================
# API 엔드포인트 (외부 시스템 연동용)
# ============================================

@login_required
def api_generate_docx(request):
    """
    API: DOCX 생성
    
    POST /voucher/api/generate/
    Body (JSON):
    {
        "template_type": "QUOTE",
        "quote_id": 123
    }
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)
    
    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    template_type = data.get('template_type', 'QUOTE')
    quote_id = data.get('quote_id')
    
    if not quote_id:
        return JsonResponse({'error': 'quote_id required'}, status=400)
    
    try:
        context = build_quote_context_from_db(quote_id)
        
        template = DocumentTemplate.get_default_template(template_type)
        template_name = template.filename if template else 'offer_template.docx'
        
        generator = QuoteDocxGenerator(template_name)
        output_path = generator.generate_quote(
            quote_info=context['quote_info'],
            supplier_info=context['supplier_info'],
            customer_info=context['customer_info'],
            items=context['items'],
            footer_info=context['footer_info'],
        )
        
        return JsonResponse({
            'success': True,
            'file_path': str(output_path),
            'download_url': f"/voucher/quote/{quote_id}/download/",
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================
# 단가표 직접 생성 (제품코드 DB 기반)
# ============================================

@login_required
def generate_price_list(request):
    """
    단가표 생성 페이지
    """
    if request.method == 'POST':
        year = request.POST.get('year')
        try:
            year = int(year)
            output_path = generate_price_list_from_products(year)
            messages.success(request, f"{year}년 단가표가 생성되었습니다: {output_path}")
            
            # 다운로드 리다이렉트
            return redirect(f"/voucher/price-list/download/?year={year}")
            
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f"오류: {e}")
    
    current_year = date.today().year
    years = [current_year + 1, current_year, current_year - 1]
    
    context = {
        'years': years,
    }
    return render(request, 'voucher/price_list_form.html', context)


# ============================================
# 견적서 생성/수정
# ============================================

@login_required
def quote_create(request):
    """견적서 생성"""
    if request.method == 'POST':
        # 견적번호 중복 체크
        quote_no = request.POST.get('quote_no')
        if Quote.objects.filter(quote_no=quote_no).exists():
            messages.error(request, f"견적번호 {quote_no}가 이미 존재합니다.")
            return redirect('voucher:quote_create')
        
        # 견적서 생성
        quote = Quote(
            quote_no=quote_no,
            title=request.POST.get('title'),
            quote_date=request.POST.get('quote_date') or date.today(),
            valid_until=request.POST.get('valid_until') or None,
            status=request.POST.get('status', 'DRAFT'),
            default_currency=request.POST.get('default_currency', 'KRW'),
            
            # 거래처
            customer_id=request.POST.get('customer') or None,
            customer_address=request.POST.get('customer_address'),
            customer_ceo=request.POST.get('customer_ceo'),
            customer_tel=request.POST.get('customer_tel'),
            customer_manager=request.POST.get('customer_manager'),
            customer_manager_tel=request.POST.get('customer_manager_tel'),
            customer_manager_email=request.POST.get('customer_manager_email') or None,
            
            # 공급처
            supplier_name=request.POST.get('supplier_name'),
            supplier_address=request.POST.get('supplier_address'),
            supplier_ceo=request.POST.get('supplier_ceo'),
            supplier_tel=request.POST.get('supplier_tel'),
            supplier_fax=request.POST.get('supplier_fax'),
            supplier_manager=request.POST.get('supplier_manager'),
            
            # 하단 정보
            valid_period=request.POST.get('valid_period'),
            trade_terms=request.POST.get('trade_terms'),
            bank_account=request.POST.get('bank_account'),
            note=request.POST.get('note'),
            
            created_by=request.user,
        )
        quote.save()
        
        messages.success(request, f"견적서 {quote.quote_no}가 생성되었습니다.")
        return redirect('voucher:quote_detail', pk=quote.pk)
    
    # 견적번호 자동 생성
    suggested_quote_no = Quote().generate_quote_no()
    
    context = {
        'quote': None,
        'suggested_quote_no': suggested_quote_no,
        'today': date.today().strftime('%Y-%m-%d'),
        'status_choices': Quote.STATUS_CHOICES,
        'currency_choices': Quote.CURRENCY_CHOICES,
        'customers': Customer.objects.filter(is_active=True).order_by('name'),
    }
    return render(request, 'voucher/quote_form.html', context)


@login_required
def quote_edit(request, pk):
    """견적서 수정"""
    quote = get_object_or_404(Quote, pk=pk)
    
    if request.method == 'POST':
        # 견적번호 중복 체크 (자기 자신 제외)
        quote_no = request.POST.get('quote_no')
        if Quote.objects.filter(quote_no=quote_no).exclude(pk=pk).exists():
            messages.error(request, f"견적번호 {quote_no}가 이미 존재합니다.")
            return redirect('voucher:quote_edit', pk=pk)
        
        # 업데이트
        quote.quote_no = quote_no
        quote.title = request.POST.get('title')
        quote.quote_date = request.POST.get('quote_date') or date.today()
        quote.valid_until = request.POST.get('valid_until') or None
        quote.status = request.POST.get('status', 'DRAFT')
        quote.default_currency = request.POST.get('default_currency', 'KRW')
        
        # 거래처
        customer_id = request.POST.get('customer')
        quote.customer_id = customer_id if customer_id else None
        quote.customer_address = request.POST.get('customer_address')
        quote.customer_ceo = request.POST.get('customer_ceo')
        quote.customer_tel = request.POST.get('customer_tel')
        quote.customer_manager = request.POST.get('customer_manager')
        quote.customer_manager_tel = request.POST.get('customer_manager_tel')
        customer_email = request.POST.get('customer_manager_email')
        quote.customer_manager_email = customer_email if customer_email else None
        
        # 공급처
        quote.supplier_name = request.POST.get('supplier_name')
        quote.supplier_address = request.POST.get('supplier_address')
        quote.supplier_ceo = request.POST.get('supplier_ceo')
        quote.supplier_tel = request.POST.get('supplier_tel')
        quote.supplier_fax = request.POST.get('supplier_fax')
        quote.supplier_manager = request.POST.get('supplier_manager')
        
        # 하단 정보
        quote.valid_period = request.POST.get('valid_period')
        quote.trade_terms = request.POST.get('trade_terms')
        quote.bank_account = request.POST.get('bank_account')
        quote.note = request.POST.get('note')
        
        quote.save()
        
        messages.success(request, f"견적서 {quote.quote_no}가 수정되었습니다.")
        return redirect('voucher:quote_detail', pk=quote.pk)
    
    context = {
        'quote': quote,
        'today': date.today().strftime('%Y-%m-%d'),
        'status_choices': Quote.STATUS_CHOICES,
        'currency_choices': Quote.CURRENCY_CHOICES,
        'customers': Customer.objects.filter(is_active=True).order_by('name'),
    }
    return render(request, 'voucher/quote_form.html', context)


# ============================================
# 회사정보 관리
# ============================================

@login_required
def company_list(request):
    """회사정보 목록"""
    suppliers = CompanyInfo.objects.filter(is_supplier=True).order_by('name')
    customers = CompanyInfo.objects.filter(is_customer=True, is_supplier=False).order_by('name')
    
    context = {
        'suppliers': suppliers,
        'customers': customers,
    }
    return render(request, 'voucher/company_list.html', context)


@login_required
def company_create(request):
    """회사 등록"""
    if request.method == 'POST':
        code = request.POST.get('code')
        
        # 중복 체크
        if CompanyInfo.objects.filter(code=code).exists():
            messages.error(request, f"회사코드 {code}가 이미 존재합니다.")
            return redirect('voucher:company_create')
        
        company = CompanyInfo(
            code=code,
            name=request.POST.get('name'),
            name_en=request.POST.get('name_en') or None,
            name_jp=request.POST.get('name_jp') or None,
            is_supplier='is_supplier' in request.POST,
            is_customer='is_customer' in request.POST,
            address=request.POST.get('address'),
            address_en=request.POST.get('address_en'),
            ceo=request.POST.get('ceo'),
            business_no=request.POST.get('business_no'),
            tel=request.POST.get('tel'),
            fax=request.POST.get('fax'),
            email=request.POST.get('email') or None,
            website=request.POST.get('website') or None,
            manager_name=request.POST.get('manager_name'),
            manager_tel=request.POST.get('manager_tel'),
            manager_email=request.POST.get('manager_email') or None,
            bank_name=request.POST.get('bank_name'),
            bank_account=request.POST.get('bank_account'),
            bank_holder=request.POST.get('bank_holder'),
            default_trade_terms=request.POST.get('default_trade_terms'),
            note=request.POST.get('note'),
            is_active='is_active' in request.POST,
        )
        company.save()
        
        messages.success(request, f"회사 {company.name}이(가) 등록되었습니다.")
        return redirect('voucher:company_list')
    
    is_supplier = request.GET.get('is_supplier') == '1'
    
    context = {
        'company': None,
        'is_supplier': is_supplier,
    }
    return render(request, 'voucher/company_form.html', context)


@login_required
def company_edit(request, pk):
    """회사정보 수정"""
    company = get_object_or_404(CompanyInfo, pk=pk)
    
    if request.method == 'POST':
        company.name = request.POST.get('name')
        company.name_en = request.POST.get('name_en') or None
        company.name_jp = request.POST.get('name_jp') or None
        company.is_supplier = 'is_supplier' in request.POST
        company.is_customer = 'is_customer' in request.POST
        company.address = request.POST.get('address')
        company.address_en = request.POST.get('address_en')
        company.ceo = request.POST.get('ceo')
        company.business_no = request.POST.get('business_no')
        company.tel = request.POST.get('tel')
        company.fax = request.POST.get('fax')
        company.email = request.POST.get('email') or None
        company.website = request.POST.get('website') or None
        company.manager_name = request.POST.get('manager_name')
        company.manager_tel = request.POST.get('manager_tel')
        company.manager_email = request.POST.get('manager_email') or None
        company.bank_name = request.POST.get('bank_name')
        company.bank_account = request.POST.get('bank_account')
        company.bank_holder = request.POST.get('bank_holder')
        company.default_trade_terms = request.POST.get('default_trade_terms')
        company.note = request.POST.get('note')
        company.is_active = 'is_active' in request.POST
        
        company.save()
        
        messages.success(request, f"회사 {company.name} 정보가 수정되었습니다.")
        return redirect('voucher:company_list')
    
    context = {
        'company': company,
    }
    return render(request, 'voucher/company_form.html', context)


# ============================================
# 템플릿 관리
# ============================================

@login_required
def template_list(request):
    """템플릿 목록 및 업로드"""
    from pathlib import Path
    import os
    from datetime import datetime
    
    if request.method == 'POST' and request.FILES.get('template_file'):
        # 파일 업로드 처리
        uploaded_file = request.FILES['template_file']
        template_type = request.POST.get('template_type', 'QUOTE')
        name = request.POST.get('name', '')
        
        # 파일명 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{template_type.lower()}_{timestamp}.docx"
        
        # 저장 경로
        template_dir = Path(settings.BASE_DIR) / 'docx_templates'
        template_dir.mkdir(exist_ok=True)
        file_path = template_dir / filename
        
        # 파일 저장
        with open(file_path, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)
        
        # DB에 등록
        template = DocumentTemplate.objects.create(
            name=name or uploaded_file.name,
            template_type=template_type,
            filename=filename,
            is_active=True,
        )
        
        messages.success(request, f"템플릿 '{template.name}'이(가) 업로드되었습니다.")
        return redirect('voucher:template_list')
    
    # 등록된 템플릿 목록
    templates = DocumentTemplate.objects.all().order_by('template_type', '-is_default', 'name')
    
    # 파일 시스템 템플릿 목록
    template_dir = Path(settings.BASE_DIR) / 'docx_templates'
    files = []
    if template_dir.exists():
        for f in template_dir.glob('*.docx'):
            stat = f.stat()
            files.append({
                'name': f.name,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime),
            })
        files.sort(key=lambda x: x['modified'], reverse=True)
    
    context = {
        'templates': templates,
        'files': files,
    }
    return render(request, 'voucher/template_list.html', context)


@login_required
def template_download(request, pk):
    """DB 등록 템플릿 다운로드"""
    template = get_object_or_404(DocumentTemplate, pk=pk)
    
    file_path = Path(settings.BASE_DIR) / 'docx_templates' / template.filename
    
    if not file_path.exists():
        messages.error(request, f"파일을 찾을 수 없습니다: {template.filename}")
        return redirect('voucher:template_list')
    
    response = FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=template.filename
    )
    return response


@login_required
def template_download_file(request):
    """파일 시스템 템플릿 직접 다운로드"""
    filename = request.GET.get('name', '')
    
    if not filename or '..' in filename:
        messages.error(request, "잘못된 파일명입니다.")
        return redirect('voucher:template_list')
    
    file_path = Path(settings.BASE_DIR) / 'docx_templates' / filename
    
    if not file_path.exists():
        messages.error(request, f"파일을 찾을 수 없습니다: {filename}")
        return redirect('voucher:template_list')
    
    response = FileResponse(
        open(file_path, 'rb'),
        as_attachment=True,
        filename=filename
    )
    return response


@login_required
def template_set_default(request, pk):
    """기본 템플릿으로 설정"""
    template = get_object_or_404(DocumentTemplate, pk=pk)
    
    # 같은 유형의 다른 템플릿 기본 해제
    DocumentTemplate.objects.filter(
        template_type=template.template_type
    ).update(is_default=False)
    
    # 선택한 템플릿을 기본으로
    template.is_default = True
    template.save()
    
    messages.success(request, f"'{template.name}'이(가) 기본 템플릿으로 설정되었습니다.")
    return redirect('voucher:template_list')


@login_required
def template_delete(request, pk):
    """템플릿 삭제"""
    template = get_object_or_404(DocumentTemplate, pk=pk)
    
    # 파일도 삭제
    file_path = Path(settings.BASE_DIR) / 'docx_templates' / template.filename
    if file_path.exists():
        file_path.unlink()
    
    name = template.name
    template.delete()
    
    messages.success(request, f"템플릿 '{name}'이(가) 삭제되었습니다.")
    return redirect('voucher:template_list')


@login_required
def template_guide(request):
    """템플릿 변수 가이드"""
    guide_path = Path(settings.BASE_DIR) / 'docx_templates' / 'TEMPLATE_VARIABLES.md'
    
    content = ""
    if guide_path.exists():
        with open(guide_path, 'r', encoding='utf-8') as f:
            content = f.read()
    
    context = {
        'content': content,
    }
    return render(request, 'voucher/template_guide.html', context)


@login_required
def template_test_quote(request):
    """
    테스트 견적서 생성
    
    실제 DB 데이터(회사정보, 제품코드)를 사용해서 
    템플릿이 어떻게 출력되는지 확인할 수 있는 샘플 견적서 생성
    """
    from products.models import ProductCode, ProductPriceHistory
    
    # 자사 정보 가져오기
    supplier = CompanyInfo.get_supplier()
    if not supplier:
        messages.error(request, "자사 정보가 등록되어 있지 않습니다. 회사정보에서 먼저 등록해주세요.")
        return redirect('voucher:template_list')
    
    # 거래처 정보 가져오기 (KDKK 또는 첫 번째 거래처)
    customer = CompanyInfo.objects.filter(code='KDKK', is_customer=True).first()
    if not customer:
        customer = CompanyInfo.objects.filter(is_customer=True, is_active=True).first()
    
    if not customer:
        messages.error(request, "거래처 정보가 등록되어 있지 않습니다. 회사정보에서 먼저 등록해주세요.")
        return redirect('voucher:template_list')
    
    # 제품코드에서 품목 가져오기 (최대 10개)
    products = ProductCode.objects.filter(is_active=True).order_by('trade_condition_no')[:10]
    
    items = []
    for idx, pc in enumerate(products, 1):
        # 현재 단가 조회
        current_price = pc.get_current_price()
        price_per_kg = current_price.price_per_kg if current_price else 0
        currency = current_price.currency if current_price else 'KRW'
        
        # 포장단가 계산
        filling_weight = float(pc.filling_weight or 0)
        packing_price = float(price_per_kg) * filling_weight if filling_weight else 0
        
        items.append({
            'no': idx,
            'category': '',
            'gas_name': pc.gas_name or '',
            'product_name': pc.display_name or '',
            'material_code': pc.trade_condition_no or '',
            'end_user': pc.customer_user_name or '',
            'packing': '',
            'filling_weight': f"{filling_weight:.0f}" if filling_weight else '',
            'currency': currency,
            'price_per_kg': price_per_kg,
            'packing_price': packing_price,
        })
    
    if not items:
        messages.error(request, "제품코드가 등록되어 있지 않습니다.")
        return redirect('voucher:template_list')
    
    # 템플릿 조회
    template = DocumentTemplate.get_default_template('QUOTE')
    template_name = template.filename if template else 'offer_template.docx'
    
    try:
        generator = QuoteDocxGenerator(template_name)
        
        output_path = generator.generate_quote(
            quote_info={
                'date': date.today(),
                'no': 'TEST-0001',
                'title': '테스트 견적서 (샘플 데이터)',
            },
            supplier_info={
                'name': supplier.name,
                'address': supplier.address or '',
                'ceo': supplier.ceo or '',
                'tel': supplier.tel or '',
                'fax': supplier.fax or '',
                'manager': supplier.manager_name or '',
                'manager_tel': supplier.manager_tel or '',
                'manager_email': supplier.manager_email or '',
            },
            customer_info={
                'name': customer.name,
                'address': customer.address or '',
                'ceo': customer.ceo or '',
                'tel': customer.tel or '',
                'tel2': customer.fax or '',
                'manager': customer.manager_name or '',
                'manager_tel': customer.manager_tel or '',
                'manager_email': customer.manager_email or '',
            },
            items=items,
            footer_info={
                'valid_period': f'{date.today().year}.01.01 ~ {date.today().year}.12.31',
                'trade_terms': supplier.default_trade_terms or 'FOB',
                'document_date': date.today(),
            },
            output_filename=f"테스트견적서_{date.today().strftime('%Y%m%d')}.docx"
        )
        
        response = FileResponse(
            open(output_path, 'rb'),
            as_attachment=True,
            filename=f"테스트견적서_{date.today().strftime('%Y%m%d')}.docx"
        )
        response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        return response
        
    except FileNotFoundError as e:
        messages.error(request, f"템플릿 파일을 찾을 수 없습니다: {e}")
        return redirect('voucher:template_list')
    except Exception as e:
        messages.error(request, f"견적서 생성 오류: {e}")
        return redirect('voucher:template_list')
