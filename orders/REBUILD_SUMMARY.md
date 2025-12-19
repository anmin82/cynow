# Orders 앱 재구성 완료 요약

## 작업 개요

기존 orders 앱을 요구사항에 맞게 **완전히 재구성**했습니다.

## 핵심 원칙 준수

### ✅ 절대 규칙 준수
1. ✅ PO 번호는 `customer_order_no` 단 하나
2. ✅ 이동서번호 가이드 = 예약 아님 (참고용 추천값)
3. ✅ FCMS 데이터 역수입(backfill) 없음
4. ✅ ERP 기능 확장 없음

### ✅ 수주 페이지 목적 (3개만)
1. ✅ 고객 이메일로 받은 수주 정보 기록
2. ✅ FCMS 수기 입력용 이동서번호 가이드 제공
3. ✅ 수주 진행 단계 모니터링

### ✅ 금지 키워드 제거
- ❌ `internal_po_no` → 제거
- ❌ `system_po_no` → 제거
- ❌ `backfill` → 제거
- ❌ `OrphanFcmsDoc` → 제거
- ❌ `POSchedule` (분할납품) → 제거
- ❌ `POProgressSnapshot` → 제거

## 변경 사항

### 모델 단순화

#### 이전 (복잡)
```
PO (po_header)
├── is_backfilled
├── needs_review
├── review_note
POItem (po_item)
POSchedule (분할납품)
ReservedDocNo (예약 시스템)
POFcmsMatch (복잡한 매칭)
OrphanFcmsDoc (고아 문서)
POProgressSnapshot (스냅샷)
```

#### 이후 (단순)
```
PO (po_simple)
├── customer_order_no (PO번호 - 유일)
├── supplier_user_code
├── supplier_user_name
├── received_at
├── status
├── memo

POItem (po_item_simple)
├── line_no
├── trade_condition_code
├── trade_condition_name
├── qty
├── remarks

MoveNoGuide (이동서번호 가이드)
├── suggested_move_no (추천값)
├── state
├── fcms_actual_move_no

FCMSMatchStatus (매칭 상태)
├── match_state
├── fcms_arrival_shipping_no
├── fcms_move_report_no
```

### 뷰 단순화

#### 제거된 뷰
- ❌ `backfill_review` (역수입 검토)
- ❌ `approve_backfill` (역수입 승인)
- ❌ `match_orphan` (고아 문서 매칭)
- ❌ `manufacturing_schedule` (제조부 납기)
- ❌ `reserve_doc_no` (예약번호 생성)
- ❌ `release_reservation` (예약 해제)
- ❌ `manual_match` (수동 매칭)

#### 유지된 뷰
- ✅ `po_list` (수주 목록)
- ✅ `po_detail` (수주 상세)
- ✅ `po_create` (수주 생성)
- ✅ `po_edit` (수주 수정)
- ✅ `po_delete` (수주 삭제)
- ✅ `generate_guide` (가이드 생성)
- ✅ `check_fcms_match` (매칭 확인)

### 서비스 단순화

#### 제거된 서비스
- ❌ `ReservationService` (예약 시스템)
- ❌ `MatchingService` (복잡한 매칭)
- ❌ `MonitoringService` (복잡한 모니터링)

#### 새 서비스 (단순)
- ✅ `move_no_guide_service.py`
  - `calculate_suggested_move_no()`: 추천 번호 계산
  - `check_fcms_match()`: 매칭 검증
- ✅ `po_progress_service.py`
  - `calculate_progress()`: 진행현황 집계

### 템플릿 단순화

#### 제거된 템플릿
- ❌ `backfill_review.html`
- ❌ `manual_match.html`
- ❌ `manufacturing_schedule.html`
- ❌ `po_progress.html`

#### 새 템플릿 (단순)
- ✅ `po_list.html` (수주 목록)
- ✅ `po_detail.html` (수주 상세)
- ✅ `po_form.html` (수주 입력/수정)

## 파일 구조

```
orders/
├── models.py                          ✅ 재작성 (단순화)
├── views.py                           ✅ 재작성 (단순화)
├── forms.py                           ✅ 재작성 (단순화)
├── urls.py                            ✅ 재작성 (단순화)
├── admin.py                           ✅ 재작성 (단순화)
├── services/
│   ├── __init__.py                   ✅ 재작성
│   ├── move_no_guide_service.py      ✅ 신규
│   └── po_progress_service.py        ✅ 신규
├── repositories/
│   └── __init__.py                   ✅ 정리
├── templates/orders/
│   ├── po_list.html                  ✅ 재작성
│   ├── po_detail.html                ✅ 재작성
│   └── po_form.html                  ✅ 재작성
├── migrations/
│   └── 0001_initial.py               ✅ 생성됨
├── management/
│   └── commands/                     ✅ backfill 제거
├── README.md                          ✅ 재작성
├── DEPLOYMENT_SIMPLE.md              ✅ 신규
└── REBUILD_SUMMARY.md                ✅ 이 파일
```

## 데이터베이스 테이블

### 생성된 테이블
```sql
po_simple              -- PO 헤더
po_item_simple         -- PO 품목
move_no_guide          -- 이동서번호 가이드
fcms_match_status      -- FCMS 매칭 상태
```

### 인덱스
```sql
-- PO
po_simple_customer_order_no_idx
po_simple_status_idx
po_simple_supplier_user_code_idx

-- MoveNoGuide
move_no_guide_po_state_idx
move_no_guide_suggested_move_no_idx

-- POItem
po_item_simple_trade_condition_code_idx
```

