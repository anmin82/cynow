# EndUser 예외 입력 가이드

## 개요

EndUser 예외는 특정 용기번호에 대해 기본값과 다른 EndUser를 지정하는 기능입니다.

예: CF4 YC 440L 용기 중 LGD 납품 전용 29병을 예외로 지정

## 입력 방법

### 1. Django 관리자 페이지 (권장)

1. 서버 실행: `python manage.py runserver`
2. 관리자 페이지 접속: http://127.0.0.1:8000/admin/
3. 로그인 후 **Core > EndUser 예외** 메뉴 선택
4. **EndUser 예외 추가** 버튼 클릭
5. 다음 정보 입력:
   - **용기번호**: 예) `22DH0001`
   - **EndUser**: 예) `LGD`
   - **사유**: 예) `LGD 납품 전용`
   - **활성화**: 체크
6. 저장

**장점**: 직관적이고 실시간으로 확인 가능

### 2. 관리 명령어 (일괄 입력)

#### CSV 파일로 일괄 입력

1. CSV 파일 생성 (`exceptions.csv`):
```csv
cylinder_no,enduser,reason
22DH0001,LGD,LGD 납품 전용
22DH0002,LGD,LGD 납품 전용
22DH0003,LGD,LGD 납품 전용
...
```

2. 명령어 실행:
```bash
python manage.py load_enduser_exceptions --file exceptions.csv
```

#### 단일 입력

```bash
python manage.py load_enduser_exceptions --cylinder-no 22DH0001 --enduser LGD --reason "LGD 납품 전용"
```

#### 미리보기 (실제 저장 안 함)

```bash
python manage.py load_enduser_exceptions --file exceptions.csv --dry-run
```

**장점**: 대량 입력 시 편리

### 3. 직접 SQL 입력

PostgreSQL에 직접 접속하여 입력:

```sql
INSERT INTO cy_enduser_exception 
(cylinder_no, enduser, reason, is_active)
VALUES 
('22DH0001', 'LGD', 'LGD 납품 전용', TRUE),
('22DH0002', 'LGD', 'LGD 납품 전용', TRUE),
('22DH0003', 'LGD', 'LGD 납품 전용', TRUE)
ON CONFLICT (cylinder_no) 
DO UPDATE SET 
    enduser = EXCLUDED.enduser,
    reason = EXCLUDED.reason,
    is_active = TRUE,
    updated_at = NOW();
```

**장점**: 복잡한 조건으로 일괄 입력 가능

## 예외 확인

### 관리자 페이지에서 확인

1. http://127.0.0.1:8000/admin/core/enduserexception/
2. 입력된 예외 목록 확인

### SQL로 확인

```sql
SELECT cylinder_no, enduser, reason, is_active, updated_at
FROM cy_enduser_exception
WHERE is_active = TRUE
ORDER BY updated_at DESC;
```

### 스냅샷 테이블에서 확인

```sql
SELECT 
    cylinder_no,
    dashboard_enduser,
    raw_usage_place
FROM cy_cylinder_current
WHERE dashboard_enduser != 'SDC'
ORDER BY dashboard_enduser, cylinder_no;
```

## 예외 비활성화

예외를 삭제하지 않고 비활성화:

### 관리자 페이지
- 해당 예외 선택 → **활성화** 체크 해제 → 저장

### SQL
```sql
UPDATE cy_enduser_exception
SET is_active = FALSE, updated_at = NOW()
WHERE cylinder_no = '22DH0001';
```

## 주의사항

1. **예외 우선순위**: 예외 테이블이 기본값 테이블보다 우선합니다.
2. **스냅샷 갱신**: 예외 입력 후 스냅샷이 자동으로 갱신됩니다 (Trigger 설정 시).
3. **중복 입력**: 같은 용기번호로 다시 입력하면 업데이트됩니다.

## 예시: CF4 YC 440L LGD 납품 전용 29병 입력

### 방법 1: CSV 파일

1. `lgd_exceptions.csv` 파일 생성:
```csv
cylinder_no,enduser,reason
22DH0001,LGD,CF4 YC 440L LGD 납품 전용
22DH0002,LGD,CF4 YC 440L LGD 납품 전용
...
(29개 용기번호)
```

2. 실행:
```bash
python manage.py load_enduser_exceptions --file lgd_exceptions.csv
```

### 방법 2: 관리자 페이지

29개 용기를 하나씩 입력하거나, 여러 개를 한 번에 추가할 수 있습니다.

### 방법 3: SQL (용기번호 패턴이 있는 경우)

```sql
-- 예: 22DH0001부터 22DH0029까지
INSERT INTO cy_enduser_exception (cylinder_no, enduser, reason, is_active)
SELECT 
    '22DH' || LPAD(CAST(seq AS TEXT), 4, '0'),
    'LGD',
    'CF4 YC 440L LGD 납품 전용',
    TRUE
FROM generate_series(1, 29) AS seq
ON CONFLICT (cylinder_no) 
DO UPDATE SET 
    enduser = EXCLUDED.enduser,
    reason = EXCLUDED.reason,
    is_active = TRUE,
    updated_at = NOW();
```

## 스냅샷 갱신 확인

예외 입력 후 스냅샷이 자동으로 갱신되었는지 확인:

```bash
python manage.py sync_cylinder_current --incremental
```

또는 특정 용기만 갱신:

```sql
SELECT sync_cylinder_current_single('22DH0001');
```










