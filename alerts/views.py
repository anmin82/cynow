from django.shortcuts import render
from core.repositories.cylinder_repository import CylinderRepository
from core.utils.view_helper import group_cylinder_types, calculate_risk_level


def alerts(request):
    """위험도 알림 리스트 - 용기종류별 집계"""
    inventory_data = CylinderRepository.get_inventory_summary()
    
    # 용기종류별 집계 (헬퍼 함수 사용)
    cylinder_types_dict = group_cylinder_types(inventory_data)
    
    alerts_list = []
    
    # 용기종류별 위험도 판단
    for key, type_info in cylinder_types_dict.items():
        available_qty = type_info['available_qty']
        total_qty = type_info['total_qty']
        abnormal_qty = type_info['statuses'].get('이상', 0)
        disposal_qty = type_info['statuses'].get('폐기', 0)
        shipping_qty = type_info['statuses'].get('출하', 0)
        
        # 위험도 계산 (헬퍼 함수 사용)
        risk_level = calculate_risk_level(available_qty, total_qty, abnormal_qty, disposal_qty)
        
        # NORMAL이 아닌 경우만 알림에 추가
        if risk_level == 'NORMAL':
            continue
        
        message = ''
        advice = ''
        
        # HIGH 위험도
        if available_qty == 0:
            message = f'{type_info["gas_name"]}의 가용수량이 0입니다.'
            advice = '긴급 조치가 필요합니다. 즉시 충전 또는 보관 용기를 확보하세요.'
        elif abnormal_qty > 0:
            message = f'{type_info["gas_name"]}의 이상 상태 용기가 {abnormal_qty}개입니다.'
            advice = '점검이 필요합니다. 이상 용기의 상태를 확인하고 조치하세요.'
        elif disposal_qty > 0:
            message = f'{type_info["gas_name"]}의 폐기 용기가 {disposal_qty}개입니다.'
            advice = '처리 계획이 필요합니다. 폐기 용기의 적절한 처리를 계획하세요.'
        # MEDIUM 위험도
        elif 0 < available_qty < 5:
            message = f'{type_info["gas_name"]}의 가용수량이 {available_qty}개로 적습니다.'
            advice = '재고 보충을 검토하세요. 향후 수요를 고려하여 충전 계획을 수립하세요.'
        # LOW 위험도 (모니터링)
        elif shipping_qty >= 50:
            message = f'{type_info["gas_name"]}의 출하 수량이 {shipping_qty}개로 많습니다.'
            advice = '회수 계획을 확인하세요. 출하된 용기의 회수 일정을 점검하세요.'
        elif available_qty / total_qty < 0.3:
            message = f'{type_info["gas_name"]}의 가용수량 비율이 낮습니다 ({available_qty}/{total_qty}).'
            advice = '재고 상태를 모니터링하세요. 필요시 보충 계획을 수립하세요.'
        
        alerts_list.append({
            'risk_level': risk_level,
            'cylinder_type_key': type_info.get('cylinder_type_key', key),
            'gas_name': type_info['gas_name'],
            'capacity': type_info['capacity'],
            'valve_spec': type_info.get('valve_spec', ''),
            'cylinder_spec': type_info['cylinder_spec'],
            'available_qty': available_qty,
            'total_qty': total_qty,
            'abnormal_qty': abnormal_qty,
            'disposal_qty': disposal_qty,
            'message': message,
            'advice': advice,
        })
    
    # 위험도 순으로 정렬 (HIGH > MEDIUM > LOW)
    risk_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    alerts_list.sort(key=lambda x: (risk_order.get(x['risk_level'], 99), x['gas_name']))
    
    context = {
        'alerts': alerts_list,
    }
    return render(request, 'alerts/alerts.html', context)
