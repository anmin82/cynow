# CYNOW (CYLINDER NOW) — 설계서/계약서 v1.0 (DB·메뉴·AI프롬프트 포함)

> 목적: **FCMS(Oracle) → Debezium/Kafka → PostgreSQL(동기화 테이블 + VIEW)** 를 *진실 데이터*로 삼아  
> 용기 수량을 **통제/보고**하고, 별도의 **계획(FORECAST/SCHEDULED)** 및 **변화이력(HISTORY)** 로 예측·분석을 지원한다.  
> *주의:* 회수예상량 기능은 참고용이며 현재 통제/보고 수치에는 **절대 반영하지 않는다.**

---

## 0. 핵심 원칙 (반드시 준수)

1) **SSOT (Single Source of Truth) = PostgreSQL VIEW**
- “현재 현황”은 오직 VIEW 기준
- VIEW는 FCMS 동기화 결과로 자동 갱신되며 CYNOW에서 수정/보정하지 않는다

2) **입력(계획/수동스냅샷)은 별도 테이블에만 저장**
- FORECAST/SCHEDULED/HISTORY는 VIEW를 바꾸지 않는다

3) **조회는 로그인 없이 가능 / 입력은 로그인 필요**
- 비로그인: 전체 조회 가능(대시보드/현황/요약/용기/알림/보고서/분석)
- 로그인: 계획 입력, 수동 스냅샷 저장 등 “쓰기” 기능만 가능

---

## 1. 용기 개념 정의

### 1.1 용기종류(Cylinder Type)
하나의 **고유한 용기종류**는 아래 속성 조합으로 정의한다.
- 가스명(gas_name)
- 용기용량(capacity)
- 밸브스펙(valve_spec)
- 용기스펙(cylinder_spec)
- 사용처(usage_place)

### 1.2 개별 용기(Cylinder)
- 각 용기는 **중복되지 않는 용기번호(cylinder_no)** 를 가진다.
- 수량은 **용기번호 개수**로 관리한다.
- 용기번호는 **현재 상태(status)** 와 **현재 위치(location)** 의 속성을 가진다.

### 1.3 상태(Status) 표준 분류
- 보관, 충전, 분석, 창입, 출하, 이상, 폐기

---

## 2. 시스템 메뉴(요구사항 고정)

- **대시보드(Dashboard)**: 모든 용기종류 한눈에, 가용수량/0-되기 예상/핵심 위험 표시  
- **현황(Detail)**: 선택 용기종류의 상세 데이터(상태·위치·추이·관련 지표)  
- **요약(Summary)**: 용기종류별 그래프/표/통계  
- **용기(Cylinders)**: 용기번호 리스트 + 필터(상태/종류/위치/기간 등)  
- **알림(Alerts)**: 용기종류가 아닌 **위험도 기준** 리스트 + 해결 조언  
- **보고서(Reports)**: 주간/월간 종합 보고서 조회/출력  
- **계획(Plans)** *(로그인 필요)*: FORECAST(출하 계획) / SCHEDULED(투입 계획) 입력  
- **변화 이력/분석(History & Analytics)**: VIEW 스냅샷 저장 + 기간별 변화/통계/출력

---

## 3. 연동 구조(현황)

- FCMS Oracle DB: **10.78.30.18**
- Debezium CDC → Kafka: **10.78.30.98**
- Kafka Sink → PostgreSQL: **10.78.30.98:5434**
- 동기화 테이블 갱신 → VIEW 갱신 → CYNOW는 VIEW를 “진실 데이터”로 사용

---

# 1) DB 모델 설계 (ERD 수준 / 계약서)

## 1. 소스(동기화) 테이블 — 읽기 전용
> 실제 테이블명은 Debezium/JDBC Sink 설정에 맞춰 들어온 것을 사용한다.  
> 여기서는 “예시 prefix = fcms_” 로 표기한다. (프로젝트에서 실제명 매핑 테이블로 고정 가능)

