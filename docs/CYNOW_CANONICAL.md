# CYNOW 정본(족보) — Single Source of Truth

> 참고: 정본 외 모든 문서는 `docs/_ref/` 로 이동해 두었습니다. (docs 폴더를 깔끔하게 유지)
>
> **정확도 기준(가장 중요)**
> - 문서 간 내용이 충돌하면 **Git 기준으로 가장 최근 커밋된 정보**가 더 정확합니다.
> - 그 다음 우선순위는 **실제 코드/SQL(실제 동작)** 입니다.
> - 즉 “정본 문서”라도 코드를 이기지 못합니다.
>
> 확인 방법:
>
> ```bash
> git log -1 -- docs/CYNOW_CANONICAL.md
> ```

---

## 0) 이 문서의 목적

- CYNOW 개발/운영에서 반복적으로 필요한 **데이터 흐름, CDC 테이블/컬럼 의미, 조인 규칙, 상태/코드 매핑, 운영 커맨드**를 한 곳에 모읍니다.
- 기능을 추가할 때마다 docs를 전수 검토하지 않고, **이 문서만 보고 “어디서 어떤 데이터를 가져오는지”** 판단할 수 있게 합니다.

---

## 1) 진실의 근원(Source of Truth) 우선순위

1. **실제 동작 SQL**: `sql/` 의 DDL/Trigger/Function (`sync_cylinder_current_single`)
2. **실제 조회 코드**: Repository/Service/View의 실제 쿼리 (`core/repositories/`, `dashboard/views.py`, `inventory/services.py`)
3. **운영 스크립트/배치**: `deploy/` 및 서버 cron 설정
4. **문서(docs)**: 참고용(항상 최신 커밋 여부 확인)

---

## 2) 시스템 전체 구조 (FCMS → CDC → CYNOW)

- **FCMS(Oracle)**: 원천 시스템
- **CDC(Debezium + Kafka)**: 변경 이벤트를 PostgreSQL로 복제
- **PostgreSQL**
  - `fcms_cdc` 스키마: CDC로 복제된 테이블(원천, 읽기 전용 취급)
  - `public` 스키마: CYNOW가 직접 관리하는 테이블/스냅샷/ORM

---

## 3) 핵심 CDC 테이블과 역할

### 3.1 용기 마스터/스펙

- **`fcms_cdc.ma_cylinders`**: 용기 기본정보(용기번호, 아이템, 용량, 스펙, 내압 관련)
- **`fcms_cdc.ma_items`**: 가스/아이템 표시명(`DISPLAY_NAME`), 정식명(`FORMAL_NAME`)
- **`fcms_cdc.ma_valve_specs`**, **`fcms_cdc.ma_cylinder_specs`**: 밸브/용기 스펙명

### 3.2 용기 상태

- **`fcms_cdc.tr_latest_cylinder_statuses`**: 현재 상태 1건(조건코드/위치/최근 이동일시/최근 이동서번호)
- **`fcms_cdc.tr_cylinder_status_histories`**: 전체 이력(제조LOT/충전LOT/이동서번호/이동코드 등)

### 3.3 문서(주문/이동서)

- **`fcms_cdc.tr_orders`**
  - 이동서 단위 문서
  - **제품코드(KFxxx)** = `TRADE_CONDITION_CODE`
  - 이동서번호 = `ARRIVAL_SHIPPING_NO`
- **`fcms_cdc.tr_order_informations`**: 예정일(충전/창입/출하 계획)
- **`fcms_cdc.tr_move_reports`**: 확정일(충전/출하) + 이동서 차원의 충전LOT
- **`fcms_cdc.tr_move_report_details`**: 이동서 상세(용기-이동서 연결, `ROW_NO`, `FILLING_WEIGHT` 등)

---

## 4) CYNOW 핵심 테이블(운영 SSOT)

### 4.1 `cy_cylinder_current` (대시보드/조회 SSOT)

- **정의(DDL)**: `sql/create_cy_cylinder_current.sql`
- Raw(원천): `raw_*`
- Dashboard(정책+번역): `dashboard_*`
- 집계 키: `cylinder_type_key` (MD5)

**실제 생성/갱신의 진실**: `sql/create_sync_triggers.sql` 의 함수 `sync_cylinder_current_single()`

