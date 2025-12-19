from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from core.repositories.cylinder_repository import CylinderRepository
from core.utils.view_helper import parse_cylinder_spec, parse_valve_spec, parse_usage_place


def cylinder_list(request):
    """용기번호 리스트"""
    # 필터 파라미터
    gas_name = request.GET.get('gas_name', '')
    status = request.GET.get('status', '')
    location = request.GET.get('location', '')
    valve_spec = request.GET.get('valve_spec', '')
    cylinder_spec = request.GET.get('cylinder_spec', '')
    usage_place = request.GET.get('usage_place', '')
    cylinder_type_key = request.GET.get('cylinder_type_key', '')
    days = request.GET.get('days', '')
    
    filters = {}
    if gas_name:
        filters['gas_name'] = gas_name
    if status:
        filters['status'] = status
    if location:
        filters['location'] = location
    if valve_spec:
        filters['valve_spec'] = valve_spec
    if cylinder_spec:
        filters['cylinder_spec'] = cylinder_spec
    if cylinder_type_key:
        filters['cylinder_type_key'] = cylinder_type_key
    
    # 기간 필터
    days_int = None
    if days:
        try:
            days_int = int(days)
        except:
            days_int = None
    
    # 페이지네이션
    page = request.GET.get('page', 1)
    try:
        page = int(page)
    except:
        page = 1
    
    per_page = 50
    offset = (page - 1) * per_page
    
    # 전체 개수 조회 (페이지네이션용)
    total_count = CylinderRepository.get_cylinder_count(filters=filters, days=days_int)
    
    # 현재 페이지 데이터만 조회 (SQL LIMIT/OFFSET 사용)
    cylinders_list = CylinderRepository.get_cylinder_list(
        filters=filters, 
        limit=per_page, 
        offset=offset,
        days=days_int
    )
    
    # 페이지네이션 객체 생성
    from django.core.paginator import Paginator, Page
    paginator = Paginator([], per_page)  # 빈 리스트로 초기화
    paginator._count = total_count  # 전체 개수 설정
    
    # Page 객체 생성
    cylinders = Page(cylinders_list, page, paginator)
    
    # 필터 옵션 조회 (최적화된 쿼리 사용)
    filter_options = CylinderRepository.get_filter_options()
    
    # 상태 목록
    statuses = ['보관', '충전', '분석', '창입', '출하', '이상', '폐기']
    
    context = {
        'cylinders': cylinders,
        'gas_name': gas_name,
        'status': status,
        'location': location,
        'valve_spec': valve_spec,
        'cylinder_spec': cylinder_spec,
        'usage_place': usage_place,
        'cylinder_type_key': cylinder_type_key,
        'days': days,
        # 필터 옵션
        'gas_names': filter_options['gas_names'],
        'locations': filter_options['locations'],
        'valve_specs': filter_options['valve_specs'],
        'cylinder_specs': filter_options['cylinder_specs'],
        'statuses': statuses,
    }
    return render(request, 'cylinders/list.html', context)


def cylinder_detail(request, cylinder_no):
    """용기 상세보기"""
    filters = {'cylinder_no': cylinder_no}
    cylinders = CylinderRepository.get_cylinder_list(filters=filters, limit=1)
    
    if not cylinders:
        from django.http import Http404
        raise Http404("용기를 찾을 수 없습니다.")
    
    cylinder = cylinders[0]
    
    context = {
        'cylinder': cylinder,
    }
    return render(request, 'cylinders/detail.html', context)