### 1.1 예시: 동기화 테이블(참조용)
- fcms_cylinders (개별 용기 마스터/상태/위치 등)
- fcms_cylinder_specs (용기 스펙)
- fcms_valve_specs (밸브 스펙)
- fcms_items / fcms_parameters / fcms_latest_statuses (현황 계산에 필요한 보조)

> **규칙:** 동기화 테이블 스키마 변경은 “연동 영역”이며, CYNOW의 핵심은 **VIEW** 계약으로 보호한다.

---

## 2. 진실 VIEW (SSOT) — 반드시 존재해야 함
> CYNOW 기능의 기준이 되는 “집계 결과” VIEW.  
> 이 VIEW는 **용기종류 × 상태 × 위치** 단위로 수량을 제공할 수 있어야 한다.

### 2.1 `vw_cynow_inventory` (필수)
**목적:** 대시보드/현황/요약/알림/보고서의 현재값 기준

**필드(계약):**
- cylinder_type_key (가스명/용량/밸브/스펙/사용처를 묶은 키 — 문자열 또는 해시)
- gas_name
- capacity
- valve_spec
- cylinder_spec
- usage_place
- status  (표준 상태)
- location (현재 위치/거점/창고)
- qty (수량 = distinct cylinder_no count)
- updated_at (VIEW 생성 기준 시각 or 소스 최신 시각)

> **주의:** qty는 “현재 상태 기준”이며, 회수예상량/예측값이 섞이면 계약 위반.

### 2.2 `vw_cynow_cylinder_list` (권장)
**목적:** 용기 메뉴(용기번호 리스트) 기준

**필드(계약):**
- cylinder_no
- gas_name, capacity, valve_spec, cylinder_spec, usage_place
- status, location
- pressure_due_date (내압만료일 등 있으면 포함)
- last_event_at (마지막 상태변경 시각)
- source_updated_at

---

## 3. CYNOW 앱 테이블 — 쓰기/분석용

### 3.1 사용자/권한 (Django 기본 auth 사용)
- auth_user, auth_group, auth_permission (Django 기본)
- 권한 규칙(계약):
  - VIEW/리포트/분석: 익명 접근 가능
  - 입력(FORECAST/SCHEDULED/수동스냅샷): 로그인 필요 + 권한 `cynow.can_edit_plan` 필요(그룹으로 관리)

---

### 3.2 계획 입력: FORECAST (출하 계획)
#### 테이블: `plan_forecast_monthly`
- id (PK)
- month (YYYY-MM-01 date)
- cylinder_type_key
- gas_name, capacity, valve_spec, cylinder_spec, usage_place (검색 편의용 denormalized)
- planned_ship_qty (int, 월 출하 필요 병수)
- note (text, optional)
- created_by (FK auth_user)
- created_at, updated_at

**제약(계약):**
- UNIQUE (month, cylinder_type_key)
- planned_ship_qty >= 0

---

### 3.3 계획 입력: SCHEDULED (투입 계획)
#### 테이블: `plan_scheduled_monthly`
- id (PK)
- month (YYYY-MM-01 date)
- cylinder_type_key
- gas_name, capacity, valve_spec, cylinder_spec, usage_place
- add_purchase_qty
- add_refurb_qty
- recover_from_defect_qty
- convert_gas_qty
- note
- created_by
- created_at, updated_at

**제약(계약):**
- UNIQUE (month, cylinder_type_key)
- 각 qty >= 0

---

### 3.4 변화 이력(스냅샷) — 핵심
#### 테이블: `hist_inventory_snapshot`
**Row 의미:** “특정 시각의 VIEW 집계 결과(용기종류×상태×위치)의 수량”

- id (PK)
- snapshot_datetime (timestamp, KST 기준)
- snapshot_type (enum: DAILY, MANUAL)
- cylinder_type_key
- gas_name, capacity, valve_spec, cylinder_spec, usage_place
- status
- location
- qty
- source_view_updated_at (VIEW의 updated_at 저장)
- created_by (nullable; DAILY는 null, MANUAL은 user)
- created_at

