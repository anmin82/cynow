# PO 관리 시스템 마이그레이션 계획

> 안전한 DB 스키마 변경을 위한 상세 계획

---

## 📋 마이그레이션 개요

### 생성되는 테이블

1. `po_header` - 수주 헤더
2. `po_item` - 수주 라인
3. `po_schedule` - 분할납품 일정
4. `po_reserved_doc_no` - 예약 문서번호
5. `po_fcms_match` - PO-FCMS 매칭
6. `po_orphan_fcms_doc` - 고아 FCMS 문서
7. `po_progress_snapshot` - 진행 현황 스냅샷

### ⚠️ 기존 테이블 변경 없음

- 기존 CYNOW 테이블 (`cy_*`, `fcms_cdc.*`) 수정 없음
- `ADD TABLE` only
- 롤백 가능 (테이블 삭제만)

---

## 🚀 마이그레이션 실행 계획

### 1단계: 사전 확인

```bash
# 현재 마이그레이션 상태 확인
python manage.py showmigrations

# 미적용 마이그레이션 확인
python manage.py migrate --plan
```

### 2단계: 마이그레이션 파일 생성

```bash
# orders 앱 마이그레이션 생성
python manage.py makemigrations orders
```

**예상 출력:**
```
Migrations for 'orders':
  orders/migrations/0001_initial.py
    - Create model PO
    - Create model POItem
    - Create model POSchedule
    - Create model ReservedDocNo
    - Create model POFcmsMatch
    - Create model OrphanFcmsDoc
    - Create model POProgressSnapshot
```

### 3단계: SQL 미리보기

```bash
# 실행될 SQL 확인
python manage.py sqlmigrate orders 0001
```

**예상 SQL (일부):**
```sql
BEGIN;
--
-- Create model PO
--
CREATE TABLE "po_header" (
    "id" bigserial NOT NULL PRIMARY KEY,
    "po_no" varchar(50) NOT NULL UNIQUE,
    "supplier_user_code" varchar(50) NOT NULL,
    ...
);

--
-- Create model POItem
--
CREATE TABLE "po_item" (
    "id" bigserial NOT NULL PRIMARY KEY,
    "po_id" bigint NOT NULL,
    "line_no" integer NOT NULL,
    ...
    CONSTRAINT "po_item_po_id_fkey" FOREIGN KEY ("po_id")
        REFERENCES "po_header" ("id") ON DELETE CASCADE
);

-- 인덱스 생성
CREATE INDEX "po_header_supplier_user_code_idx" ON "po_header" ("supplier_user_code", "customer_order_no");
...

COMMIT;
```

### 4단계: 백업 (선택)

```bash
# PostgreSQL 백업
sudo -u postgres pg_dump cycy_db > /tmp/cycy_db_backup_$(date +%Y%m%d).sql

# 또는 특정 스키마만
sudo -u postgres pg_dump -n public cycy_db > /tmp/public_schema_backup.sql
```

### 5단계: 마이그레이션 실행

```bash
# Dry run 확인
python manage.py migrate orders --plan

# 실제 실행
python manage.py migrate orders

# 또는 특정 마이그레이션까지만
python manage.py migrate orders 0001
```

**예상 출력:**
```
Operations to perform:
  Apply all migrations: orders
Running migrations:
  Applying orders.0001_initial... OK
```

### 6단계: 검증

```bash
# 테이블 생성 확인
python manage.py dbshell

# PostgreSQL에서
\dt po_*
\d po_header
\q

# Django ORM 확인
python manage.py shell
>>> from orders.models import PO
>>> PO.objects.count()
0
```

---

## 🔄 롤백 계획

### 즉시 롤백 (테이블 삭제)

```bash
# orders 앱 마이그레이션 되돌리기
python manage.py migrate orders zero
```

**예상 SQL:**
```sql
BEGIN;
DROP TABLE IF EXISTS "po_progress_snapshot" CASCADE;
DROP TABLE IF EXISTS "po_orphan_fcms_doc" CASCADE;
DROP TABLE IF EXISTS "po_fcms_match" CASCADE;
DROP TABLE IF EXISTS "po_reserved_doc_no" CASCADE;
DROP TABLE IF EXISTS "po_schedule" CASCADE;
DROP TABLE IF EXISTS "po_item" CASCADE;
DROP TABLE IF EXISTS "po_header" CASCADE;
COMMIT;
```

