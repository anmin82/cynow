"""
FCMS CDC → CYNOW 제품코드 동기화 서비스
"""
from django.db import connection
from django.utils import timezone
from .models import ProductCode, ProductCodeSync


def sync_product_codes_from_cdc():
    """
    fcms_cdc.ma_selection_patterns + ma_selection_pattern_details 
    → products.ProductCode 동기화
    """
    sync_log = ProductCodeSync.objects.create(
        sync_type='FULL',
        started_at=timezone.now(),
        status='RUNNING'
    )
    
    try:
        with connection.cursor() as cursor:
            # CDC 테이블에서 제품코드 + 상세 + 가스명 + 충전량 조인 조회
            cursor.execute("""
                SELECT 
                    p."SELECTION_PATTERN_CODE",
                    TRIM(p."TRADE_CONDITION_NO") as trade_condition_no,
                    TRIM(p."PRIMARY_STORE_USER_CODE") as primary_store_user_code,
                    TRIM(p."CUSTOMER_USER_CODE") as customer_user_code,
                    TRIM(d."CYLINDER_SPEC_CODE") as cylinder_spec_code,
                    TRIM(d."VALVE_SPEC_CODE") as valve_spec_code,
                    d."CAPACITY",
                    TRIM(p."ITEM_CODE") as item_code,
                    TRIM(i."DISPLAY_NAME") as gas_name,
                    ax."NSGT_YORY" as filling_weight
                FROM "fcms_cdc"."ma_selection_patterns" p
                LEFT JOIN "fcms_cdc"."ma_selection_pattern_details" d 
                    ON p."SELECTION_PATTERN_CODE" = d."SELECTION_PATTERN_CODE"
                    AND d."ROW_SEQ" = 1
                LEFT JOIN "fcms_cdc"."ma_items" i
                    ON TRIM(p."ITEM_CODE") = TRIM(i."ITEM_CODE")
                LEFT JOIN "fcms_cdc"."mt_ax0330" ax
                    ON TRIM(p."PACKING_CODE") = TRIM(ax."NSGT_CD")
                ORDER BY p."TRADE_CONDITION_NO"
            """)
            
            rows = cursor.fetchall()
            
        records_created = 0
        records_updated = 0
        
        for row in rows:
            (selection_pattern_code, trade_condition_no, primary_store_user_code,
             customer_user_code, cylinder_spec_code, valve_spec_code, capacity,
             item_code, gas_name, filling_weight) = row
            
            # 스펙명은 코드로 대체 (별도 테이블 조인 없이)
            cylinder_spec_name = cylinder_spec_code
            valve_spec_name = valve_spec_code
            
            # gas_name이 없으면 item_code 앞부분 사용 (fallback)
            if not gas_name and item_code:
                gas_name = item_code.strip()[:20] if item_code else None
            
            # 표시명 생성
            display_name = generate_display_name(
                trade_condition_no, gas_name, capacity, valve_spec_name, filling_weight
            )
            
            # Upsert
            product, created = ProductCode.objects.update_or_create(
                selection_pattern_code=selection_pattern_code.strip() if selection_pattern_code else '',
                defaults={
                    'trade_condition_no': trade_condition_no or '',
                    'primary_store_user_code': (primary_store_user_code or '').strip(),
                    'customer_user_code': (customer_user_code or '').strip() if customer_user_code else None,
                    'cylinder_spec_code': cylinder_spec_code,
                    'valve_spec_code': valve_spec_code,
                    'capacity': capacity,
                    'cylinder_spec_name': cylinder_spec_name,
                    'valve_spec_name': valve_spec_name,
                    'gas_name': gas_name,
                    'filling_weight': filling_weight,
                    'display_name': display_name,
                    'fcms_synced_at': timezone.now(),
                }
            )
            
            if created:
                records_created += 1
            else:
                records_updated += 1
        
        sync_log.completed_at = timezone.now()
        sync_log.records_processed = len(rows)
        sync_log.records_created = records_created
        sync_log.records_updated = records_updated
        sync_log.status = 'SUCCESS'
        sync_log.save()
        
        return {
            'success': True,
            'processed': len(rows),
            'created': records_created,
            'updated': records_updated
        }
        
    except Exception as e:
        sync_log.completed_at = timezone.now()
        sync_log.status = 'FAILED'
        sync_log.error_message = str(e)
        sync_log.save()
        
        return {
            'success': False,
            'error': str(e)
        }


def get_gas_name_from_item_code(item_code):
    """아이템코드로 가스명 조회 (DISPLAY_NAME 사용)"""
    if not item_code:
        return None
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COALESCE("DISPLAY_NAME", "NAME") 
                FROM "fcms_cdc"."ma_items" 
                WHERE TRIM("ITEM_CODE") = %s
                LIMIT 1
            """, [item_code.strip()])
            row = cursor.fetchone()
            return row[0].strip() if row and row[0] else None
    except:
        return None


def generate_display_name(trade_condition_no, gas_name, capacity, valve_spec_name, filling_weight=None):
    """표시명 생성"""
    parts = []
    
    if gas_name:
        parts.append(gas_name)
    
    if filling_weight:
        parts.append(f"{int(filling_weight)}kg")
    elif capacity:
        parts.append(f"{capacity}L")
    
    if valve_spec_name:
        parts.append(valve_spec_name)
    
    return ' / '.join(parts) if parts else trade_condition_no


def get_cdc_product_count():
    """CDC 테이블의 제품코드 개수"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) FROM "fcms_cdc"."ma_selection_patterns"
            """)
            return cursor.fetchone()[0]
    except:
        return 0