**인덱스/유니크(계약):**
- UNIQUE (snapshot_datetime, snapshot_type, cylinder_type_key, status, location)
- INDEX (snapshot_datetime)
- INDEX (cylinder_type_key, status)
- INDEX (gas_name, capacity)

---

### 3.5 수동 스냅샷 기록(감사 로그) — 권장
#### 테이블: `hist_snapshot_request`
- id
- requested_at
- requested_by
- reason (text)
- status (SUCCESS/FAILED)
- message (text)

---

### 3.6 보고서 출력 이력(선택)
#### 테이블: `report_export_log`
- id
- report_type (WEEKLY/MONTHLY/HISTORY_EXPORT)
- params_json (필터/기간)
- exported_by (nullable)
- exported_at
- file_path (optional)

---

## 4. 스냅샷 적재 규칙(고정)

### 4.1 정기 스냅샷(필수)
- 매일 **00:05 (KST)** 실행
- `vw_cynow_inventory` 를 조회하여 전량 `hist_inventory_snapshot`에 insert
- snapshot_type = DAILY
- created_by = null

### 4.2 수동 스냅샷(필수)
- 로그인 사용자만 가능
- UI 버튼: **[현재 상태 저장]**
- snapshot_type = MANUAL
- created_by = user

### 4.3 증감(Δ) 계산
- DB에 Δ를 저장하지 않는다.
- 조회 시점에 전일/전주/전월/기간첫날/직전스냅샷 대비로 계산한다.

---

# 2) 메뉴 트리 + URL 구조(계약)

## 2.1 공개(비로그인) 메뉴
- `/` → Dashboard
- `/detail/` → 현황(용기종류 선택)
- `/summary/` → 요약(그래프/표/통계)
- `/cylinders/` → 용기번호 리스트
- `/alerts/` → 위험도 알림 리스트
- `/reports/weekly/` → 주간 보고서
- `/reports/monthly/` → 월간 보고서
- `/history/` → 변화 이력/분석 (조회/통계/다운로드)

## 2.2 로그인 필요(쓰기) 메뉴
- `/accounts/login/`
- `/plans/forecast/`
- `/plans/scheduled/`
- `/history/snapshot/manual/`

---

## 2.3 각 메뉴의 “필수 화면 요소”(최소 계약)

### Dashboard (`/`)
- 모든 용기종류 목록/그리드(한눈에)
- 핵심 숫자: 가용수량, 위험표시(0 임박/이상 급증/폐기 급증 등)
- “0 예상 시점”은 계산식 확정 전까지 v1에서는 위험도(임계치) 중심으로 구현 가능

### Detail (`/detail/?type=...`)
- 용기종류 선택(검색/필터)
- 상태별 수량, 위치별 수량, 최근 추이(History가 있을 경우)

### Summary (`/summary/`)
- 기간(최근 7일/30일/사용자 지정)
- 상태 분포/추이/Top 변동 랭킹

### Cylinders (`/cylinders/`)
- 용기번호 리스트 + 필터(상태/종류/위치/기간)
- 상세보기(`/cylinders/<cylinder_no>/`)

### Alerts (`/alerts/`)
- 위험도 기준 리스트(High/Medium/Low)
- 각 항목에 룰 기반 조언 텍스트

### Reports
- weekly/monthly 조회 + 출력(PDF/Excel)
- 데이터 근거: 현재 VIEW + History 비교 요약(가능 범위)

### History & Analytics (`/history/`)
- 기간 선택(일/주/월/사용자지정)
- 필터(가스명/용량/밸브/스펙/사용처/상태/위치/스냅샷유형)
- 표/그래프 + 다운로드(`/history/export.xlsx?...`)

---

