# PO 번호 수정 - 마이그레이션 및 배포 가이드

## 🚨 변경 사항 요약

### 문제점
- **PO 번호가 2개 존재**했습니다:
  1. `po_no` (시스템 내부 생성, PO24XXXX)
  2. `customer_order_no` (고객발주번호)

### 해결책
- **PO 번호는 `customer_order_no` 하나만 존재**
- `po_no` 필드 완전 제거
- `customer_order_no`를 UNIQUE KEY로 변경

---

## 📋 수정된 파일 목록

### Python 파일
```
✅ orders/models.py          - po_no 제거, customer_order_no를 unique=True로
✅ orders/views.py           - 모든 po_no → customer_order_no 변경
✅ orders/urls.py            - URL 파라미터 customer_order_no로 변경
✅ orders/forms.py           - label 수정
```

### 템플릿 파일
```
✅ orders/templates/orders/po_list.html    - PO 번호 컬럼 하나만 표시
✅ orders/templates/orders/po_detail.html  - po_no 제거
✅ orders/templates/orders/po_form.html    - (변경 불필요, 이미 올바름)
```

---

## 🔧 배포 절차

### 1️⃣ 데이터 확인 (중요!)

**서버에 SSH 접속**
```bash
ssh cynow@10.78.30.98
cd /opt/cynow/cynow
source venv/bin/activate
```

**현재 PO 데이터 확인**
```bash
python manage.py shell
```

```python
from orders.models import PO

# 현재 PO 개수 확인
count = PO.objects.count()
print(f"현재 PO 개수: {count}")

# 데이터가 있으면 백업 필요
if count > 0:
    print("⚠️ 데이터가 존재합니다! 백업이 필요합니다.")
    for po in PO.objects.all()[:5]:
        print(f"  - {po.po_no}: {po.customer_order_no}")
else:
    print("✅ 데이터가 없습니다. 안전하게 진행 가능합니다.")

exit()
```

### 2️⃣-A 데이터가 **없는 경우** (권장)

가장 간단한 방법: **기존 테이블 삭제 후 재생성**

```bash
cd /opt/cynow/cynow
source venv/bin/activate

# 1. 기존 마이그레이션 제거
rm -f orders/migrations/0001_initial.py

# 2. 파일 업로드 (로컬에서)
# scp로 수정된 파일들을 전송

# 3. 새 마이그레이션 생성
python manage.py makemigrations orders

# 4. 기존 테이블 DROP (데이터 없으므로 안전)
python manage.py dbshell
```

PostgreSQL에서:
```sql
DROP TABLE IF EXISTS po_header CASCADE;
DROP TABLE IF EXISTS po_item CASCADE;
DROP TABLE IF EXISTS po_reserved_doc_no CASCADE;
DROP TABLE IF EXISTS po_progress_snapshot CASCADE;
DROP TABLE IF EXISTS po_schedule CASCADE;
DROP TABLE IF EXISTS po_fcms_match CASCADE;
DROP TABLE IF EXISTS po_orphan_fcms_doc CASCADE;

-- 마이그레이션 기록도 삭제
DELETE FROM django_migrations WHERE app = 'orders';

\q
```

```bash
# 5. 새 테이블 생성
python manage.py migrate orders

# 6. 확인
python manage.py check
```

### 2️⃣-B 데이터가 **있는 경우**

**⚠️ 주의: 데이터 손실 위험!**

```bash
cd /opt/cynow/cynow
source venv/bin/activate

# 1. 데이터 백업 (JSON 형식)
python manage.py dumpdata orders > orders_backup_$(date +%Y%m%d_%H%M%S).json

# 2. customer_order_no를 임시로 저장
python manage.py shell
```

```python
from orders.models import PO

# customer_order_no를 CSV로 저장
with open('/tmp/po_customer_order_nos.csv', 'w') as f:
    f.write('id,po_no,customer_order_no,supplier_user_code,supplier_user_name\n')
    for po in PO.objects.all():
        f.write(f'{po.id},{po.po_no},{po.customer_order_no},{po.supplier_user_code},{po.supplier_user_name}\n')

print("✅ 백업 완료: /tmp/po_customer_order_nos.csv")
exit()
```

```bash
# 3. 테이블 삭제 및 재생성 (2-A 방법과 동일)

# 4. 데이터 복원 (customer_order_no 기준으로)
python manage.py shell
```