### 수동 롤백 (SQL)

```sql
-- PostgreSQL에서 직접 실행
BEGIN;

DROP TABLE IF EXISTS po_progress_snapshot CASCADE;
DROP TABLE IF EXISTS po_orphan_fcms_doc CASCADE;
DROP TABLE IF EXISTS po_fcms_match CASCADE;
DROP TABLE IF EXISTS po_reserved_doc_no CASCADE;
DROP TABLE IF EXISTS po_schedule CASCADE;
DROP TABLE IF EXISTS po_item CASCADE;
DROP TABLE IF EXISTS po_header CASCADE;

COMMIT;
```

---

## 📊 마이그레이션 영향 분석

### 기존 시스템 영향도

| 항목 | 영향도 | 설명 |
|------|--------|------|
| 기존 테이블 | ✅ 없음 | 기존 테이블 변경 없음 |
| 기존 데이터 | ✅ 없음 | 데이터 손실 위험 없음 |
| 기존 View | ✅ 없음 | URL, View 변경 없음 |
| 성능 | ⚠️ 미미 | 인덱스 추가로 약간의 INSERT 오버헤드 |
| 스토리지 | ⚠️ 미미 | 약 10MB 추가 (1000건 PO 기준) |

### 예상 스토리지

```
po_header:          ~1MB (1000건)
po_item:            ~2MB (3000건)
po_reserved_doc_no: ~500KB (2000건)
po_fcms_match:      ~500KB (1000건)
...
총 예상:            ~10MB
```

---

## 🔍 마이그레이션 검증 체크리스트

### 실행 전
- [ ] 백업 완료
- [ ] SQL 미리보기 확인
- [ ] 기존 테이블 변경 없음 확인
- [ ] 롤백 계획 수립

### 실행 후
- [ ] 마이그레이션 성공 메시지 확인
- [ ] 테이블 생성 확인 (`\dt po_*`)
- [ ] 인덱스 생성 확인
- [ ] Django Admin에서 모델 접근 확인
- [ ] 기존 화면 정상 동작 확인

---

## 🚨 트러블슈팅

### 문제 1: 권한 오류

```
django.db.utils.OperationalError: permission denied for schema public
```

**해결:**
```sql
-- PostgreSQL에서
GRANT ALL PRIVILEGES ON SCHEMA public TO cynow_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cynow_user;
```

### 문제 2: 마이그레이션 충돌

```
django.db.migrations.exceptions.InconsistentMigrationHistory
```

**해결:**
```bash
# 마이그레이션 히스토리 확인
python manage.py showmigrations

# 문제 마이그레이션 fake
python manage.py migrate orders 0001 --fake

# 재시도
python manage.py migrate orders
```

### 문제 3: 테이블 이미 존재

```
django.db.utils.ProgrammingError: relation "po_header" already exists
```

**해결:**
```bash
# 기존 테이블 삭제 (주의!)
python manage.py dbshell

DROP TABLE IF EXISTS po_header CASCADE;

# 또는 fake 후 재실행
python manage.py migrate orders zero --fake
python manage.py migrate orders
```

---

## 📅 마이그레이션 일정

### 개발 환경
- [ ] 로컬 개발 PC에서 마이그레이션 테스트
- [ ] 백업/롤백 절차 검증

### 스테이징 환경 (있다면)
- [ ] 스테이징 DB 백업
- [ ] 마이그레이션 실행
- [ ] 통합 테스트
- [ ] 롤백 테스트

### 프로덕션 환경
- [ ] 운영 DB 백업
- [ ] 점검 시간 공지
- [ ] 마이그레이션 실행 (3분 소요)
- [ ] 검증 테스트
- [ ] 서비스 재개

---

## 📌 참고사항

### Django 마이그레이션 파일 구조

```python
# orders/migrations/0001_initial.py

from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]
    
    operations = [
        migrations.CreateModel(
            name='PO',
            fields=[
                ('id', models.BigAutoField(primary_key=True)),
                ('po_no', models.CharField(max_length=50, unique=True)),
                ...
            ],
            options={
                'db_table': 'po_header',
            },
        ),
        ...
    ]
```

### 마이그레이션 상태 확인

```bash
# 현재 적용된 마이그레이션
python manage.py showmigrations orders

# 출력 예시:
# orders
#  [X] 0001_initial
```

---

*마이그레이션 계획 버전: 1.0*  
*최종 수정: 2024-12-18*




