# 3) AI 코딩 프롬프트 (Cursor/Claude/ChatGPT용)

## 3.1 프로젝트 생성 + 기본 구조
```text
너는 시니어 Django 엔지니어다. 아래 설계서(계약서)를 100% 준수해서 프로젝트를 생성하라.

- 프로젝트명: cynow (또는 config)
- 앱: core, dashboard, plans, history, reports, cylinders, alerts
- DB: PostgreSQL
- 'SSOT=VIEW' 원칙 반드시 준수: VIEW 데이터 수정/보정 금지
- 조회는 익명 허용, 입력(FORECAST/SCHEDULED/수동스냅샷)은 로그인+권한 필요
- 코드는 절대 축약하지 말고 파일 단위로 완성본 제공

필수 구현:
1) vw_cynow_inventory, vw_cynow_cylinder_list 를 기준으로 조회 화면 구현
2) plan_forecast_monthly, plan_scheduled_monthly 모델 구현
3) hist_inventory_snapshot, hist_snapshot_request 구현
4) 매일 00:05 DAILY 스냅샷 적재 (cron+management command 권장)
5) URL 구조는 설계서대로 고정

지금 단계에서는:
- Django 프로젝트 생성
- settings (.env 기반)
- URLConf
- Bootstrap 기반 기본 레이아웃
- 각 메뉴 placeholder 페이지 + 데이터 연결(가능 범위)
까지 진행하라.
```

## 3.2 DB/모델/마이그레이션
```text
설계서의 DB 계약을 구현하라.

필수:
- Django models: PlanForecastMonthly, PlanScheduledMonthly, HistInventorySnapshot, HistSnapshotRequest, ReportExportLog(선택)
- UNIQUE/INDEX 제약을 models에 반영
- admin 등록(검색/필터 편의)
- VIEW는 ORM 모델로 만들지 말고(읽기 전용), Raw SQL 또는 Repository로 접근
- vw_cynow_inventory 조회 함수, vw_cynow_cylinder_list 조회 함수 제공

산출물:
- models.py 전체
- admin.py 전체
- migrations 생성 안내
- 예시 SQL: vw_cynow_inventory / vw_cynow_cylinder_list 생성 템플릿(소스 테이블명은 TODO로)
```

## 3.3 History 스냅샷 적재(정기/수동) + 조회/엑셀
```text
History(스냅샷) 기능을 완성하라.

요구:
- 매일 00:05(KST) `vw_cynow_inventory` 를 읽어 `hist_inventory_snapshot`에 insert
- 중복 방지: UNIQUE 위반 시 안전 처리(UPSERT 또는 스킵)
- 수동 스냅샷: 로그인 사용자만 버튼으로 실행
- 실행 기록: HistSnapshotRequest에 SUCCESS/FAILED 기록
- History 조회: 기간/필터/유형에 따라 스냅샷 조회,
  증감(Δ)을 전일/전주/전월/기간첫날/직전스냅샷 대비로 계산
- export: 엑셀 다운로드(openpyxl)

산출물:
- management command: `take_daily_snapshot`, `take_manual_snapshot`
- /history 페이지(필터/표/다운로드)
- /history/snapshot/manual POST 엔드포인트(권한 필요)
```

---

# 부록 A) 운영 권장(고정 선택)
- 정기 실행: **cron + management command** 권장
  - 예: `05 0 * * * /path/venv/bin/python /app/manage.py take_daily_snapshot`

---

# 부록 B) 착수 시 확정해야 하는 5가지(TODO)
1) 동기화 테이블의 정확한 테이블명/컬럼명(현재는 예시)
2) FCMS 상태코드 → 표준 상태 7종 매핑 규칙
3) location(현재 위치) 코드 체계/표시명
4) “가용수량” 정의(보관만? 보관+충전? 회사 정책)
5) “0 예상 시점” 계산식(FORECAST/SCHEDULED 결합 방식)

---

# 끝.
