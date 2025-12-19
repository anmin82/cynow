# 수주 페이지 빠른 시작 가이드

## 1분 요약

기존 orders 앱을 요구사항에 맞게 **완전히 재구성**했습니다.

### 핵심 변경
- ✅ PO 번호 = `customer_order_no` 단 하나
- ✅ 역수입(backfill) 완전 제거
- ✅ 이동서번호 가이드 = 참고용 추천값
- ✅ 복잡한 기능 모두 제거

## 즉시 실행

### 1. 마이그레이션
```bash
cd c:\cynow
python manage.py migrate orders
```

### 2. 서버 실행
```bash
python manage.py runserver
```

### 3. 접근
- 수주 목록: http://localhost:8000/orders/
- Admin: http://localhost:8000/admin/orders/

## 테스트 데이터 생성

```bash
python manage.py shell
```

```python
from orders.models import PO, POItem
from django.utils import timezone

# 수주 생성
po = PO.objects.create(
    customer_order_no='TEST-2024-001',
    supplier_user_code='KDKK',
    supplier_user_name='케이디케이케이',
    received_at=timezone.now(),
    status='DRAFT',
    memo='테스트 수주'
)

# 품목 생성
POItem.objects.create(
    po=po,
    line_no=1,
    trade_condition_code='ITEM001',
    trade_condition_name='테스트 품목 1',
    qty=100
)

POItem.objects.create(
    po=po,
    line_no=2,
    trade_condition_code='ITEM002',
    trade_condition_name='테스트 품목 2',
    qty=50
)

print(f"✅ 테스트 수주 생성 완료: {po.customer_order_no}")
print(f"   총 수주수량: {po.total_qty}")
```

## 주요 화면

### 수주 목록
- URL: `/orders/`
- 기능: 수주 목록 조회, 필터링, 새 수주 등록

### 수주 상세
- URL: `/orders/<PO번호>/`
- 기능: 수주 정보, 품목 목록, 이동서번호 가이드, FCMS 매칭

### 수주 등록
- URL: `/orders/new/`
- 기능: 새 수주 입력

## 다음 단계

### 필수
1. FCMS CDC 연결 설정 확인
2. `move_no_guide_service.py` 실제 쿼리 구현
3. `po_progress_service.py` 실제 쿼리 구현

### 선택
1. 권한 관리 추가 (`@login_required`)
2. 테스트 코드 작성
3. 페이지네이션 추가

## 문서

- `README.md`: 전체 개요
- `REBUILD_SUMMARY.md`: 재구성 상세 내역
- `DEPLOYMENT_SIMPLE.md`: 배포 가이드
- `QUICK_START.md`: 이 파일

## 문의

개발팀에 연락하세요.


