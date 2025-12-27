# CYNOW 데이터 아키텍처 종합 가이드

## 개요

CYNOW 시스템의 전체 데이터 구조, CDC 테이블, CYNOW 테이블, 그리고 테이블 간 관계를 정리한 종합 문서입니다.
새로운 기능 개발 시 이 문서를 참조하여 데이터 소스와 연결 관계를 파악할 수 있습니다.

**최종 갱신**: 2024-12-27

---

## 목차

1. [시스템 아키텍처](#1-시스템-아키텍처)
2. [CDC 테이블 (FCMS 원천)](#2-cdc-테이블-fcms-원천)
3. [CYNOW 테이블](#3-cynow-테이블)
4. [주요 테이블 상세](#4-주요-테이블-상세)
5. [데이터 흐름](#5-데이터-흐름)
6. [ER 다이어그램](#6-er-다이어그램)
7. [주요 쿼리 패턴](#7-주요-쿼리-패턴)
8. [코드 매핑](#8-코드-매핑)

---

## 1. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FCMS (Oracle DB)                              │
│                    [원천 시스템 - 일본]                               │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ CDC (Debezium)
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PostgreSQL (cynow_db)                             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │            fcms_cdc 스키마 (CDC 동기화 테이블)                 │   │
│  │  - ma_cylinders, ma_items, ma_valve_specs...                  │   │
│  │  - tr_latest_cylinder_statuses, tr_cylinder_status_histories  │   │
│  │  - tr_orders, tr_move_reports, tr_move_report_details         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │             public 스키마 (CYNOW 자체 테이블)                  │   │
│  │  - cy_cylinder_current (용기 현재 상태 스냅샷)                 │   │
│  │  - Django ORM 테이블들 (PO, ProductCode, Quote 등)            │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      CYNOW Django Application                        │
│                     [대시보드, 수주관리, 보고서 등]                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. CDC 테이블 (FCMS 원천)

**스키마**: `fcms_cdc`

### 2.1 마스터 테이블 (MA_*)

| 테이블명 | 용도 | PK | 주요 용도 |
|---------|------|-----|----------|
| `ma_cylinders` | 용기 마스터 | CYLINDER_NO | 용기 기본정보, 스펙, 내압정보 |
| `ma_items` | 가스/아이템 마스터 | ITEM_CODE | 가스명, 등급, 특성 |
| `ma_valve_specs` | 밸브 스펙 마스터 | VALVE_SPEC_CODE | 밸브 타입(CGA/DISS/DIN) |
| `ma_cylinder_specs` | 용기 스펙 마스터 | CYLINDER_SPEC_CODE | 용기 재질, 형식 |
| `ma_parameters` | 코드 매핑 | TYPE, KEY1, KEY2, KEY3 | 상태코드, 위치코드 의미 |

### 2.2 트랜잭션 테이블 (TR_*)

| 테이블명 | 용도 | PK/UK | 주요 용도 |
|---------|------|-------|----------|
| `tr_latest_cylinder_statuses` | 최신 용기 상태 | CYLINDER_NO | 현재 상태, 위치, 이동정보 |
| `tr_cylinder_status_histories` | 용기 상태 이력 | CYLINDER_NO, HISTORY_SEQ | 전체 이동 이력, LOT정보 |
| `tr_orders` | 주문(이동서) 정보 | ARRIVAL_SHIPPING_NO | 고객, 제품코드, 수량 |
| `tr_order_informations` | 주문 상세 정보 | MOVE_REPORT_NO | 예정일(충전/창입/출하) |
| `tr_move_reports` | 이동 보고서 | MOVE_REPORT_NO | 확정일, LOT번호 |
| `tr_move_report_details` | 이동서 상세 | MOVE_REPORT_NO, CYLINDER_NO | 용기-이동서 연결, 무게 |

---

## 3. CYNOW 테이블

**스키마**: `public`

### 3.1 핵심 운영 테이블

| 테이블명 | Django 모델 | 용도 |
|---------|------------|------|
| `cy_cylinder_current` | (Raw SQL) | 용기 현재 상태 스냅샷 (대시보드 핵심) |

### 3.2 앱별 Django 모델

#### Core (core)
| 모델 | 테이블명 | 용도 |
|------|---------|------|
| Translation | translation | FCMS 일본어 → 한국어 번역 |
| EndUserMaster | enduser_master | EndUser 마스터 (SDC, LGD 등) |
| EndUserDefault | enduser_default | 가스별 기본 EndUser 정책 |
| EndUserException | enduser_exception | 용기번호별 EndUser 예외 |
| ValveGroup | valve_group | 밸브 그룹 정의 |
| ValveGroupMapping | valve_group_mapping | 밸브 스펙 → 그룹 매핑 |
| HiddenCylinderType | hidden_cylinder_type | 대시보드 숨김 용기종류 |

#### Orders (orders) - 수주관리
| 모델 | 테이블명 | 용도 |
|------|---------|------|
| PO | po | 수주(Purchase Order) |
| POItem | po_item | 수주 품목 |
| PlannedMoveReport | planned_move_report | 가발행 이동서 |
| FCMSMatchStatus | fcms_match_status | FCMS 매칭 상태 |
| FCMSProductionProgress | fcms_production_progress | 생산 진척 동기화 |

#### Products (products) - 제품관리
| 모델 | 테이블명 | 용도 |
|------|---------|------|
| ProductCode | product_code | 제품코드(KFxxx) 마스터 |
| ProductPriceHistory | product_price_history | 단가 변경 이력 |
| ProductCodeSync | product_code_sync | FCMS 동기화 이력 |

#### Inventory (inventory) - 재고관리
| 모델 | 테이블명 | 용도 |
|------|---------|------|
| InventorySettings | inventory_settings | 재고 설정 (마감시간 등) |
| InventoryTransaction | inventory_transaction | 재고 트랜잭션 로그 |
| CylinderInventory | cylinder_inventory | 용기 재고 (타입×상태×위치) |
| ProductInventory | product_inventory | 제품 재고 (제품코드×창고) |
| CylinderInventorySnapshot | cylinder_inventory_snapshot | 용기 재고 스냅샷 |
| ProductInventorySnapshot | product_inventory_snapshot | 제품 재고 스냅샷 |
| SnapshotLog | snapshot_log | 스냅샷 생성 로그 |
| CylinderMaintenanceLog | cylinder_maintenance_log | 정비 입출고 로그 |

#### History (history) - 이력/추이
| 모델 | 테이블명 | 용도 |
|------|---------|------|
| HistInventorySnapshot | hist_inventory_snapshot | 재고 추이 스냅샷 |
| HistSnapshotRequest | hist_snapshot_request | 스냅샷 요청 |

#### Plans (plans) - 계획관리
| 모델 | 테이블명 | 용도 |
|------|---------|------|
| PlanForecastMonthly | plan_forecast_monthly | 월별 출하 계획 |
| PlanScheduledMonthly | plan_scheduled_monthly | 월별 투입 계획 |
| PlanFillingMonthly | plan_filling_monthly | 월별 충전 계획 |

#### Voucher (voucher) - 견적/문서
| 모델 | 테이블명 | 용도 |
|------|---------|------|
| CompanyInfo | company_info | 자사 정보 |
| Customer | customer | 고객사 정보 |
| Quote | quote | 견적서 |
| QuoteItem | quote_item | 견적 품목 |
| DocumentTemplate | document_template | 문서 템플릿 |

---

## 4. 주요 테이블 상세

### 4.1 ma_cylinders (용기 마스터)

```sql
-- 주요 컬럼
CYLINDER_NO          -- PK, 용기번호 (12자리)
ITEM_CODE            -- FK → ma_items, 가스 종류
CAPACITY             -- 용량 (L)
CYLINDER_SPEC_CODE   -- FK → ma_cylinder_specs
VALVE_SPEC_CODE      -- FK → ma_valve_specs
WEIGHT               -- 용기 무게 (kg)
WITHSTAND_PRESSURE_MAINTE_DATE  -- 내압 시험일
WITHSTAND_PRESSURE_TEST_TERM    -- 내압 주기 (년)
MANUFACTURE_DATE     -- 제조일
```

### 4.2 tr_cylinder_status_histories (용기 상태 이력)

```sql
-- 주요 컬럼
CYLINDER_NO          -- 용기번호
HISTORY_SEQ          -- 이력 순번
MOVE_CODE            -- 이동 코드 (10=입하, 20=충전, 50=창입, 60=출하 등)
MOVE_DATE            -- 이동일시
MOVE_REPORT_NO       -- 이동서번호
CONDITION_CODE       -- 상태 코드

-- LOT 정보
MANUFACTURE_LOT_HEADER, MANUFACTURE_LOT_NO, MANUFACTURE_LOT_BRANCH  -- 제조LOT
FILLING_LOT_HEADER, FILLING_LOT_NO, FILLING_LOT_BRANCH              -- 충전LOT
FILLING_WEIGHT       -- 충전 무게

-- 관련자 정보
SUPPLIER_USER_NAME   -- 공급처
CUSTOMER_USER_NAME   -- 고객사
POSITION_USER_NAME   -- 위치
```

### 4.3 tr_orders (주문/이동서 정보)

```sql
-- 주요 컬럼
ARRIVAL_SHIPPING_NO      -- PK, 이동서번호
CUSTOMER_ORDER_NO        -- 고객 주문번호 (PO번호)
SUPPLIER_USER_CODE/NAME  -- 고객사
TRADE_CONDITION_CODE     -- 제품코드 (KFxxx)
ITEM_NAME               -- 품목명
INSTRUCTION_COUNT       -- 지시 수량
DELIVERY_DATE           -- 납기일
ORDER_DATE              -- 주문일
```

### 4.4 tr_order_informations (주문 상세/일정)

```sql
-- 주요 컬럼
MOVE_REPORT_NO           -- PK, 이동서번호
FILLING_PLAN_DATE        -- 충전 예정일
WAREHOUSING_PLAN_DATE    -- 창입 예정일
SHIPPING_PLAN_DATE       -- 출하 예정일
SALES_REMARKS            -- 영업 비고
PRODUCTION_REMARKS       -- 생산 비고
```

### 4.5 tr_move_reports (이동 보고서)

```sql
-- 주요 컬럼
MOVE_REPORT_NO           -- PK, 이동서번호
PROGRESS_CODE            -- 진행 코드 (51=취소)
FILLING_DATE             -- 충전 확정일
SHIPPING_DATE            -- 출하 확정일
FILLING_LOT_HEADER/NO/BRANCH  -- 충전LOT
```

### 4.6 tr_move_report_details (이동서 상세)

```sql
-- 주요 컬럼
MOVE_REPORT_NO      -- 이동서번호
CYLINDER_NO         -- 용기번호
ROW_NO              -- 헤더번호 (순서)
CYLINDER_WEIGHT     -- 용기 무게
FILLING_WEIGHT      -- 충전 무게
ADD_DATETIME        -- 등록일시
```

### 4.7 cy_cylinder_current (CYNOW 용기 스냅샷)

```sql
-- 식별자
cylinder_no              -- PK, 용기번호

-- Raw 값 (FCMS 원본)
raw_gas_name, raw_capacity, raw_valve_spec_code, raw_valve_spec_name
raw_cylinder_spec_code, raw_cylinder_spec_name, raw_condition_code

-- Dashboard 값 (정책 적용)
dashboard_gas_name, dashboard_capacity
dashboard_valve_spec_name, dashboard_valve_group_name
dashboard_cylinder_spec_name, dashboard_enduser, dashboard_status

-- 집계용
cylinder_type_key        -- 용기종류 키 (MD5 해시)
is_available             -- 가용 여부

-- 메타데이터
pressure_expire_date     -- 내압 만료일
last_event_at            -- 마지막 이벤트
snapshot_updated_at      -- 스냅샷 갱신 시각
```

---

## 5. 데이터 흐름

### 5.1 용기 조회 흐름

```
[대시보드 카드 클릭]
       │
       ▼
cy_cylinder_current (현재 상태)
       │
       ├──[상태가 "보관"]──→ 용기 리스트 페이지로 이동
       │
       └──[상태가 "충전~제품"]──→ 이동서별 용기 모달
                                     │
                                     ├── tr_move_report_details (용기-이동서 연결)
                                     ├── tr_orders (주문 정보)
                                     ├── tr_order_informations (예정일)
                                     └── tr_move_reports (확정일, LOT)
```

### 5.2 수주 → 출하 흐름

```
[PO 등록] ──→ [POItem] ──→ [PlannedMoveReport]
                                   │
                                   ▼ FCMS 입력 후 CDC 동기화
                           [tr_orders] ←───────────────┐
                                   │                    │
                           [tr_move_reports]            │
                                   │                    │
                           [tr_move_report_details]     │
                                   │                    │
                           [tr_cylinder_status_histories]
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
        MOVE_CODE=20         MOVE_CODE=50         MOVE_CODE=60
          (충전)               (창입)               (출하)
```

### 5.3 재고 스냅샷 흐름

```
[매일 00:00 cron]
       │
       ▼
create_inventory_snapshot 명령어
       │
       ├── sync_cylinder_inventory_from_current()
       │      └── cy_cylinder_current → CylinderInventory
       │
       ├── sync_product_inventory_from_documents()
       │      └── tr_cylinder_status_histories (MOVE_CODE=50) 
       │          + tr_orders → ProductInventory
       │
       └── create_daily_snapshot()
              ├── CylinderInventory → CylinderInventorySnapshot
              └── ProductInventory → ProductInventorySnapshot
```

---

## 6. ER 다이어그램

### 6.1 CDC 테이블 관계

```
┌─────────────────────┐     ┌─────────────────────┐
│    ma_cylinders     │     │      ma_items       │
│─────────────────────│     │─────────────────────│
│ CYLINDER_NO (PK)    │────▶│ ITEM_CODE (PK)      │
│ ITEM_CODE (FK)      │     │ DISPLAY_NAME        │
│ CYLINDER_SPEC_CODE  │     │ FORMAL_NAME         │
│ VALVE_SPEC_CODE     │     └─────────────────────┘
│ CAPACITY, WEIGHT    │
└──────────┬──────────┘
           │
           │     ┌─────────────────────┐
           │     │  ma_cylinder_specs  │
           ├────▶│─────────────────────│
           │     │ CYLINDER_SPEC_CODE  │
           │     │ NAME                │
           │     └─────────────────────┘
           │
           │     ┌─────────────────────┐
           │     │   ma_valve_specs    │
           └────▶│─────────────────────│
                 │ VALVE_SPEC_CODE     │
                 │ NAME                │
                 └─────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              tr_cylinder_status_histories                    │
│─────────────────────────────────────────────────────────────│
│ CYLINDER_NO, HISTORY_SEQ (PK)                               │
│ MOVE_CODE, MOVE_DATE, MOVE_REPORT_NO                        │
│ MANUFACTURE_LOT_*, FILLING_LOT_*, FILLING_WEIGHT            │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ MOVE_REPORT_NO
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        tr_orders                             │
│─────────────────────────────────────────────────────────────│
│ ARRIVAL_SHIPPING_NO (PK) = MOVE_REPORT_NO                   │
│ CUSTOMER_ORDER_NO, SUPPLIER_USER_NAME                       │
│ TRADE_CONDITION_CODE (제품코드 KFxxx)                        │
│ INSTRUCTION_COUNT, DELIVERY_DATE                            │
└─────────────────────────────────────────────────────────────┘
          │                                    │
          │ MOVE_REPORT_NO                     │ MOVE_REPORT_NO
          ▼                                    ▼
┌─────────────────────────┐    ┌─────────────────────────────┐
│ tr_order_informations   │    │     tr_move_reports         │
│─────────────────────────│    │─────────────────────────────│
│ MOVE_REPORT_NO (PK)     │    │ MOVE_REPORT_NO (PK)         │
│ FILLING_PLAN_DATE       │    │ FILLING_DATE (확정)         │
│ WAREHOUSING_PLAN_DATE   │    │ SHIPPING_DATE (확정)        │
│ SHIPPING_PLAN_DATE      │    │ FILLING_LOT_*               │
└─────────────────────────┘    └─────────────────────────────┘
                                              │
                                              │ MOVE_REPORT_NO
                                              ▼
                               ┌─────────────────────────────┐
                               │   tr_move_report_details    │
                               │─────────────────────────────│
                               │ MOVE_REPORT_NO, CYLINDER_NO │
                               │ ROW_NO (헤더번호)            │
                               │ CYLINDER_WEIGHT             │
                               │ FILLING_WEIGHT              │
                               └─────────────────────────────┘
```

### 6.2 CYNOW-FCMS 연결 관계

```
┌─────────────────────────────────────────────────────────────┐
│                    CYNOW 테이블                              │
└─────────────────────────────────────────────────────────────┘
           │
    ┌──────┴──────────────────────────────────────────┐
    │                                                  │
    ▼                                                  ▼
┌──────────────────┐                    ┌──────────────────────┐
│ cy_cylinder_     │                    │     ProductCode      │
│ current          │                    │──────────────────────│
│──────────────────│                    │ trade_condition_code │
│ cylinder_no ─────┼───▶ ma_cylinders   │ (= KFxxx)            │
│ cylinder_type_   │                    │                      │
│ key              │                    └──────────┬───────────┘
└──────────────────┘                               │
                                                   │ 연결
                                                   ▼
                                    ┌──────────────────────────┐
                                    │ tr_orders.               │
                                    │ TRADE_CONDITION_CODE     │
                                    └──────────────────────────┘

┌──────────────────┐
│       PO         │
│──────────────────│
│ customer_order_  │───▶ tr_orders.CUSTOMER_ORDER_NO
│ no               │
└──────────────────┘
```

---

## 7. 주요 쿼리 패턴

### 7.1 용기 현재 상태 조회

```sql
SELECT * FROM cy_cylinder_current
WHERE cylinder_type_key = 'xxx'
  AND dashboard_status = '충전중';
```

### 7.2 용기의 이동서 연결 조회

```sql
-- tr_move_report_details 우선, 없으면 tr_cylinder_status_histories
WITH detail_links AS (
    SELECT DISTINCT ON (TRIM(d."CYLINDER_NO"))
        TRIM(d."CYLINDER_NO") as cylinder_no,
        TRIM(d."MOVE_REPORT_NO") as move_report_no,
        d."ROW_NO" as row_no
    FROM fcms_cdc.tr_move_report_details d
    ORDER BY TRIM(d."CYLINDER_NO"), d."ADD_DATETIME" DESC
)
SELECT * FROM detail_links;
```

### 7.3 이동서 + 주문 + 일정 조회

```sql
SELECT 
    o."ARRIVAL_SHIPPING_NO" as move_report_no,
    o."CUSTOMER_ORDER_NO",
    o."SUPPLIER_USER_NAME" as customer_name,
    o."TRADE_CONDITION_CODE" as product_code,
    oi."FILLING_PLAN_DATE",
    oi."WAREHOUSING_PLAN_DATE",
    oi."SHIPPING_PLAN_DATE",
    m."FILLING_DATE",
    m."SHIPPING_DATE",
    CONCAT(m."FILLING_LOT_HEADER", m."FILLING_LOT_NO", 
           CASE WHEN m."FILLING_LOT_BRANCH" != '' THEN '-' || m."FILLING_LOT_BRANCH" END) as filling_lot
FROM fcms_cdc.tr_orders o
LEFT JOIN fcms_cdc.tr_order_informations oi ON o."ARRIVAL_SHIPPING_NO" = oi."MOVE_REPORT_NO"
LEFT JOIN fcms_cdc.tr_move_reports m ON o."ARRIVAL_SHIPPING_NO" = m."MOVE_REPORT_NO";
```

### 7.4 LOT 정보 구성

```sql
-- 제조LOT
CONCAT(
    COALESCE(h."MANUFACTURE_LOT_HEADER", ''),
    COALESCE(h."MANUFACTURE_LOT_NO", ''),
    CASE WHEN h."MANUFACTURE_LOT_BRANCH" IS NOT NULL AND h."MANUFACTURE_LOT_BRANCH" != '' 
         THEN '-' || h."MANUFACTURE_LOT_BRANCH" ELSE '' END
) as manufacture_lot

-- 충전LOT
CONCAT(
    COALESCE(h."FILLING_LOT_HEADER", ''),
    COALESCE(h."FILLING_LOT_NO", ''),
    CASE WHEN h."FILLING_LOT_BRANCH" IS NOT NULL AND h."FILLING_LOT_BRANCH" != '' 
         THEN '-' || h."FILLING_LOT_BRANCH" ELSE '' END
) as filling_lot
```

---

## 8. 코드 매핑

### 8.1 MOVE_CODE (이동 코드)

| 코드 | 한글명 | 설명 |
|------|-------|------|
| 00 | 신규구매 | 새 용기 구매 |
| 01 | 신규등록 | 시스템 등록 |
| 10 | 입하 | 고객으로부터 용기 입하 |
| 14 | 회수완료 | 회수 완료 |
| 16 | 회수없음 | 회수 불가 |
| 17 | 재보관 | 재보관 처리 |
| 19 | 이상처리 | 이상 상태 처리 |
| 20 | 충전(시작) | 충전 시작 |
| 21 | 충전선택 | 충전 선택 |
| 22 | 충전완료 | 충전 완료 |
| 30 | 창고출고 | 창고에서 출고 |
| 31 | 외부충전 | 외부 충전 |
| 41 | 분석중 | 분석 진행 |
| 42 | 분석완료 | 분석 완료 |
| 50 | 창고입고 | 창고에 입고 (제품 완성) |
| 51 | 수주연결 | 수주와 연결 |
| 52 | 연결해제 | 수주 연결 해제 |
| 60 | 출하 | 고객에게 출하 |
| 65 | 영업외출하 | 영업 외 출하 |
| 70 | 반품 | 반품 처리 |
| 85 | 전출 | 타 사업장 전출 |
| 86 | 전입 | 타 사업장 전입 |
| 99 | 폐기 | 용기 폐기 |

### 8.2 CONDITION_CODE (상태 코드) → dashboard_status

| 코드 | dashboard_status | 설명 |
|------|-----------------|------|
| 100, 102 | 보관:미회수, 보관:회수 | 창고 보관 상태 |
| 210, 220 | 충전중, 충전완료 | 충전 공정 |
| 300, 310, 320 | 분석중, 분석완료 | 분석/검사 공정 |
| 420 | 분석 | 분석 상태 |
| 500 | 제품 | 창고입고 완료 (출하 가능) |
| 600 | 출하 | 고객에게 출하 완료 |
| 190 | 이상 | 이상 상태 |
| 950, 952 | 정비대상 | 내압만료 등 정비 필요 |
| 990 | 폐기 | 폐기 완료 |

### 8.3 주요 상태 구분

| 구분 | 상태 | is_available |
|------|------|--------------|
| **가용** | 보관:미회수, 보관:회수 | TRUE |
| **공정중** | 충전중, 충전완료, 분석중, 분석완료, 제품 | FALSE |
| **출하** | 출하 | FALSE |
| **비가용** | 이상, 정비대상, 폐기, 기타 | FALSE |

---

## 부록: 자주 사용되는 조인 패턴

### A. 용기 기본정보 + 가스/스펙

```sql
SELECT 
    c."CYLINDER_NO",
    COALESCE(i."DISPLAY_NAME", i."FORMAL_NAME") as gas_name,
    c."CAPACITY",
    vs."NAME" as valve_spec,
    cs."NAME" as cylinder_spec
FROM fcms_cdc.ma_cylinders c
LEFT JOIN fcms_cdc.ma_items i ON c."ITEM_CODE" = i."ITEM_CODE"
LEFT JOIN fcms_cdc.ma_valve_specs vs ON c."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
LEFT JOIN fcms_cdc.ma_cylinder_specs cs ON c."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE";
```

### B. 용기 현재상태 + 히스토리

```sql
SELECT 
    cc.*,
    tcs."MOVE_REPORT_NO",
    tcs."MOVE_DATE"
FROM cy_cylinder_current cc
LEFT JOIN fcms_cdc.tr_latest_cylinder_statuses tcs 
    ON cc.cylinder_no = TRIM(tcs."CYLINDER_NO");
```

### C. 이동서 전체 정보

```sql
SELECT 
    o.*,
    oi."FILLING_PLAN_DATE", oi."WAREHOUSING_PLAN_DATE", oi."SHIPPING_PLAN_DATE",
    m."FILLING_DATE", m."SHIPPING_DATE",
    m."FILLING_LOT_HEADER" || m."FILLING_LOT_NO" as filling_lot
FROM fcms_cdc.tr_orders o
LEFT JOIN fcms_cdc.tr_order_informations oi ON o."ARRIVAL_SHIPPING_NO" = oi."MOVE_REPORT_NO"
LEFT JOIN fcms_cdc.tr_move_reports m ON o."ARRIVAL_SHIPPING_NO" = m."MOVE_REPORT_NO"
WHERE m."PROGRESS_CODE" IS NULL OR m."PROGRESS_CODE" != '51';  -- 취소 제외
```

---

## 변경 이력

| 날짜 | 변경 내용 |
|------|----------|
| 2024-12-27 | 초기 작성 |
