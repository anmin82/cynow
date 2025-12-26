# PO 관리 시스템 무중단 배포 가이드

> 기존 CYNOW 시스템에 영향을 주지 않고 안전하게 PO 관리 기능을 추가하는 단계별 배포 절차

---

## 🎯 배포 원칙

### ✅ 기존 시스템 보호 원칙

1. **완전 분리**: 새 Django 앱 (`orders`)으로 독립 배포
2. **URL 분리**: `/orders/` 경로로만 접근, 기존 경로 무영향
3. **DB 안전**: ADD TABLE only, 기존 테이블 수정 없음
4. **점진적 공개**: Feature Flag로 필요시 비활성화 가능
5. **롤백 가능**: 언제든지 앱 비활성화로 즉시 복구

---

## 📋 배포 전 체크리스트

- [ ] 로컬 개발 환경에서 테스트 완료
- [ ] 마이그레이션 파일 검증 완료
- [ ] FCMS CDC 테이블 접근 권한 확인
- [ ] 백업 완료 (DB, 코드)
- [ ] 배포 롤백 계획 수립
- [ ] 관리자 계정 로그인 확인

---

## 🚀 배포 단계 (Step-by-Step)

### 1단계: 소스 코드 업로드 (10분)

**로컬에서 실행:**

```powershell
cd C:\cynow

# 새 orders 앱 전송
scp -r orders root@10.78.30.98:/opt/cynow/cynow/

# 기존 파일 수정사항 전송 (config만)
scp config/settings.py config/urls.py root@10.78.30.98:/opt/cynow/cynow/config/
```

**확인:**
```bash
ssh root@10.78.30.98
ls -la /opt/cynow/cynow/orders/
```

---

### 2단계: 설정 파일 수정 (5분)

**서버에서 실행:**

```bash
sudo su - cynow
cd /opt/cynow/cynow
source venv/bin/activate

# settings.py 확인
nano config/settings.py
```

**변경 내용 (최소):**

```python
# config/settings.py

INSTALLED_APPS = [
    ...
    'alerts',
    'orders',  # 🆕 추가
]

# Feature Flag (선택)
ENABLE_PO_MANAGEMENT = True  # False로 설정하면 비활성화
```

**URL 설정 확인:**

```python
# config/urls.py

urlpatterns = [
    ...
    path('alerts/', include('alerts.urls')),
    path('orders/', include('orders.urls')),  # 🆕 추가
]
```

---

### 3단계: 마이그레이션 실행 (10분)

**⚠️ 중요: Dry Run 먼저 실행**

```bash
# 마이그레이션 계획 확인
python manage.py makemigrations orders --dry-run

# 실제 마이그레이션 파일 생성
python manage.py makemigrations orders

# SQL 미리보기 (안전 확인)
python manage.py sqlmigrate orders 0001

# 실행 전 확인
python manage.py migrate --plan
```

**문제 없으면 실행:**

```bash
# 마이그레이션 실행
python manage.py migrate orders

# 결과 확인
python manage.py showmigrations orders
```

**예상 출력:**
```
orders
 [X] 0001_initial
```

---

### 4단계: 정적 파일 수집 (2분)

```bash
# 정적 파일 재수집 (CSS/JS가 있다면)
python manage.py collectstatic --noinput
```

---

### 5단계: 서비스 재시작 (3분)

**⚠️ 무중단 배포 방법 (Graceful Restart)**

```bash
# cynow 사용자에서 나가기
exit

# Gunicorn PID 확인
sudo systemctl status cynow

# Graceful Restart (접속 끊김 최소화)
sudo systemctl reload cynow

# 또는 일반 재시작
sudo systemctl restart cynow

# 상태 확인
sudo systemctl status cynow
```

**로그 모니터링:**

```bash
# 실시간 로그 확인
sudo tail -f /var/log/cynow/error.log
sudo journalctl -u cynow -f
```

---

### 6단계: 배포 검증 (5분)

#### 6-1. 서비스 정상 동작 확인

```bash
# HTTP 응답 확인
curl -I http://10.78.30.98/cynow/

# 200 OK 확인
```

#### 6-2. PO 관리 화면 접근 확인

**브라우저에서:**

1. `http://10.78.30.98/cynow/orders/` 접속
2. 로그인 (관리자 계정)
3. PO 리스트 화면 표시 확인

#### 6-3. Django Admin 확인

1. `http://10.78.30.98/cynow/admin/` 접속
2. "수주 관리" 섹션 확인
3. PO, 예약번호 등 모델 표시 확인

#### 6-4. 기존 화면 정상 동작 확인

**⚠️ 중요: 기존 기능 회귀 테스트**

- [ ] 대시보드 (`/cynow/`) 정상 표시
- [ ] 용기 리스트 (`/cynow/cylinders/`) 정상 조회
- [ ] 히스토리 (`/cynow/history/`) 정상 동작
- [ ] 알림 (`/cynow/alerts/`) 정상 동작

---

### 7단계: 역수입(Backfill) 실행 (선택, 20분)

**⚠️ 프로덕션 데이터 작업이므로 신중하게**

#### 7-1. Dry Run 테스트

```bash
sudo su - cynow
cd /opt/cynow/cynow
source venv/bin/activate

# 시뮬레이션 (저장 안 함)
python manage.py backfill_po_from_fcms --dry-run --days 7 --limit 10
```

