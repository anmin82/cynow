# CYNOW 수주(PO) 관리 시스템

> FCMS 연계 수주 입력, 번호 예약, 매칭 검증, 진행 모니터링 통합 시스템

---

## 📋 개요

CYNOW PO 관리 시스템은 FCMS(Oracle)에 입력될 주문 정보를 사전에 등록하고, 문서번호를 예약하며, 실제 FCMS 입력 후 매칭 검증을 수행하는 가이드/모니터링 시스템입니다.

### 주요 기능

1. **수주 입력**: FCMS 입력 전 CYNOW에서 사전 등록
2. **번호 예약**: 도착출하번호/이동서번호 자동 추천
3. **매칭 검증**: 예약번호와 FCMS 실제 입력 일치 여부 확인
4. **진행 모니터링**: 충전→입고→출하 단계별 진행률 추적
5. **역수입(Backfill)**: FCMS 기존 데이터로부터 PO 자동 복원

---

## 🏗️ 아키텍처

### 데이터 모델

```
PO (수주 헤더)
├─ POItem (수주 라인)
├─ POSchedule (분할납품 일정)
├─ ReservedDocNo (예약 문서번호)
├─ POFcmsMatch (FCMS 매칭 결과)
└─ POProgressSnapshot (진행 현황 스냅샷)

OrphanFcmsDoc (고아 문서)
```

### 서비스 레이어

- `POService`: PO 생성/수정
- `ReservationService`: 예약번호 생성
- `MatchingService`: FCMS 매칭 검증
- `MonitoringService`: 진행 현황 집계

### Repository 레이어

- `PORepository`: PO 조회
- `FcmsRepository`: FCMS CDC 테이블 조회

---

## 📂 파일 구조

```
orders/
├── models.py                  # 데이터 모델 (7개 테이블)
├── admin.py                   # Django Admin 설정
├── urls.py                    # URL 라우팅
├── views.py                   # View 로직
├── forms.py                   # Form 클래스
├── services/                  # 비즈니스 로직
│   ├── po_service.py
│   ├── reservation_service.py
│   ├── matching_service.py
│   └── monitoring_service.py
├── repositories/              # 데이터 접근
│   ├── po_repository.py
│   └── fcms_repository.py
├── management/commands/       # 관리 명령
│   ├── backfill_po_from_fcms.py
│   └── check_po_fcms_match.py
├── templates/orders/          # HTML 템플릿
│   ├── po_list.html
│   ├── po_detail.html
│   ├── po_form.html
│   ├── backfill_review.html
│   └── manufacturing_schedule.html
├── docs/                      # 문서
│   ├── DATA_INTEGRITY_ISSUES.md
│   ├── DEPLOYMENT_GUIDE.md
│   └── MIGRATION_PLAN.md
└── README.md                  # 본 문서
```

---

## 🚀 설치 및 배포

### 1. 기존 CYNOW에 추가

```python
# config/settings.py
INSTALLED_APPS = [
    ...
    'orders',  # 추가
]
```

```python
# config/urls.py
urlpatterns = [
    ...
    path('orders/', include('orders.urls')),
]
```

### 2. 마이그레이션

```bash
python manage.py makemigrations orders
python manage.py migrate orders
```

### 3. 역수입 실행 (선택)

```bash
# Dry Run
python manage.py backfill_po_from_fcms --dry-run --days 30

# 실제 실행
python manage.py backfill_po_from_fcms --days 30 --limit 100
```

### 4. 배치 작업 설정

```bash
# crontab -e
# 매칭 확인 (매일 06:00)
0 6 * * * cd /opt/cynow/cynow && source venv/bin/activate && python manage.py check_po_fcms_match

# 진행 현황 갱신 (매일 08:00)
0 8 * * * cd /opt/cynow/cynow && source venv/bin/activate && python manage.py update_po_progress
```

---

## 📖 사용 가이드

### PO 생성

1. `/orders/create/` 접속
2. 거래처, 고객 발주번호, 품목, 수량 입력
3. 저장 → 자동으로 예약번호 생성

### 예약번호 확인

1. PO 상세 화면에서 "예약번호" 섹션 확인
2. FCMS 입력 시 추천된 번호 사용
3. 자동 매칭 확인 (배치 작업)

### 진행 현황 확인

1. PO 상세 화면에서 "진행 현황" 탭
2. 수주→충전→입고→출하 단계별 수량 확인
3. 진행률 그래프 표시

### 역수입 데이터 검토

1. `/orders/backfill/review/` 접속
2. "검토 필요" 필터링
3. 거래처/발주번호 수정
4. 고아 문서 매칭

---

## 🔧 관리 명령

### backfill_po_from_fcms

FCMS 기존 데이터로부터 PO 자동 생성

```bash
python manage.py backfill_po_from_fcms [옵션]

옵션:
  --days N          최근 N일 데이터 처리 (기본 90)
  --limit N         최대 N건 처리 (기본 1000)
  --dry-run         시뮬레이션만 (저장 안 함)
  --force           이미 처리된 문서도 재처리
```

### check_po_fcms_match

예약번호 매칭 확인 배치

```bash
python manage.py check_po_fcms_match [옵션]

옵션:
  --limit N         최대 N건 확인 (기본 100)
```

---

## 📊 Django Admin

`http://10.78.30.98/cynow/admin/` 접속 후 "수주 관리" 섹션

- **수주**: PO 목록, 상태 변경
- **예약 문서번호**: 예약번호 현황
- **PO-FCMS 매칭**: 매칭 결과 확인
- **고아 FCMS 문서**: 매칭 실패 문서 관리
- **PO 진행 현황**: 진행률 스냅샷

---

## 🛡️ 기존 시스템 보호

### 변경 금지 사항 준수

✅ **추가만 수행**:
- 새 Django 앱 (`orders`)
- 새 URL 경로 (`/orders/`)
- 새 DB 테이블 (`po_*`)

❌ **변경 없음**:
- 기존 모델/테이블
- 기존 URL/View
- 기존 템플릿/화면

### 롤백 방법

```python
# 즉시 비활성화
# config/settings.py
INSTALLED_APPS = [
    ...
    # 'orders',  # 주석 처리
]
```

또는

```bash
# 마이그레이션 되돌리기
python manage.py migrate orders zero
```

---

## 📋 정합성 이슈

자세한 내용은 [`docs/DATA_INTEGRITY_ISSUES.md`](docs/DATA_INTEGRITY_ISSUES.md) 참조

### 주요 이슈 유형

- (A) 필수 키 누락 → `needs_review=True`
- (B) 수량 불일치 → 검토 리스트
- (C) 고아 문서 → `OrphanFcmsDoc`
- (D) 분할 납품 → `POSchedule`

---

## 🔗 관련 문서

- [정합성 이슈 처리 가이드](docs/DATA_INTEGRITY_ISSUES.md)
- [배포 가이드](docs/DEPLOYMENT_GUIDE.md)
- [마이그레이션 계획](docs/MIGRATION_PLAN.md)

---

## 📞 지원

문제 발생 시:
1. 에러 로그 확인: `sudo journalctl -u cynow -n 100`
2. Django Admin에서 상태 확인
3. Dry Run으로 재시도

---

*CYNOW PO 관리 시스템 v1.0*  
*최종 수정: 2024-12-18*

