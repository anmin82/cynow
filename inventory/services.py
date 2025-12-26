"""
재고 관리 서비스

스냅샷 생성, 재고 갱신 등 핵심 비즈니스 로직
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, List, Any

from django.db import connection, transaction
from django.db.models import Sum, Count, Q, F
from django.utils import timezone

from .models import (
    InventorySettings,
    InventoryTransaction,
    CylinderInventory,
    ProductInventory,
    CylinderInventorySnapshot,
    ProductInventorySnapshot,
    SnapshotLog,
)

logger = logging.getLogger(__name__)


class InventoryService:
    """재고 관리 서비스"""
    
    # ============================================
    # 스냅샷 생성
    # ============================================
    
    @staticmethod
    def create_daily_snapshot(
        snapshot_date: date = None,
        triggered_by: str = 'AUTO',
        user=None
    ) -> SnapshotLog:
        """
        일간 스냅샷 생성
        
        Args:
            snapshot_date: 스냅샷 기준일 (기본: 오늘)
            triggered_by: 트리거 유형 ('AUTO' 또는 'MANUAL')
            user: 실행 사용자
        
        Returns:
            SnapshotLog: 스냅샷 로그
        """
        if snapshot_date is None:
            snapshot_date = timezone.localdate()
        
        snapshot_datetime = timezone.now()
        
        # 로그 생성
        log = SnapshotLog.objects.create(
            snapshot_date=snapshot_date,
            triggered_by=triggered_by,
            triggered_user=user,
            status='RUNNING'
        )
        
        try:
            with transaction.atomic():
                # 1. 용기 재고 스냅샷 생성
                cylinder_count = InventoryService._create_cylinder_snapshots(
                    snapshot_date, snapshot_datetime
                )
                
                # 2. 제품 재고 스냅샷 생성
                product_count = InventoryService._create_product_snapshots(
                    snapshot_date, snapshot_datetime
                )
                
                # 3. 스냅샷 트랜잭션 기록
                InventoryTransaction.objects.create(
                    txn_type='SNAPSHOT',
                    txn_date=snapshot_date,
                    txn_datetime=snapshot_datetime,
                    remarks=f'일간 스냅샷 생성 (용기: {cylinder_count}, 제품: {product_count})'
                )
                
                # 로그 업데이트
                log.status = 'SUCCESS'
                log.cylinder_snapshots_created = cylinder_count
                log.product_snapshots_created = product_count
                log.completed_at = timezone.now()
                log.save()
                
                logger.info(
                    f"일간 스냅샷 생성 완료: {snapshot_date} "
                    f"(용기: {cylinder_count}, 제품: {product_count})"
                )
                
        except Exception as e:
            log.status = 'FAILED'
            log.error_message = str(e)
            log.completed_at = timezone.now()
            log.save()
            logger.error(f"스냅샷 생성 실패: {e}")
            raise
        
        return log
    
    @staticmethod
    def _create_cylinder_snapshots(snapshot_date: date, snapshot_datetime: datetime) -> int:
        """
        용기 재고 스냅샷 생성
        
        현재 CylinderInventory 테이블에서 스냅샷 복사
        + 당일 트랜잭션 집계
        """
        # 기존 스냅샷 삭제 (같은 날짜)
        CylinderInventorySnapshot.objects.filter(
            snapshot_date=snapshot_date
        ).delete()
        
        # 당일 트랜잭션 집계 (용기 관련)
        day_txns = InventoryTransaction.objects.filter(
            txn_date=snapshot_date,
            txn_type__startswith='CYL_'
        ).exclude(txn_type='SNAPSHOT')
        
        # 그룹별 입출고 집계
        in_agg = day_txns.filter(is_inbound=True).values(
            'cylinder_type_key'
        ).annotate(total=Sum('quantity'))
        
        out_agg = day_txns.filter(is_inbound=False).values(
            'cylinder_type_key'
        ).annotate(total=Sum('quantity'))
        
        in_map = {item['cylinder_type_key']: int(item['total'] or 0) for item in in_agg}
        out_map = {item['cylinder_type_key']: int(item['total'] or 0) for item in out_agg}
        
        # 현재 재고 스냅샷 생성
        inventories = CylinderInventory.objects.all()
        snapshots = []
        
        for inv in inventories:
            snapshots.append(CylinderInventorySnapshot(
                snapshot_date=snapshot_date,
                snapshot_datetime=snapshot_datetime,
                cylinder_type_key=inv.cylinder_type_key,
                gas_name=inv.gas_name,
                capacity=inv.capacity,
                valve_spec=inv.valve_spec,
                cylinder_spec=inv.cylinder_spec,
                enduser_code=inv.enduser_code,
                status=inv.status,
                location=inv.location,
                quantity=inv.quantity,
                day_in=in_map.get(inv.cylinder_type_key, 0),
                day_out=out_map.get(inv.cylinder_type_key, 0),
            ))
        
        if snapshots:
            CylinderInventorySnapshot.objects.bulk_create(snapshots)
        
        return len(snapshots)
    
    @staticmethod
    def _create_product_snapshots(snapshot_date: date, snapshot_datetime: datetime) -> int:
        """
        제품 재고 스냅샷 생성
        
        현재 ProductInventory 테이블에서 스냅샷 복사
        + 당일 입고/출하 집계
        """
        # 기존 스냅샷 삭제 (같은 날짜)
        ProductInventorySnapshot.objects.filter(
            snapshot_date=snapshot_date
        ).delete()
        
        # 당일 트랜잭션 집계 (제품 관련)
        day_txns = InventoryTransaction.objects.filter(
            txn_date=snapshot_date,
            txn_type__startswith='PROD_'
        )
        
        # 제품코드별 입출고 집계
        in_agg = day_txns.filter(txn_type='PROD_IN').values(
            'gas_name'  # trade_condition_code 대신 gas_name 사용
        ).annotate(total=Sum('quantity'))
        
        out_agg = day_txns.filter(txn_type='PROD_OUT').values(
            'gas_name'
        ).annotate(total=Sum('quantity'))
        
        in_map = {item['gas_name']: int(item['total'] or 0) for item in in_agg}
        out_map = {item['gas_name']: int(item['total'] or 0) for item in out_agg}
        
        # 현재 재고 스냅샷 생성
        inventories = ProductInventory.objects.all()
        snapshots = []
        
        for inv in inventories:
            snapshots.append(ProductInventorySnapshot(
                snapshot_date=snapshot_date,
                snapshot_datetime=snapshot_datetime,
                product_code=inv.product_code,
                trade_condition_code=inv.trade_condition_code,
                gas_name=inv.gas_name,
                warehouse=inv.warehouse,
                quantity=inv.quantity,
                day_in=in_map.get(inv.gas_name, 0),
                day_out=out_map.get(inv.gas_name, 0),
            ))
        
        if snapshots:
            ProductInventorySnapshot.objects.bulk_create(snapshots)
        
        return len(snapshots)
    
    # ============================================
    # cy_cylinder_current 기반 용기 재고 동기화
    # ============================================
    
    @staticmethod
    def sync_cylinder_inventory_from_current() -> Dict[str, int]:
        """
        cy_cylinder_current 테이블에서 용기 재고 동기화
        
        cylinder_type_key × dashboard_status 별로 집계
        
        Returns:
            {'synced': N, 'deleted': M}
        """
        query = '''
            SELECT 
                cylinder_type_key,
                dashboard_gas_name,
                dashboard_capacity,
                dashboard_valve_spec_name,
                dashboard_cylinder_spec_name,
                dashboard_enduser,
                dashboard_status,
                dashboard_location,
                COUNT(*) as cnt
            FROM cy_cylinder_current
            WHERE cylinder_type_key IS NOT NULL
            GROUP BY 
                cylinder_type_key,
                dashboard_gas_name,
                dashboard_capacity,
                dashboard_valve_spec_name,
                dashboard_cylinder_spec_name,
                dashboard_enduser,
                dashboard_status,
                dashboard_location
        '''
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
        except Exception as e:
            logger.error(f"cy_cylinder_current 조회 실패: {e}")
            return {'synced': 0, 'deleted': 0, 'error': str(e)}
        
        # 상태 매핑 (dashboard_status → CylinderInventory.status)
        status_map = {
            '보관': 'FILLED',
            '충전': 'FILLING',
            '분석': 'ANALYZING',
            '수리': 'REPAIRING',
            '폐기': 'SCRAPPED',
            '빈용기': 'EMPTY',
            '空ボンベ': 'EMPTY',
            '出荷': 'AT_CUSTOMER',
            '출하': 'AT_CUSTOMER',
        }
        
        synced = 0
        updated = 0
        with transaction.atomic():
            # 기존 재고 모두 0으로 초기화 (이후 업데이트되지 않은 항목 식별용)
            CylinderInventory.objects.all().update(quantity=0)
            
            for row in rows:
                type_key = row[0]
                gas_name = row[1] or ''
                capacity = row[2]
                valve_spec = row[3] or ''
                cylinder_spec = row[4] or ''
                enduser_code = row[5] or ''
                raw_status = row[6] or ''
                location = row[7] or ''
                count = row[8]
                
                # 상태 변환
                status = status_map.get(raw_status, 'OTHER')
                
                obj, created = CylinderInventory.objects.update_or_create(
                    cylinder_type_key=type_key,
                    status=status,
                    location=location,
                    defaults={
                        'gas_name': gas_name,
                        'capacity': capacity,
                        'valve_spec': valve_spec,
                        'cylinder_spec': cylinder_spec,
                        'enduser_code': enduser_code,
                        'quantity': count,
                    }
                )
                if created:
                    synced += 1
                else:
                    updated += 1
            
            # 수량 0인 항목 삭제 (더 이상 존재하지 않는 조합)
            deleted = CylinderInventory.objects.filter(quantity=0).delete()[0]
        
        logger.info(f"용기 재고 동기화 완료: 신규 {synced}건, 갱신 {updated}건, 삭제 {deleted}건")
        return {'synced': synced, 'updated': updated, 'deleted': deleted}
    
    # ============================================
    # cy_cylinder_current 기반 제품 재고 동기화
    # ============================================
    
    @staticmethod
    def sync_product_inventory_from_current() -> Dict[str, int]:
        """
        cy_cylinder_current 테이블에서 제품 재고 동기화
        
        "제품" 상태(창입) 용기를 ProductCode(제품코드) 기준으로 집계
        cylinder_type_key를 통해 ProductCode와 매핑
        
        Returns:
            {'synced': N, 'updated': M, 'deleted': D}
        """
        from products.models import ProductCode as PC
        
        # cylinder_type_key → ProductCode 객체 매핑 생성
        type_key_to_product = {}
        for pc in PC.objects.filter(is_active=True, cylinder_type_key__isnull=False):
            if pc.cylinder_type_key:
                type_key_to_product[pc.cylinder_type_key] = pc
        
        # trade_condition_no로도 조회할 수 있도록 매핑 추가
        trade_no_to_product = {
            pc.trade_condition_no: pc
            for pc in PC.objects.filter(is_active=True)
        }
        
        # "제품" 상태 용기를 cylinder_type_key별로 집계
        query = '''
            SELECT 
                cylinder_type_key,
                dashboard_gas_name,
                dashboard_capacity,
                COUNT(*) as cnt
            FROM cy_cylinder_current
            WHERE dashboard_status = '제품'
              AND cylinder_type_key IS NOT NULL
            GROUP BY cylinder_type_key, dashboard_gas_name, dashboard_capacity
        '''
        
        try:
            with connection.cursor() as cursor:
                cursor.execute(query)
                rows = cursor.fetchall()
        except Exception as e:
            logger.error(f"제품 재고 조회 실패: {e}")
            return {'synced': 0, 'updated': 0, 'deleted': 0, 'error': str(e)}
        
        synced = 0
        updated = 0
        
        # trade_condition_code별 수량 합산 (여러 cylinder_type_key가 같은 제품코드로 매핑될 수 있음)
        product_qty_map = {}  # trade_condition_code -> {'product': ProductCode, 'quantity': int, 'gas_name': str}
        
        for row in rows:
            type_key = row[0]
            gas_name = row[1] or ''
            capacity = row[2]
            count = row[3]
            
            # ProductCode 매핑 확인
            if type_key in type_key_to_product:
                pc = type_key_to_product[type_key]
                trade_code = pc.trade_condition_no
                display_name = pc.display_name or pc.gas_name or gas_name
            else:
                # 매핑 없으면 gas_name + capacity로 대체
                trade_code = f"{gas_name}_{int(capacity)}L" if capacity else gas_name
                display_name = gas_name
                pc = None
            
            # 수량 합산
            if trade_code in product_qty_map:
                product_qty_map[trade_code]['quantity'] += count
            else:
                product_qty_map[trade_code] = {
                    'product': pc,
                    'quantity': count,
                    'gas_name': display_name,
                }
        
        with transaction.atomic():
            # 기존 재고 0으로 초기화
            ProductInventory.objects.all().update(quantity=0)
            
            for trade_code, data in product_qty_map.items():
                pc = data['product']
                qty = data['quantity']
                display_name = data['gas_name']
                
                obj, created = ProductInventory.objects.update_or_create(
                    trade_condition_code=trade_code,
                    warehouse='MAIN',
                    defaults={
                        'product_code': pc,  # ProductCode FK 연결
                        'gas_name': display_name,
                        'quantity': qty,
                    }
                )
                if created:
                    synced += 1
                else:
                    updated += 1
            
            # 수량 0인 항목 삭제
            deleted = ProductInventory.objects.filter(quantity=0).delete()[0]
        
        logger.info(f"제품 재고 동기화 완료: 신규 {synced}건, 갱신 {updated}건, 삭제 {deleted}건")
        return {'synced': synced, 'updated': updated, 'deleted': deleted}
    
    # ============================================
    # 제품 재고 트랜잭션 처리
    # ============================================
    
    @staticmethod
    def record_product_in(
        trade_condition_code: str,
        quantity: int,
        gas_name: str = '',
        warehouse: str = 'MAIN',
        reference_type: str = '',
        reference_no: str = '',
        remarks: str = '',
        user=None
    ) -> InventoryTransaction:
        """
        제품 입고 기록 (충전 완료 용기 창고 입고)
        
        Args:
            trade_condition_code: 제품코드 (예: KF001)
            quantity: 수량 (병)
            gas_name: 가스명
            warehouse: 창고 (기본: MAIN)
            reference_type: 참조 문서 유형
            reference_no: 참조 문서 번호
            remarks: 비고
            user: 실행 사용자
        
        Returns:
            InventoryTransaction
        """
        with transaction.atomic():
            # 트랜잭션 기록
            txn = InventoryTransaction.objects.create(
                txn_type='PROD_IN',
                gas_name=gas_name,
                quantity=Decimal(quantity),
                is_inbound=True,
                to_location=warehouse,
                reference_type=reference_type,
                reference_no=reference_no,
                remarks=remarks,
                created_by=user,
            )
            
            # 재고 갱신
            inv, created = ProductInventory.objects.get_or_create(
                trade_condition_code=trade_condition_code,
                warehouse=warehouse,
                defaults={
                    'gas_name': gas_name,
                    'quantity': 0,
                }
            )
            inv.quantity = F('quantity') + quantity
            inv.save()
            inv.refresh_from_db()
        
        logger.info(f"제품 입고: {trade_condition_code} +{quantity}병 → 재고 {inv.quantity}병")
        return txn
    
    @staticmethod
    def record_product_out(
        trade_condition_code: str,
        quantity: int,
        gas_name: str = '',
        warehouse: str = 'MAIN',
        reference_type: str = '',
        reference_no: str = '',
        remarks: str = '',
        user=None
    ) -> InventoryTransaction:
        """
        제품 출하 기록 (고객 출하)
        
        Args:
            trade_condition_code: 제품코드
            quantity: 수량 (병)
            gas_name: 가스명
            warehouse: 창고
            reference_type: 참조 문서 유형 (예: PO, MOVE_REPORT)
            reference_no: 참조 문서 번호
            remarks: 비고
            user: 실행 사용자
        
        Returns:
            InventoryTransaction
        """
        with transaction.atomic():
            # 트랜잭션 기록
            txn = InventoryTransaction.objects.create(
                txn_type='PROD_OUT',
                gas_name=gas_name,
                quantity=Decimal(quantity),
                is_inbound=False,
                from_location=warehouse,
                reference_type=reference_type,
                reference_no=reference_no,
                remarks=remarks,
                created_by=user,
            )
            
            # 재고 갱신
            try:
                inv = ProductInventory.objects.get(
                    trade_condition_code=trade_condition_code,
                    warehouse=warehouse
                )
                inv.quantity = F('quantity') - quantity
                inv.save()
                inv.refresh_from_db()
                
                # 마이너스 재고 체크 (경고만)
                if inv.quantity < 0:
                    logger.warning(
                        f"재고 부족 경고: {trade_condition_code} 재고 {inv.quantity}병 (마이너스)"
                    )
            except ProductInventory.DoesNotExist:
                # 재고 없는 경우 마이너스로 시작 (경고)
                inv = ProductInventory.objects.create(
                    trade_condition_code=trade_condition_code,
                    warehouse=warehouse,
                    gas_name=gas_name,
                    quantity=-quantity,
                )
                logger.warning(f"재고 없이 출하: {trade_condition_code} → {inv.quantity}병")
        
        logger.info(f"제품 출하: {trade_condition_code} -{quantity}병 → 재고 {inv.quantity}병")
        return txn
    
    # ============================================
    # 재고 조회
    # ============================================
    
    @staticmethod
    def get_product_inventory_summary() -> List[Dict[str, Any]]:
        """
        제품 재고 요약 조회
        
        Returns:
            [{'trade_condition_code': 'KF001', 'gas_name': 'COS', 'quantity': 10, ...}, ...]
        """
        return list(ProductInventory.objects.values(
            'trade_condition_code',
            'gas_name',
            'warehouse',
            'quantity',
            'updated_at'
        ).order_by('trade_condition_code'))
    
    @staticmethod
    def get_cylinder_inventory_summary() -> List[Dict[str, Any]]:
        """
        용기 재고 요약 조회 (가스명 × 상태별 집계)
        
        Returns:
            [{'gas_name': 'COS', 'status': 'FILLED', 'total': 100}, ...]
        """
        return list(CylinderInventory.objects.values(
            'gas_name', 'status'
        ).annotate(
            total=Sum('quantity')
        ).order_by('gas_name', 'status'))
    
    @staticmethod
    def get_inventory_trend(
        days: int = 30,
        trade_condition_code: str = None
    ) -> List[Dict[str, Any]]:
        """
        제품 재고 추세 조회
        
        Args:
            days: 조회 기간 (일)
            trade_condition_code: 특정 제품코드 (None이면 전체)
        
        Returns:
            일별 재고량 리스트
        """
        since = timezone.localdate() - timedelta(days=days)
        
        qs = ProductInventorySnapshot.objects.filter(
            snapshot_date__gte=since
        )
        
        if trade_condition_code:
            qs = qs.filter(trade_condition_code=trade_condition_code)
        
        return list(qs.values(
            'snapshot_date',
            'trade_condition_code',
            'gas_name',
            'quantity',
            'day_in',
            'day_out'
        ).order_by('snapshot_date', 'trade_condition_code'))

