# EndUser 예외 입력 빠른 가이드

## 방법 1: Django 관리자 페이지 (가장 쉬움) ⭐

### 단계별 안내

1. **서버 실행**
   ```bash
   python manage.py runserver
   ```

2. **관리자 페이지 접속**
   - URL: http://127.0.0.1:8000/admin/
   - 관리자 계정으로 로그인

3. **EndUser 예외 메뉴 선택**
   - 좌측 메뉴에서 **Core** → **EndUser 예외** 클릭

4. **예외 추가**
   - 우측 상단 **EndUser 예외 추가** 버튼 클릭
   - 다음 정보 입력:
     - **용기번호**: 예) `22DH0001`
     - **EndUser**: 예) `LGD`
     - **사유**: 예) `CF4 YC 440L LGD 납품 전용`
     - **활성화**: ✅ 체크
   - **저장** 버튼 클릭

5. **일괄 입력 (여러 개)**
   - 목록 페이지에서 여러 개를 한 번에 추가하려면
   - 각각 개별로 추가하거나
   - 방법 2 (CSV 파일) 사용 권장

### 장점
- ✅ 직관적이고 쉬움
- ✅ 실시간으로 확인 가능
- ✅ 수정/삭제가 편리

---

## 방법 2: CSV 파일로 일괄 입력 (대량 입력 시 권장)

### 1단계: CSV 파일 생성

`lgd_exceptions.csv` 파일을 생성하고 다음 형식으로 작성:

```csv
cylinder_no,enduser,reason
22DH0001,LGD,CF4 YC 440L LGD 납품 전용
22DH0002,LGD,CF4 YC 440L LGD 납품 전용
22DH0003,LGD,CF4 YC 440L LGD 납품 전용
22DH0004,LGD,CF4 YC 440L LGD 납품 전용
...
(29개 용기번호)
```

### 2단계: 명령어 실행

```bash
# 실제 입력
python manage.py load_enduser_exceptions --file lgd_exceptions.csv

# 미리보기 (실제 저장 안 함)
python manage.py load_enduser_exceptions --file lgd_exceptions.csv --dry-run
```

### 장점
- ✅ 대량 입력 시 빠름
- ✅ 파일로 관리 가능
- ✅ 재사용 가능

---

## 방법 3: 단일 입력 (명령어)

```bash
python manage.py load_enduser_exceptions \
  --cylinder-no 22DH0001 \
  --enduser LGD \
  --reason "CF4 YC 440L LGD 납품 전용"
```

### 장점
- ✅ 빠른 단일 입력
- ✅ 스크립트에 포함 가능

---

## 방법 4: 직접 SQL (고급)

PostgreSQL에 직접 접속하여 입력:

```sql
INSERT INTO cy_enduser_exception 
(cylinder_no, enduser, reason, is_active)
VALUES 
('22DH0001', 'LGD', 'CF4 YC 440L LGD 납품 전용', TRUE),
('22DH0002', 'LGD', 'CF4 YC 440L LGD 납품 전용', TRUE),
('22DH0003', 'LGD', 'CF4 YC 440L LGD 납품 전용', TRUE)
ON CONFLICT (cylinder_no) 
DO UPDATE SET 
    enduser = EXCLUDED.enduser,
    reason = EXCLUDED.reason,
    is_active = TRUE,
    updated_at = NOW();
```

### 장점
- ✅ 복잡한 조건으로 일괄 입력 가능
- ✅ 패턴 기반 자동 생성 가능

---

## 입력 후 확인

### 1. 관리자 페이지에서 확인
- http://127.0.0.1:8000/admin/core/enduserexception/
- 입력된 예외 목록 확인

### 2. 스냅샷 갱신 (자동 또는 수동)

**자동 갱신** (Trigger 설정 시):
- 예외 입력 시 자동으로 스냅샷이 갱신됩니다

**수동 갱신**:
```bash
# 전체 갱신
python manage.py sync_cylinder_current

# 증분 갱신 (최근 1시간)
python manage.py sync_cylinder_current --incremental
```

### 3. 대시보드에서 확인
- http://127.0.0.1:8000/dashboard/
- 해당 용기의 EndUser가 변경되었는지 확인

---

## 예시: CF4 YC 440L LGD 납품 전용 29병 입력

### CSV 파일 예시

`lgd_exceptions.csv`:
```csv
cylinder_no,enduser,reason
22DH0001,LGD,CF4 YC 440L LGD 납품 전용
22DH0002,LGD,CF4 YC 440L LGD 납품 전용
22DH0003,LGD,CF4 YC 440L LGD 납품 전용
22DH0004,LGD,CF4 YC 440L LGD 납품 전용
22DH0005,LGD,CF4 YC 440L LGD 납품 전용
22DH0006,LGD,CF4 YC 440L LGD 납품 전용
22DH0007,LGD,CF4 YC 440L LGD 납품 전용
22DH0008,LGD,CF4 YC 440L LGD 납품 전용
22DH0009,LGD,CF4 YC 440L LGD 납품 전용
22DH0010,LGD,CF4 YC 440L LGD 납품 전용
22DH0011,LGD,CF4 YC 440L LGD 납품 전용
22DH0012,LGD,CF4 YC 440L LGD 납품 전용
22DH0013,LGD,CF4 YC 440L LGD 납품 전용
22DH0014,LGD,CF4 YC 440L LGD 납품 전용
22DH0015,LGD,CF4 YC 440L LGD 납품 전용
22DH0016,LGD,CF4 YC 440L LGD 납품 전용
22DH0017,LGD,CF4 YC 440L LGD 납품 전용
22DH0018,LGD,CF4 YC 440L LGD 납품 전용
22DH0019,LGD,CF4 YC 440L LGD 납품 전용
22DH0020,LGD,CF4 YC 440L LGD 납품 전용
22DH0021,LGD,CF4 YC 440L LGD 납품 전용
22DH0022,LGD,CF4 YC 440L LGD 납품 전용
22DH0023,LGD,CF4 YC 440L LGD 납품 전용
22DH0024,LGD,CF4 YC 440L LGD 납품 전용
22DH0025,LGD,CF4 YC 440L LGD 납품 전용
22DH0026,LGD,CF4 YC 440L LGD 납품 전용
22DH0027,LGD,CF4 YC 440L LGD 납품 전용
22DH0028,LGD,CF4 YC 440L LGD 납품 전용
22DH0029,LGD,CF4 YC 440L LGD 납품 전용
```

실행:
```bash
python manage.py load_enduser_exceptions --file lgd_exceptions.csv
```

---

## 주의사항

1. **예외 우선순위**: 예외 테이블이 기본값 테이블보다 우선합니다.
2. **스냅샷 갱신**: 예외 입력 후 스냅샷이 자동으로 갱신됩니다 (Trigger 설정 시).
3. **중복 입력**: 같은 용기번호로 다시 입력하면 업데이트됩니다.
4. **비활성화**: 삭제하지 않고 `is_active = FALSE`로 비활성화할 수 있습니다.