```python
from orders.models import PO
import csv

with open('/tmp/po_customer_order_nos.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        PO.objects.create(
            customer_order_no=row['customer_order_no'],
            supplier_user_code=row['supplier_user_code'],
            supplier_user_name=row['supplier_user_name'],
            status='DRAFT',  # 기본값
            received_at='2024-12-18 00:00:00',  # 기본값
        )

print(f"✅ {PO.objects.count()}건 복원 완료")
exit()
```

### 3️⃣ 파일 전송 (로컬 → 서버)

**로컬에서 실행:**
```bash
cd c:\cynow

# Python 파일 전송
scp orders/models.py cynow@10.78.30.98:/opt/cynow/cynow/orders/
scp orders/views.py cynow@10.78.30.98:/opt/cynow/cynow/orders/
scp orders/urls.py cynow@10.78.30.98:/opt/cynow/cynow/orders/
scp orders/forms.py cynow@10.78.30.98:/opt/cynow/cynow/orders/

# 템플릿 파일 전송
scp orders/templates/orders/po_list.html cynow@10.78.30.98:/opt/cynow/cynow/orders/templates/orders/
scp orders/templates/orders/po_detail.html cynow@10.78.30.98:/opt/cynow/cynow/orders/templates/orders/
```

### 4️⃣ 서버 재시작

```bash
ssh cynow@10.78.30.98

# Gunicorn 재시작
sudo systemctl restart gunicorn-cynow
sudo systemctl status gunicorn-cynow

# 로그 확인
sudo journalctl -u gunicorn-cynow -f
```

### 5️⃣ 동작 확인

**브라우저에서 테스트:**
```
✅ 수주 목록:    http://10.78.30.98/cynow/orders/
✅ 수주 등록:    http://10.78.30.98/cynow/orders/new/
✅ 수주 상세:    http://10.78.30.98/cynow/orders/{customer_order_no}/
```

**확인 사항:**
- [ ] 수주 목록에서 PO 번호 컬럼이 **1개**만 표시되는가?
- [ ] "PO번호(고객발주번호)" 라는 라벨이 보이는가?
- [ ] 수주 등록 시 고객발주번호만 입력하는가?
- [ ] 상세 페이지에서 po_no가 사라졌는가?

---

## 🔄 롤백 (문제 발생 시)

### 방법 1: 백업 복원
```bash
cd /opt/cynow/cynow
source venv/bin/activate

# JSON 백업 복원
python manage.py loaddata orders_backup_YYYYMMDD_HHMMSS.json
```

### 방법 2: 코드 롤백
```bash
cd /opt/cynow/cynow
git checkout HEAD~1 -- orders/

sudo systemctl restart gunicorn-cynow
```

---

## ✅ 검증 체크리스트

- [ ] `po_no` 필드가 완전히 제거되었는가?
- [ ] `customer_order_no`가 UNIQUE 제약조건을 가지고 있는가?
- [ ] 리스트 화면에서 PO 번호 컬럼이 **1개**만 보이는가?
- [ ] URL이 `/orders/{customer_order_no}/`로 작동하는가?
- [ ] 수주 등록 폼에서 customer_order_no만 입력하는가?
- [ ] 모든 페이지에서 "PO번호(고객발주번호)" 라벨이 일관되게 표시되는가?

---

## 📝 변경 이유

**원칙:**
> PO 번호는 오직 하나이며, 그것은 "고객발주번호(customer_order_no)"이다.
> 리스트/화면/테이블에 PO 번호가 2개 이상 존재하면 설계 오류로 간주한다.

**기존 문제:**
- 시스템 내부 생성 번호 `po_no`와 고객 발주번호 `customer_order_no` 혼재
- 사용자 혼란 가능성
- 불필요한 번호 생성 로직

**개선 결과:**
- PO 번호 = 고객발주번호 = `customer_order_no` 하나로 통일
- 명확하고 단순한 식별 체계
- 고객과 소통하는 실제 번호 기준

---

## 🚀 배포 완료 후

1. 사용자에게 변경 사항 공지
2. 수주 입력 테스트 실시
3. 모니터링 강화 (에러 로그 확인)

---

**작성일:** 2024-12-18  
**버전:** 1.0  
**작성자:** CYNOW 개발팀


















