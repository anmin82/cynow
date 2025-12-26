from datetime import date, datetime

from django.shortcuts import render
from django.utils import timezone
from django.http import HttpResponseBadRequest

from orders.repositories.fcms_repository import FcmsRepository
from voucher.models import CompanyInfo

from .services import SalesService


def index(request):
    """판매(MVP) 홈"""
    context = {
        "today": timezone.localdate(),
    }
    return render(request, "sales/index.html", context)


def transaction_statement(request):
    """
    거래명세서(MVP)
    - 기간 + 거래처 기준 출하(MOVE_CODE=60) 집계
    - 비로그인은 단가/금액 블라인드
    """
    today = timezone.localdate()
    default_start = date(today.year, 1, 1)

    start_s = request.GET.get("start") or default_start.isoformat()
    end_s = request.GET.get("end") or today.isoformat()
    supplier_code = (request.GET.get("supplier") or "").strip()

    try:
        start = datetime.strptime(start_s, "%Y-%m-%d").date()
        end = datetime.strptime(end_s, "%Y-%m-%d").date()
    except ValueError:
        return HttpResponseBadRequest("날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)")

    shipments = SalesService.list_shipments(start, end, supplier_user_code=supplier_code)

    # 거래처 목록(드롭다운) - 회사정보에 등록된 고객코드 사용
    companies = CompanyInfo.objects.all().order_by("name")[:300]
    company_map = {c.code: c for c in companies if c.code}

    # 단가/금액은 로그인 사용자에게만 표시 (MVP 정책)
    price_date = end if request.user.is_authenticated else None
    summary = SalesService.build_statement_summary(shipments, at_date_for_price=price_date)

    context = {
        "start": start,
        "end": end,
        "supplier_code": supplier_code,
        "companies": companies,
        "shipments": shipments,
        "summary_items": summary["items"],
        "total_amount": summary["total_amount"],
        "selected_company": company_map.get(supplier_code),
        "is_price_visible": request.user.is_authenticated,
    }
    return render(request, "sales/transaction_statement.html", context)


def shipping_instruction(request):
    """
    출하지시서(MVP)
    - 이동서번호(MOVE_REPORT_NO) 입력 → 이동서 상세(품목/수량/용기리스트) 표시
    """
    move_report_no = (request.GET.get("move_report_no") or "").strip()
    detail = None
    if move_report_no:
        detail = FcmsRepository.get_move_report_detail(move_report_no)

    context = {
        "move_report_no": move_report_no,
        "detail": detail,
    }
    return render(request, "sales/shipping_instruction.html", context)


def sales_summary(request):
    """
    매출 집계(MVP)
    - 월별(기간) 제품코드별 출하 수량 집계
    - 비로그인은 단가/금액 블라인드
    """
    today = timezone.localdate()
    default_start = date(today.year, 1, 1)

    start_s = request.GET.get("start") or default_start.isoformat()
    end_s = request.GET.get("end") or today.isoformat()

    try:
        start = datetime.strptime(start_s, "%Y-%m-%d").date()
        end = datetime.strptime(end_s, "%Y-%m-%d").date()
    except ValueError:
        return HttpResponseBadRequest("날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)")

    shipments = SalesService.list_shipments(start, end)

    # 월-제품코드 집계
    monthly = {}
    for s in shipments:
        if not s.shipping_date:
            continue
        ym = s.shipping_date.strftime("%Y-%m")
        code = s.trade_condition_code or "UNKNOWN"
        if ym not in monthly:
            monthly[ym] = {}
        monthly[ym][code] = monthly[ym].get(code, 0) + int(s.shipped_count or 0)

    # 월별 테이블 표시용 정렬
    months = sorted(monthly.keys())
    all_codes = sorted({code for m in monthly.values() for code in m.keys()})
    rows = []
    for ym in months:
        row = {"ym": ym, "items": [], "total_qty": 0}
        for code in all_codes:
            qty = monthly[ym].get(code, 0)
            row["items"].append({"code": code, "qty": qty})
            row["total_qty"] += qty
        rows.append(row)

    context = {
        "start": start,
        "end": end,
        "rows": rows,
        "codes": all_codes,
    }
    return render(request, "sales/sales_summary.html", context)