## 화면 구성

### 1. 수주 목록 (`/orders/`)
| 컬럼 | 설명 |
|------|------|
| PO번호 | `customer_order_no` (유일한 식별자) |
| 고객명 | `supplier_user_name` |
| 수주일 | `received_at` |
| 수주수량 | `SUM(POItem.qty)` |
| 추천이동서번호 | `MoveNoGuide.suggested_move_no` |
| 상태 | DRAFT/GUIDED/MATCHED/IN_PROGRESS/COMPLETED |
| FCMS매칭 | MATCHED/NOT_ENTERED/MISMATCH |

### 2. 수주 상세 (`/orders/<customer_order_no>/`)
- 기본 정보 (PO번호, 고객, 수주일, 상태)
- 수주 품목 목록
- 이동서번호 가이드 (생성 버튼)
- FCMS 매칭 상태 (확인 버튼)
- 진행 현황 (구현 예정)

### 3. 수주 입력 (`/orders/new/`)
- PO번호(고객발주번호) 입력
- 고객 정보 입력
- 품목 정보 입력 (최소 1개)

## 이동서번호 가이드 로직

```python
def calculate_suggested_move_no():
    """
    1. FCMS CDC에서 최신 이동서번호 조회
       SELECT MAX(MOVE_REPORT_NO) 
       FROM fcms_cdc.TR_MOVE_REPORTS
       WHERE MOVE_REPORT_NO LIKE 'FP25%'
    
    2. 연번 추출 및 +1
       FP240123 → 123 → 124
    
    3. 추천 번호 생성
       FP25 + 000124 = FP250124
    
    4. 화면에 표시만 (발급/예약 없음)
    """
```

## FCMS 매칭 검증 로직

```python
def check_fcms_match(customer_order_no, suggested_move_no):
    """
    1. FCMS CDC에서 실제 이동서 조회
       SELECT mr.MOVE_REPORT_NO, o.ARRIVAL_SHIPPING_NO
       FROM fcms_cdc.TR_MOVE_REPORTS mr
       JOIN fcms_cdc.TR_ORDERS o ON mr.ORDERS_ID = o.id
       WHERE o.CUSTOMER_ORDER_NO = ?
    
    2. 매칭 판단
       - 없음 → NOT_ENTERED
       - 일치 → MATCHED
       - 불일치 → MISMATCH
    """
```

## 진행 현황 집계 로직

```python
def calculate_progress(customer_order_no):
    """
    1. 수주수량: POItem.qty 합계
    2. 충전지시수량: TR_ORDERS_INFORMATIONS.INSTRUCTION_COUNT
    3. 충전진행수량: TR_MOVE_REPORT_DETAILS 병 수
    4. 입고수량: FCMS 입고 테이블
    5. 출하수량: FCMS 출하 테이블
    
    단계 판단:
    - 출하수량 == 수주수량 → "완료"
    - 입고수량 > 0 → "입고 진행중"
    - 충전진행수량 > 0 → "충전 진행중"
    - 충전지시수량 > 0 → "충전 지시됨"
    - 기타 → "대기중"
    """
```

## 다음 단계

### 즉시 가능
1. ✅ 마이그레이션 적용: `python manage.py migrate orders`
2. ✅ 테스트 데이터 생성
3. ✅ 수주 입력 테스트

### 구현 필요
1. ⏳ FCMS CDC 연결 설정 확인
2. ⏳ `calculate_suggested_move_no()` 실제 쿼리 구현
3. ⏳ `check_fcms_match()` 실제 쿼리 구현
4. ⏳ `calculate_progress()` 실제 쿼리 구현
5. ⏳ 입고/출하 테이블 구조 확인

## 코드 품질

### 준수 사항
- ✅ PEP 8 스타일 가이드
- ✅ Django Best Practices
- ✅ 명확한 주석
- ✅ Docstring 작성
- ✅ 타입 힌트 (부분)

### 테스트 커버리지
- ⏳ 단위 테스트 작성 필요
- ⏳ 통합 테스트 작성 필요

## 성능 고려사항

### 인덱스
- ✅ `customer_order_no` (UNIQUE)
- ✅ `status`
- ✅ `supplier_user_code`
- ✅ `suggested_move_no`
- ✅ `trade_condition_code`

### 쿼리 최적화
- ✅ `select_related()` 사용 (FK)
- ✅ `prefetch_related()` 사용 (역참조)
- ⏳ CDC 쿼리 최적화 필요

## 보안 고려사항

- ✅ CSRF 보호
- ✅ SQL Injection 방지 (Parameterized Query)
- ✅ XSS 방지 (Django Template Escaping)
- ⏳ 권한 관리 (`@login_required` 추가 필요)

## 결론

기존 orders 앱을 요구사항에 맞게 **완전히 단순화**하여 재구성했습니다.

### 핵심 성과
1. ✅ PO 번호 단일화 (`customer_order_no`)
2. ✅ 역수입(backfill) 완전 제거
3. ✅ 이동서번호 가이드 = 참고용 추천값
4. ✅ FCMS 매칭 검증 단순화
5. ✅ 불필요한 기능 모두 제거

### 남은 작업
1. FCMS CDC 실제 쿼리 구현
2. 진행현황 집계 완성
3. 테스트 코드 작성
4. 권한 관리 추가

**이제 수주 페이지는 요구사항에 정확히 맞는 단순하고 명확한 시스템입니다.**


