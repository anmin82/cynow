# 수주 페이지 배포 가이드

## 개요

기존 orders 앱을 요구사항에 맞게 **단순화**하여 재구성했습니다.

## 변경 사항

### 삭제된 기능
- ❌ 역수입(backfill) 기능 완전 제거
- ❌ 복잡한 예약 시스템 제거
- ❌ 고아 문서 관리 제거
- ❌ 분할납품 일정 제거
- ❌ 제조부 납기 화면 제거

### 유지된 핵심 기능
- ✅ 수주 입력 (PO, POItem)
- ✅ 이동서번호 가이드 (참고용 추천값)
- ✅ FCMS 매칭 검증
- ✅ 진행 현황 모니터링 (기본 구조)

## 배포 절차

### 1. 기존 데이터 백업 (중요!)

```bash
# PostgreSQL 백업
pg_dump -U cynow_user -d cynow_db > backup_before_orders_rebuild_$(date +%Y%m%d).sql

# 또는 Django dumpdata
python manage.py dumpdata orders > orders_backup_$(date +%Y%m%d).json
```

### 2. 기존 테이블 삭제 (선택)

기존 orders 앱의 테이블이 있다면 삭제:

```sql
-- PostgreSQL
DROP TABLE IF EXISTS po_orphan_fcms_doc CASCADE;
DROP TABLE IF EXISTS po_progress_snapshot CASCADE;
DROP TABLE IF EXISTS po_fcms_match CASCADE;
DROP TABLE IF EXISTS po_reserved_doc_no CASCADE;
DROP TABLE IF EXISTS po_schedule CASCADE;
DROP TABLE IF EXISTS po_item CASCADE;
DROP TABLE IF EXISTS po_header CASCADE;
```

또는 Django 명령:

```bash
# 기존 마이그레이션 되돌리기
python manage.py migrate orders zero
```

### 3. 새 마이그레이션 적용

```bash
# 마이그레이션 파일 생성 (이미 완료됨)
python manage.py makemigrations orders

# 마이그레이션 적용
python manage.py migrate orders
```

### 4. 테이블 확인

```sql
-- 생성된 테이블 확인
\dt po_*
\dt move_*
\dt fcms_*

-- 예상 테이블:
-- po_simple
-- po_item_simple
-- move_no_guide
-- fcms_match_status
```

### 5. Admin 슈퍼유저 생성 (필요 시)

```bash
python manage.py createsuperuser
```

### 6. 개발 서버 실행

```bash
python manage.py runserver
```

### 7. 접근 확인

- 수주 목록: http://localhost:8000/orders/
- Admin: http://localhost:8000/admin/orders/

## 테스트 데이터 생성

```python
# Django shell
python manage.py shell

from orders.models import PO, POItem
from django.utils import timezone

# 테스트 수주 생성
po = PO.objects.create(
    customer_order_no='TEST-2024-001',
    supplier_user_code='KDKK',
    supplier_user_name='케이디케이케이',
    received_at=timezone.now(),
    status='DRAFT'
)

# 테스트 품목 생성
POItem.objects.create(
    po=po,
    line_no=1,
    trade_condition_code='ITEM001',
    trade_condition_name='테스트 품목',
    qty=100
)

print(f"테스트 수주 생성 완료: {po.customer_order_no}")
```

## FCMS CDC 연결 설정

### 1. 데이터베이스 라우터 확인

`config/settings.py`에서 FCMS CDC 데이터베이스 설정 확인:

```python
DATABASES = {
    'default': {
        # CYNOW 메인 DB
    },
    'fcms_cdc': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'fcms_cdc',
        'USER': 'fcms_user',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 2. CDC 쿼리 테스트

```python
from django.db import connection

with connection.cursor() as cursor:
    # FCMS 이동서 최신 번호 조회 테스트
    cursor.execute("""
        SELECT MAX(MOVE_REPORT_NO) 
        FROM fcms_cdc.TR_MOVE_REPORTS
        WHERE MOVE_REPORT_NO LIKE 'FP24%'
    """)
    result = cursor.fetchone()
    print(f"최신 이동서번호: {result[0]}")
```

## 구현 필요 항목

현재 임시로 구현된 부분:

### 1. `move_no_guide_service.py`
- `calculate_suggested_move_no()`: FCMS CDC 실제 쿼리 구현 필요
- `check_fcms_match()`: FCMS CDC 실제 쿼리 구현 필요

### 2. `po_progress_service.py`
- `get_instruction_qty()`: TR_ORDERS_INFORMATIONS 쿼리 구현 필요
- `get_filling_qty()`: TR_MOVE_REPORT_DETAILS 쿼리 구현 필요
- `get_warehouse_in_qty()`: 입고 테이블 구조 확인 후 구현 필요
- `get_shipping_qty()`: 출하 테이블 구조 확인 후 구현 필요

## 트러블슈팅

### 마이그레이션 충돌
```bash
# 마이그레이션 충돌 시
python manage.py migrate orders --fake-initial
```

### 테이블명 충돌
기존 테이블과 충돌 시:
```sql
-- 기존 테이블 이름 변경
ALTER TABLE po_header RENAME TO po_header_old;
ALTER TABLE po_item RENAME TO po_item_old;
```

### FCMS CDC 연결 실패
- PostgreSQL 연결 정보 확인
- 방화벽 설정 확인
- 사용자 권한 확인

## 롤백 절차

문제 발생 시 롤백:

```bash
# 1. 마이그레이션 되돌리기
python manage.py migrate orders zero

# 2. 백업 복원
psql -U cynow_user -d cynow_db < backup_before_orders_rebuild_YYYYMMDD.sql

# 또는
python manage.py loaddata orders_backup_YYYYMMDD.json
```

## 문의

배포 관련 문의는 개발팀에 연락하세요.