**결과 확인:**
```
=== FCMS 데이터 역수입 시작 ===
- 기간: 최근 7일
- 최대 처리: 10건
- Dry Run: 예

1️⃣ FCMS 주문 데이터 조회 중...
   ✓ 10건 조회

2️⃣ PO 생성/매칭 처리 중...
   [생성] FP240001
   [검토필요] FP240002
   ...

✅ 처리 완료
총 확인: 10건
  ✓ 생성: 7건
  - 건너뜀: 1건
  ⚠ 검토필요: 2건

⚠️ Dry Run 모드: 실제 저장되지 않음
```

#### 7-2. 실제 실행 (단계적)

```bash
# 1단계: 최근 7일, 소량
python manage.py backfill_po_from_fcms --days 7 --limit 20

# 결과 확인 후
# 2단계: 최근 30일
python manage.py backfill_po_from_fcms --days 30 --limit 100

# 3단계: 전체 (90일)
python manage.py backfill_po_from_fcms --days 90 --limit 1000
```

---

## 🔄 롤백 절차 (문제 발생 시)

### 즉시 롤백 (5분 이내)

#### 방법 1: Feature Flag 비활성화 (가장 빠름)

```bash
# settings.py 수정
sudo su - cynow
cd /opt/cynow/cynow
nano config/settings.py
```

```python
# Feature Flag를 False로 변경
ENABLE_PO_MANAGEMENT = False
```

```bash
# 재시작
exit
sudo systemctl restart cynow
```

#### 방법 2: URL 비활성화

```python
# config/urls.py에서 주석 처리
urlpatterns = [
    ...
    # path('orders/', include('orders.urls')),  # 비활성화
]
```

#### 방법 3: 앱 제거

```python
# config/settings.py
INSTALLED_APPS = [
    ...
    # 'orders',  # 비활성화
]
```

```bash
sudo systemctl restart cynow
```

### 완전 롤백 (마이그레이션 되돌리기)

**⚠️ 주의: 생성된 PO 데이터가 모두 삭제됨**

```bash
# 마이그레이션 되돌리기
python manage.py migrate orders zero

# 확인
python manage.py showmigrations orders
```

**예상 출력:**
```
orders
 [ ] 0001_initial
```

---

## 🚨 트러블슈팅

### 문제 1: 500 Internal Server Error

**증상:**
```
http://10.78.30.98/cynow/orders/ → 500 오류
```

**원인:**
- 마이그레이션 미실행
- FCMS CDC 테이블 접근 권한 없음
- Python 의존성 누락

**해결:**
```bash
# 로그 확인
sudo journalctl -u cynow -n 100

# 마이그레이션 상태 확인
python manage.py showmigrations orders

# 마이그레이션 실행
python manage.py migrate orders

# 재시작
sudo systemctl restart cynow
```

### 문제 2: ImportError

**증상:**
```
ModuleNotFoundError: No module named 'orders'
```

**원인:**
- orders 폴더가 정확히 업로드되지 않음
- `__init__.py` 파일 누락

**해결:**
```bash
# 폴더 구조 확인
ls -la /opt/cynow/cynow/orders/
ls -la /opt/cynow/cynow/orders/__init__.py

# 재업로드
scp -r orders root@10.78.30.98:/opt/cynow/cynow/
```

### 문제 3: FCMS CDC 테이블 조회 실패

**증상:**
```
relation "fcms_cdc.tr_orders" does not exist
```

**원인:**
- PostgreSQL 스키마 경로 설정 누락
- CDC 데이터 미동기화

**해결:**
```bash
# PostgreSQL 접속
sudo -u postgres psql cycy_db

# 스키마 확인
\dn

# 테이블 확인
\dt fcms_cdc.*

# settings.py 확인
OPTIONS': {
    'options': '-c search_path=public,fcms_cdc'
}
```

---

## 📊 배포 후 모니터링

### 체크 포인트 (배포 후 1주일)

- [ ] 일 1회: PO 생성 건수 확인
- [ ] 일 1회: 에러 로그 확인
- [ ] 주 1회: 역수입 실행 (신규 데이터)
- [ ] 주 1회: 예약번호 매칭 배치 실행

### 모니터링 명령

```bash
# PO 통계 확인 (Django shell)
python manage.py shell

>>> from orders.models import PO
>>> PO.objects.count()
>>> PO.objects.filter(needs_review=True).count()
>>> PO.objects.filter(is_backfilled=True).count()
```

---

## ✅ 배포 완료 체크리스트

- [ ] orders 앱 소스 코드 업로드 완료
- [ ] settings.py에 'orders' 추가 완료
- [ ] urls.py에 'orders/' 경로 추가 완료
- [ ] 마이그레이션 실행 완료
- [ ] Gunicorn 재시작 완료
- [ ] PO 리스트 화면 접근 확인
- [ ] Django Admin에서 PO 관리 가능 확인
- [ ] 기존 대시보드 정상 동작 확인
- [ ] 기존 용기 리스트 정상 동작 확인
- [ ] 에러 로그 없음 확인
- [ ] (선택) Backfill 실행 완료

---

## 📅 배포 일정 예시

### Phase 1: 개발 환경 (로컬)
- [ ] 모델 설계 및 테스트
- [ ] 서비스 로직 구현
- [ ] Admin 설정 및 검증

### Phase 2: 스테이징 (있다면)
- [ ] 스테이징 서버 배포
- [ ] 실제 FCMS 데이터로 테스트
- [ ] Backfill 검증

### Phase 3: 프로덕션 (운영)
- [ ] 본 가이드 따라 배포
- [ ] 사용자 교육
- [ ] 1주일 모니터링

---

*배포 가이드 버전: 1.0*  
*최종 수정: 2024-12-18*  
*CYNOW PO 관리 시스템*



