- 상태 판단: `tr_latest_cylinder_statuses.CONDITION_CODE` → `dashboard_status`
- EndUser 정책: `cy_enduser_exception` → `cy_enduser_default` → (없으면 `NULL`)
- 밸브 그룹 정책: `cy_valve_group_mapping` / `cy_valve_group`
- 번역 적용: `core_translation` (gas_name/valve_spec/cylinder_spec/location)

> 주의: 과거 문서 일부는 `dashboard_enduser_code`, `dashboard_cylinder_type_key`, `cy_enduser_policy` 등 **구 설계 명칭**이 섞여 있을 수 있습니다. 최신 기준은 위 SQL/코드입니다.

### 4.2 CYNOW 정책 테이블

- **DDL**: `sql/create_cynow_policy_tables.sql`
- `cy_enduser_default`, `cy_enduser_exception`, `cy_valve_group`, `cy_valve_group_mapping`

---

## 5) 핵심 데이터 흐름(업무 기준)

### 5.1 대시보드 상태 클릭

- **보관(보관:미회수/보관:회수)**: 용기 리스트 페이지로 이동
- **충전~제품(공정/제품)**: 이동서별 모달
  - 용기→이동서 연결 우선순위:
    1) `tr_move_report_details` (우선)
    2) `tr_cylinder_status_histories` (fallback)

### 5.2 제품재고(제품코드 KFxxx) 계산 기준

**코드 기준(진실)**: `inventory/services.py` 의 `sync_product_inventory_from_documents()`

- 용기별 최신 이력 1건(DISTINCT ON)
- 최신 `MOVE_CODE='50'`(창고입고)인 용기만 재고로 카운트
- `MOVE_REPORT_NO` → `tr_orders.ARRIVAL_SHIPPING_NO` 조인
- 제품코드 = `tr_orders.TRADE_CONDITION_CODE` (KFxxx)

즉, 제품재고는 **cylinder_type_key 기반이 아니라 문서(주문/이동서) 흐름 기반**입니다.

### 5.3 일간 스냅샷(재고)

- 용기재고: `cy_cylinder_current` → `CylinderInventory` 동기화 → `CylinderInventorySnapshot`
- 제품재고: 문서 기반 동기화 → `ProductInventorySnapshot`
- 마감시간: 00:00 기준(운영 정책)

---

## 6) LOT / 무게 / 헤더번호(ROW_NO) 정의

### 6.1 제조LOT

- 이력 기반: `tr_cylinder_status_histories.MANUFACTURE_LOT_*`
- 조합: `MANUFACTURE_LOT_HEADER` + `MANUFACTURE_LOT_NO` + (branch 있으면 `-MANUFACTURE_LOT_BRANCH`)

### 6.2 충전LOT

- 이동서 헤더 기준: `tr_move_reports.FILLING_LOT_*`
- 이력에서도 `tr_cylinder_status_histories.FILLING_LOT_*` 로 조회 가능

### 6.3 용기무게 / 충전된 가스무게

- 용기무게: `ma_cylinders.WEIGHT`
- 충전된 가스무게: 우선 `tr_move_report_details.FILLING_WEIGHT`

### 6.4 헤더번호

- `tr_move_report_details.ROW_NO`
- 정렬 우선순위: `ROW_NO` → `cylinder_no`

---

## 7) 코드/상태 매핑

- **CONDITION_CODE → dashboard_status**: `sql/create_sync_triggers.sql` 의 CASE 로직이 기준
- **제품재고 기준 MOVE_CODE**: 창고입고 `50` 포함, 최신이 `60`이면 제외

---

## 8) 운영 Playbook (CDC / 복구)

- 백업 시간 pause/resume
  - Linux: `deploy/pause_debezium_for_backup.sh`
  - Windows: `deploy/pause_debezium_for_backup.ps1`
- 상세 운영 문서(참고):
  - `docs/_ref/CDC_BACKUP_TIME_RECOVERY_PLAN.md`
  - `docs/_ref/CDC_SMART_RECOVERY_GUIDE.md`
  - `docs/_ref/CDC_UBUNTU_SETUP_GUIDE.md`

---

## 9) 문서 유지보수 룰

- 새 기능 추가 시 먼저 **정본(`docs/CYNOW_CANONICAL.md`)**을 업데이트합니다.
- 정본과 충돌하는 문서가 생기면 즉시 `docs/_ref/`로 이동(또는 archive)하고, 정본에 기준을 반영합니다.

---

## 10) 변경 이력

- 2025-12-27: docs 전수 검토 + 코드/SQL 기준으로 정본 작성

 