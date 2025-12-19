# 수주 페이지 (Orders App)

## 목적

수주 페이지는 다음 **3가지 목적만** 가집니다:

1. **고객 이메일로 받은 수주 정보를 정확히 기록**
2. **FCMS 수기 입력을 돕기 위해 "이동서번호 가이드(추천값)" 제공**
3. **수주가 현재 어느 단계인지 모니터링**

## ⚠️ 중요 원칙

### 1. PO 번호는 단 하나
- **PO 번호 = `customer_order_no` (고객발주번호)**
- 내부 PO 번호 없음
- 시스템 생성 PO 번호 없음
- id를 PO 번호처럼 사용하지 않음

### 2. 이동서번호 가이드 = 예약 아님
- CYNOW는 번호를 **발급하지 않음**
- FCMS 최신 번호 기준 +1 계산하여 **참고용으로만 표시**
- 실제 기준은 **FCMS에 생성된 문서**

### 3. FCMS 데이터 역수입(backfill) 없음
- FCMS 데이터를 CYNOW로 가져오지 않음
- FCMS는 독립적으로 운영

### 4. ERP 기능 없음
- 단순 수주 기록 및 모니터링만
- 복잡한 ERP 기능 확장 금지

## 데이터 모델

### PO (수주)
```python
customer_order_no  # PO번호(고객발주번호) - 유일한 식별자
supplier_user_code # 고객코드
supplier_user_name # 고객명
received_at        # 수주일시
status             # DRAFT/GUIDED/MATCHED/IN_PROGRESS/COMPLETED
memo               # 메모
```

### POItem (수주 품목)
```python
po                    # FK to PO
line_no               # 라인번호
trade_condition_code  # 제품코드
trade_condition_name  # 제품명
qty                   # 수주수량
remarks               # 비고
```

### MoveNoGuide (이동서번호 가이드)
```python
po                   # FK to PO
suggested_move_no    # 추천이동서번호 (FP+YY+6자리)
state                # SHOWN/MATCHED/IGNORED
fcms_actual_move_no  # FCMS실제번호
```

### FCMSMatchStatus (FCMS 매칭 상태)
```python
po                        # OneToOne to PO
fcms_arrival_shipping_no  # FCMS도착출하번호
fcms_move_report_no       # FCMS이동서번호
match_state               # MATCHED/NOT_ENTERED/MISMATCH
```

## 주요 기능

### 1. 수주 목록 (`/orders/`)
- PO번호, 고객명, 수주일, 수주수량, 추천이동서번호, 상태, FCMS매칭 표시

### 2. 수주 등록 (`/orders/new/`)
- PO번호(고객발주번호) 입력
- 고객 정보 입력
- 품목 정보 입력 (최소 1개)

### 3. 수주 상세 (`/orders/<customer_order_no>/`)
- 수주 정보 표시
- 품목 목록 표시
- 이동서번호 가이드 생성 버튼
- FCMS 매칭 확인 버튼

### 4. 이동서번호 가이드 생성
```python
# services/move_no_guide_service.py
calculate_suggested_move_no()
# → FCMS CDC에서 MAX 번호 조회
# → +1 계산
# → 추천값 반환 (예: FP250001)
```

### 5. FCMS 매칭 검증
```python
# services/move_no_guide_service.py
check_fcms_match(customer_order_no, suggested_move_no)
# → FCMS CDC에서 실제 입력 확인
# → MATCHED / NOT_ENTERED / MISMATCH 판단
```

### 6. 진행 현황 모니터링
```python
# services/po_progress_service.py
calculate_progress(customer_order_no)
# → 수주수량: POItem 합계
# → 충전지시수량: TR_ORDERS_INFORMATIONS
# → 충전진행수량: TR_MOVE_REPORT_DETAILS
# → 입고수량: FCMS 입고 테이블
# → 출하수량: FCMS 출하 테이블
```

## 설치 및 실행

### 1. 마이그레이션
```bash
python manage.py makemigrations orders
python manage.py migrate orders
```

### 2. Admin 등록
```bash
python manage.py createsuperuser
# Admin: http://localhost:8000/admin/
```

### 3. URL 설정
`config/urls.py`에 이미 포함되어 있음:
```python
urlpatterns = [
    path('orders/', include('orders.urls')),
]
```

### 4. 접근
- 수주 목록: http://localhost:8000/orders/
- 새 수주: http://localhost:8000/orders/new/

## 파일 구조

```
orders/
├── models.py                          # 데이터 모델
├── views.py                           # 뷰 함수
├── forms.py                           # 폼
├── urls.py                            # URL 라우팅
├── admin.py                           # Admin 설정
├── services/
│   ├── move_no_guide_service.py      # 이동서번호 가이드 계산
│   └── po_progress_service.py        # 진행현황 집계
├── templates/orders/
│   ├── po_list.html                  # 수주 목록
│   ├── po_detail.html                # 수주 상세
│   └── po_form.html                  # 수주 입력/수정
└── README.md                          # 이 파일
```

## TODO

### 구현 완료
- [x] 수주 모델 (PO, POItem)
- [x] 이동서번호 가이드 모델 (MoveNoGuide)
- [x] FCMS 매칭 모델 (FCMSMatchStatus)
- [x] 수주 CRUD 뷰
- [x] 수주 목록/상세/입력 템플릿
- [x] Admin 설정

### 구현 필요
- [ ] FCMS CDC 연결 설정 확인
- [ ] `calculate_suggested_move_no()` 실제 CDC 쿼리 구현
- [ ] `check_fcms_match()` 실제 CDC 쿼리 구현
- [ ] `calculate_progress()` 실제 CDC 쿼리 구현
- [ ] 입고/출하 테이블 구조 확인 및 쿼리 구현
- [ ] 진행현황 화면 완성

## 금지 사항

다음 키워드/개념이 코드에 나타나면 **실패**입니다:

- ❌ `internal_po_no`
- ❌ `system_po_no`
- ❌ `backfill` (역수입)
- ❌ 자동 주문 생성
- ❌ ERP 확장
- ❌ 기존 모델 수정
- ❌ FCMS 데이터 복원

## 문의

수주 페이지 관련 문의는 개발팀에 연락하세요.
