"""
용기 사이클 시뮬레이션 서비스 레이어
"""
from datetime import date
from dateutil.relativedelta import relativedelta
from django.db import connection
from typing import Dict, List, Optional
from plans.models import PlanForecastMonthly, PlanScheduledMonthly, PlanFillingMonthly


class SimulationService:
    """용기 사이클 시뮬레이션 계산 서비스"""
    
    @staticmethod
    def get_current_inventory(cylinder_type_key: str) -> Dict:
        """
        특정 용기종류의 현재 재고 현황 조회
        
        Returns:
            {
                'available': int,      # 가용재고 (보관:미회수 + 보관:회수)
                'at_enduser': int,     # 엔드유저 보유 (출하 상태)
                'in_repair': int,      # 정비대기 (정비대상 상태)
                'expired': int,        # 내압만료
                'total': int,          # 전체
            }
        """
        with connection.cursor() as cursor:
            # cylinder_type_key로 용기 조회
            query = """
                SELECT 
                    dashboard_status,
                    pressure_expire_date,
                    COUNT(*) as qty
                FROM cy_cylinder_current
                WHERE cylinder_type_key = %s
                GROUP BY dashboard_status, pressure_expire_date
            """
            cursor.execute(query, [cylinder_type_key])
            rows = cursor.fetchall()
        
        result = {
            'available': 0,
            'at_enduser': 0,
            'in_repair': 0,
            'expired': 0,
            'total': 0,
        }
        
        today = date.today()
        
        for row in rows:
            status = row[0] or ''
            expire_date = row[1]
            qty = row[2]
            
            result['total'] += qty
            
            # 내압만료 체크
            expire_date_val = expire_date.date() if hasattr(expire_date, 'date') else expire_date
            if expire_date_val and expire_date_val < today:
                result['expired'] += qty
            elif status in ('보관:미회수', '보관:회수', '보관'):
                result['available'] += qty
            elif status == '출하':
                result['at_enduser'] += qty
            elif status in ('정비대상', '정비'):
                result['in_repair'] += qty
        
        return result
    
    @staticmethod
    def get_monthly_expiring(cylinder_type_key: str, months: int = 12) -> Dict[str, int]:
        """
        향후 N개월간 내압만료 예정 용기 수량 조회
        
        Returns:
            {'2025-01': 5, '2025-02': 3, ...}
        """
        today = date.today()
        end_date = today + relativedelta(months=months)
        
        with connection.cursor() as cursor:
            query = """
                SELECT 
                    TO_CHAR(pressure_expire_date, 'YYYY-MM') as expire_month,
                    COUNT(*) as qty
                FROM cy_cylinder_current
                WHERE cylinder_type_key = %s
                  AND pressure_expire_date >= %s
                  AND pressure_expire_date < %s
                GROUP BY TO_CHAR(pressure_expire_date, 'YYYY-MM')
                ORDER BY expire_month
            """
            cursor.execute(query, [cylinder_type_key, today, end_date])
            rows = cursor.fetchall()
        
        return {row[0]: row[1] for row in rows}
    
    @staticmethod
    def get_historical_recovery_rate(cylinder_type_key: str, months: int = 6) -> float:
        """
        과거 N개월간 평균 회수율 계산
        
        회수율 = 회수 수량 / 출하 수량
        """
        # 실제로는 이력 데이터에서 계산해야 하지만,
        # MVP에서는 간단하게 고정값 또는 추정치 사용
        # TODO: 실제 이력 데이터 기반 계산 구현
        return 0.8  # 기본 80%
    
    @staticmethod
    def get_plans(cylinder_type_key: str, months: int = 12) -> Dict:
        """
        출하계획, 충전계획, 투입계획 조회
        
        Returns:
            {
                'forecast': {'2025-01': 50, '2025-02': 60, ...},  # 출하계획
                'filling': {'2025-01': 100, ...},  # 충전계획
                'filling_shutdown': {'2025-04': True, ...},  # 오버홀 여부
                'purchase': {'2025-01': 10, ...},
                'repair': {'2025-01': 5, ...},
            }
        """
        today = date.today()
        start_month = date(today.year, today.month, 1)
        
        # 용기종류 키에서 개별 필드 추출 (간단한 파싱)
        # cylinder_type_key는 MD5 해시이므로, 실제 조회는 다른 방법 필요
        
        forecast_plans = PlanForecastMonthly.objects.filter(
            cylinder_type_key=cylinder_type_key,
            month__gte=start_month,
            month__lt=start_month + relativedelta(months=months)
        ).values('month', 'planned_ship_qty')
        
        filling_plans = PlanFillingMonthly.objects.filter(
            cylinder_type_key=cylinder_type_key,
            month__gte=start_month,
            month__lt=start_month + relativedelta(months=months)
        ).values('month', 'planned_fill_qty', 'is_shutdown')
        
        scheduled_plans = PlanScheduledMonthly.objects.filter(
            cylinder_type_key=cylinder_type_key,
            month__gte=start_month,
            month__lt=start_month + relativedelta(months=months)
        ).values('month', 'add_purchase_qty', 'add_refurb_qty', 
                 'recover_from_defect_qty', 'convert_gas_qty')
        
        result = {
            'forecast': {},
            'filling': {},
            'filling_shutdown': {},
            'purchase': {},
            'repair': {},
            'recover': {},
            'convert': {},
        }
        
        for plan in forecast_plans:
            month_key = plan['month'].strftime('%Y-%m')
            result['forecast'][month_key] = plan['planned_ship_qty'] or 0
        
        for plan in filling_plans:
            month_key = plan['month'].strftime('%Y-%m')
            result['filling'][month_key] = plan['planned_fill_qty'] or 0
            result['filling_shutdown'][month_key] = plan['is_shutdown']
        
        for plan in scheduled_plans:
            month_key = plan['month'].strftime('%Y-%m')
            result['purchase'][month_key] = plan['add_purchase_qty'] or 0
            result['repair'][month_key] = plan['add_refurb_qty'] or 0
            result['recover'][month_key] = plan['recover_from_defect_qty'] or 0
            result['convert'][month_key] = plan['convert_gas_qty'] or 0
        
        return result
    
    @staticmethod
    def simulate(
        cylinder_type_key: str,
        months: int = 12,
        recovery_method: str = 'fixed_rate',
        recovery_rate: float = 0.8,
        recovery_lead_months: int = 2,
        manual_recovery: Optional[Dict[str, int]] = None,
        purchase_multiplier: float = 1.0,
        repair_multiplier: float = 1.0,
    ) -> Dict:
        """
        시뮬레이션 실행
        
        Args:
            cylinder_type_key: 용기종류 키
            months: 시뮬레이션 기간 (개월)
            recovery_method: 회수 예측 방법 ('fixed_rate', 'historical', 'manual')
            recovery_rate: 고정 회수율 (0.0 ~ 1.0)
            recovery_lead_months: 회수 리드타임 (개월)
            manual_recovery: 직접 입력 회수량 {'2025-01': 50, ...}
            purchase_multiplier: 신규구매 배수
            repair_multiplier: 정비투입 배수
        
        Returns:
            {
                'months': ['2025-01', '2025-02', ...],
                'series': {
                    'available': [500, 480, ...],
                    'at_enduser': [200, 220, ...],
                    'in_repair': [50, 45, ...],
                    'expired': [10, 15, ...],
                },
                'details': [
                    {'month': '2025-01', 'available': 500, 'ship': -80, 'recover': +60, ...},
                    ...
                ]
            }
        """
        # 1. 현재 재고 조회
        current = SimulationService.get_current_inventory(cylinder_type_key)
        
        # 2. 계획 데이터 조회
        plans = SimulationService.get_plans(cylinder_type_key, months)
        
        # 3. 내압만료 예정 조회
        expiring = SimulationService.get_monthly_expiring(cylinder_type_key, months)
        
        # 4. 과거 회수율 (historical 방법일 때)
        if recovery_method == 'historical':
            recovery_rate = SimulationService.get_historical_recovery_rate(cylinder_type_key)
        
        # 5. 월별 시뮬레이션
        today = date.today()
        month_list = []
        for i in range(months):
            m = today + relativedelta(months=i)
            month_list.append(date(m.year, m.month, 1).strftime('%Y-%m'))
        
        # 초기값
        available = current['available']
        at_enduser = current['at_enduser']
        in_repair = current['in_repair']
        expired = current['expired']
        
        # 과거 출하 이력 (회수 계산용)
        past_shipments = {}  # {'2024-11': 100, '2024-12': 80, ...}
        
        series = {
            'available': [],
            'at_enduser': [],
            'in_repair': [],
            'expired': [],
        }
        details = []
        
        for i, month_key in enumerate(month_list):
            # 이번 달 변동
            ship_out = plans['forecast'].get(month_key, 0)
            fill_plan = plans['filling'].get(month_key, 0)
            is_shutdown = plans['filling_shutdown'].get(month_key, False)
            purchase_in = int(plans['purchase'].get(month_key, 0) * purchase_multiplier)
            repair_in = int(plans['repair'].get(month_key, 0) * repair_multiplier)
            expire_out = expiring.get(month_key, 0)
            
            # 회수량 계산
            if recovery_method == 'manual' and manual_recovery:
                recover_in = manual_recovery.get(month_key, 0)
            else:
                # N개월 전 출하량 기준 회수
                lead_month_idx = i - recovery_lead_months
                if lead_month_idx >= 0:
                    lead_month_key = month_list[lead_month_idx]
                    past_ship = plans['forecast'].get(lead_month_key, 0)
                elif lead_month_idx >= -recovery_lead_months:
                    # 시뮬레이션 시작 전 출하는 현재 at_enduser에서 추정
                    past_ship = at_enduser / max(recovery_lead_months, 1) if i == 0 else 0
                else:
                    past_ship = 0
                recover_in = int(past_ship * recovery_rate)
            
            # 재고 변동 적용
            
            # 충전 역량 제한: 오버홀이면 충전 불가, 아니면 충전계획만큼 출하 가능
            # 충전계획이 있으면 그 수량만큼만 출하 가능 (충전 → 제품 → 출하)
            if is_shutdown:
                # 오버홀 기간: 충전 불가 = 출하 불가 (기존 재고에서만 출하)
                actual_fill = 0
            elif fill_plan > 0:
                # 충전계획이 있으면 공용기에서 충전해서 출하
                actual_fill = min(fill_plan, empty_cyl) if 'empty_cyl' in locals() else fill_plan
            else:
                # 충전계획이 없으면 제한 없음 (기존 로직)
                actual_fill = ship_out
            
            # 출하: 가용 → 엔드유저 (충전 역량 고려)
            max_ship = min(ship_out, available)
            if fill_plan > 0 and not is_shutdown:
                # 충전계획이 있으면 충전 수량 이내로만 출하
                max_ship = min(max_ship, fill_plan)
            elif is_shutdown:
                # 오버홀이면 출하 불가 (이미 충전된 제품 재고만 출하 가능)
                max_ship = 0  # 간소화: 오버홀 기간에는 출하 0으로 가정
            
            actual_ship = max_ship
            available -= actual_ship
            at_enduser += actual_ship
            
            # 회수: 엔드유저 → 가용
            actual_recover = min(recover_in, at_enduser)
            at_enduser -= actual_recover
            available += actual_recover
            
            # 신규 구매: → 가용
            available += purchase_in
            
            # 정비 완료: 정비대기 → 가용
            actual_repair = min(repair_in, in_repair)
            in_repair -= actual_repair
            available += actual_repair
            
            # 내압만료: 가용/정비대기 → 만료
            if expire_out > 0:
                expire_from_available = min(expire_out, available)
                available -= expire_from_available
                expired += expire_from_available
                remain_expire = expire_out - expire_from_available
                if remain_expire > 0:
                    expire_from_repair = min(remain_expire, in_repair)
                    in_repair -= expire_from_repair
                    expired += expire_from_repair
            
            # 기록
            series['available'].append(available)
            series['at_enduser'].append(at_enduser)
            series['in_repair'].append(in_repair)
            series['expired'].append(expired)
            
            details.append({
                'month': month_key,
                'available': available,
                'at_enduser': at_enduser,
                'in_repair': in_repair,
                'expired': expired,
                'ship': -actual_ship,
                'fill': fill_plan,
                'is_shutdown': is_shutdown,
                'recover': actual_recover,
                'purchase': purchase_in,
                'repair': actual_repair,
                'expire': -expire_out,
            })
        
        return {
            'months': month_list,
            'series': series,
            'details': details,
            'current': current,
            'params': {
                'recovery_method': recovery_method,
                'recovery_rate': recovery_rate,
                'recovery_lead_months': recovery_lead_months,
                'purchase_multiplier': purchase_multiplier,
                'repair_multiplier': repair_multiplier,
            }
        }

