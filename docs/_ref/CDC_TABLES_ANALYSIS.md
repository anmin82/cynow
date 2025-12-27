# CDC 테이블 구조 및 용도 분석

## 개요

FCMS Oracle DB에서 CDC를 통해 PostgreSQL `cycy_db.fcms_cdc` 스키마로 동기화된 테이블들의 구조와 용도를 분석한 문서입니다.

## 테이블 목록

### 마스터 테이블 (MA_*)
- `ma_cylinders` - 용기 마스터 (2,773개)
- `ma_cylinder_specs` - 용기 스펙 마스터 (6개)
- `ma_valve_specs` - 밸브 스펙 마스터 (20개)
- `ma_items` - 아이템(가스) 마스터 (12개)
- `ma_parameters` - 파라미터 마스터 (1,042개)

### 트랜잭션 테이블 (TR_*)
- `tr_latest_cylinder_statuses` - 최신 용기 상태 (2,773개)
- `tr_cylinder_status_histories` - 용기 상태 이력
- `tr_move_reports` - 이동 보고서
- `tr_move_report_details` - 이동 보고서 상세
- `tr_orders` - 주문 정보
- `tr_order_informations` - 주문 상세 정보

---

## 1. MA_CYLINDERS (용기 마스터) ⭐ 핵심

### 용도
개별 용기의 기본 정보를 저장하는 마스터 테이블. 각 용기의 고유 번호, 스펙, 제조 정보 등을 관리.

### 주요 컬럼

#### 식별자
- `CYLINDER_NO` (PK) - 용기 번호 (12자리)
- `CYLINDER_NO_SIGN` - 용기 번호 접두사
- `CYLINDER_NO_NUM` - 용기 번호 숫자 부분
- `BASE_CODE` - 기본 코드

#### 아이템/가스 정보
- `ITEM_CODE` - 아이템 코드 (가스 종류)
- `STAMP_ITEM_CODE` - 스탬프 아이템 코드
- `STAMP_GAS_CHANGES_COUNT` - 가스 변경 횟수

#### 용량/무게 정보
- `CAPACITY` - 용량 (필수)
- `STAMP_CAPACITY` - 스탬프 용량
- `WEIGHT` - 무게
- `VALVE_WEIGHT` - 밸브 무게
- `OUTLET_CAP_WEIGHT` - 아웃렛 캡 무게
- `SKID_WEIGHT` - 스키드 무게
- `ACCESSORIES_WEIGHT` - 액세서리 무게

#### 압력 정보
- `MAX_FILLING_PRESSURE` - 최대 충전 압력
- `WITHSTAND_TEST_PRESSURE` - 내압 시험 압력
- `WITHSTAND_PRESSURE_TEST_TERM` - 내압 시험 주기
- `WITHSTAND_PRESSURE_MAINTE_DATE` - 내압 유지일

#### 스펙 정보
- `CYLINDER_SPEC_CODE` - 용기 스펙 코드 (FK → ma_cylinder_specs)
- `VALVE_SPEC_CODE` - 밸브 스펙 코드 (FK → ma_valve_specs)
- `PAINTING_SPEC_CODE` - 도장 스펙 코드
- `MAKER_CODE` - 제조사 코드

#### 날짜 정보
- `PURCHASE_DATE` - 구매일
- `MANUFACTURE_DATE` - 제조일
- `VALVE_INSTALLATION_DATE` - 밸브 설치일
- `SALE_DISPOSAL_DATE` - 판매/폐기일

#### 기타
- `OWNER_CODE` - 소유자 코드
- `USE_DEPARTMENT_CODE` - 사용 부서 코드
- `REMARKS` - 비고
- `ADD_DATETIME`, `UPDATE_DATETIME` - 등록/수정 일시

### CYNOW에서의 활용
- 용기 리스트 조회
- 용기 상세 정보 표시
- 용기종류 그룹화 (ITEM_CODE, CYLINDER_SPEC_CODE, VALVE_SPEC_CODE 조합)

---

## 2. MA_CYLINDER_SPECS (용기 스펙 마스터)

### 용도
용기의 재질, 형식, 구조 등 스펙 정보를 정의하는 마스터 테이블.

### 주요 컬럼
- `CYLINDER_SPEC_CODE` (PK) - 용기 스펙 코드 (10자리)
- `NAME` - 스펙명 (예: "BN SUS WELDING SHOT-Y In-screw")
- `FORMAT_TYPE_CODE` - 형식 타입 코드 (예: "BN")
- `FORMAT_DETAIL_CODE` - 형식 상세 코드
- `MATERIAL_CODE` - 재질 코드 (예: "2")
- `CONSTRUCTION_CODE` - 구조 코드 (예: "1")
- `FINISH_CODE` - 마감 코드 (예: "1")
- `SCREW_TYPE_CODE` - 나사 타입 코드 (예: "1")
- `REMARKS` - 비고

### CYNOW에서의 활용
- 용기 스펙명 표시 (`NAME` 컬럼)
- 재질 정보 추출 (MATERIAL_CODE 매핑)

---

## 3. MA_VALVE_SPECS (밸브 스펙 마스터)

### 용도
밸브의 재질, 마감, 나사 타입 등 스펙 정보를 정의하는 마스터 테이블.

### 주요 컬럼
- `VALVE_SPEC_CODE` (PK) - 밸브 스펙 코드 (10자리)
- `NAME` - 스펙명 (예: "CGA330", "DISS724" 등)
- `MATERIAL_CODE` - 재질 코드
- `FINISH_CODE` - 마감 코드
- `SAFETY_VALVE_CODE` - 안전 밸브 코드
- `SCREW_TYPE_CODE` - 나사 타입 코드
- `HANDLE_CODE` - 핸들 코드
- `MAKER_CODE` - 제조사 코드
- `REMARKS` - 비고

### CYNOW에서의 활용
- 밸브 스펙명 표시 (`NAME` 컬럼에서 CGA/DISS/DIN 코드 추출)
- 밸브 타입별 필터링

---

## 4. MA_ITEMS (아이템/가스 마스터) ⭐ 핵심

### 용도
가스 종류(아이템)의 기본 정보를 정의하는 마스터 테이블.

### 주요 컬럼
- `ITEM_CODE` (PK) - 아이템 코드 (28자리)
- `DISPLAY_NAME` - 표시명 (예: "CF4")
- `FORMAL_NAME` - 정식명 (예: "Carbon tetrafluoride")
- `IS_REPRESENTATIVE_ITEM` - 대표 아이템 여부
- `REPRESENTATIVE_ITEM_CODE` - 대표 아이템 코드
- `GRADE_CODE` - 등급 코드
- `IS_CLEAN` - 클린 여부
- `NEED_FILLING_WEIGHT_CHECK` - 충전 무게 체크 필요 여부
- `NEED_SHIPPING_COUNT_CHECK` - 출하 횟수 체크 필요 여부
- `MAX_SHIPPING_COUNT` - 최대 출하 횟수
- `NEED_WITHSTAND_PRESSURE_TEST` - 내압 시험 필요 여부
- `CYLINDER_ITEM_CODE` - 용기 아이템 코드
- `IS_HIGH_PRESSURE` - 고압 여부
- `IS_POISON` - 독성 여부

### CYNOW에서의 활용
- 가스명 표시 (`DISPLAY_NAME` 또는 `FORMAL_NAME`)
- 가스별 필터링
- 용기종류 그룹화의 핵심 키

---

## 5. MA_PARAMETERS (파라미터 마스터)

### 용도
시스템 전반에서 사용되는 코드값 매핑 테이블. 상태 코드, 위치 코드 등의 의미를 정의.

### 주요 컬럼
- `TYPE` (PK) - 파라미터 타입 (4자리)
- `KEY1`, `KEY2`, `KEY3` - 키 값들
- `VALUE1`, `VALUE2`, `VALUE3`, `VALUE4` - 값들
- `SORT` - 정렬 순서
- `IS_COOPERATE` - 협력 여부

### CYNOW에서의 활용
- 상태 코드 매핑 (CONDITION_CODE → 상태명)
- 위치 코드 매핑
- 기타 코드값 해석

---

## 6. TR_LATEST_CYLINDER_STATUSES (최신 용기 상태) ⭐ 핵심

### 용도
각 용기의 현재 상태 정보를 저장하는 테이블. 용기별로 최신 상태 1건만 유지.

### 주요 컬럼

#### 식별자
- `CYLINDER_NO` (PK) - 용기 번호 (FK → ma_cylinders)

#### 상태 정보
- `CONDITION_CODE` - 상태 코드 (예: "100", "210", "600" 등)
- `MOVE_CODE` - 이동 코드
- `MOVE_DATE` - 이동일시

#### 위치 정보
- `LOCATION_CODE` - 위치 코드
- `POSITION_USER_CODE` - 위치 사용자 코드
- `POSITION_USER_NAME` - 위치 사용자명 (일본어)
- `LOCATION_USER_CODE` - 위치 사용자 코드
- `LOCATION_USER_NAME` - 위치 사용자명

#### 이동 정보
- `MOVE_DEPARTMENT_NAME` - 이동 부서명
- `MOVE_STAFF_NAME` - 이동 담당자명
- `CARRIER_USER_CODE` - 운반자 코드
- `CARRIER_USER_NAME` - 운반자명
- `CAR_NO` - 차량 번호
- `MOVE_REPORT_NO` - 이동 보고서 번호

#### 기타
- `HAS_REMAINING_GAS` - 잔류 가스 여부
- `HAS_NITROGEN` - 질소 여부
- `REMARKS` - 비고
- `UPDATE_TERMINAL_NAME` - 업데이트 터미널명

### 상태 코드 매핑 (예상)
- `100`, `102` → 보관
- `210`, `220` → 충전
- `420` → 분석
- `500` → 창입
- `600` → 출하
- `190` → 이상
- `950`, `952` → 폐기

### CYNOW에서의 활용
- 현재 상태 조회 (가장 중요!)
- 위치 정보 조회
- 상태별 집계
- VIEW 생성 시 핵심 테이블

---

## 7. TR_CYLINDER_STATUS_HISTORIES (용기 상태 이력)

### 용도
용기 상태 변경 이력을 저장하는 테이블. 과거 상태 변경 내역을 모두 보관.

### 주요 컬럼 (예상)
- `CYLINDER_NO` - 용기 번호
- `CONDITION_CODE` - 상태 코드
- `CHANGE_DATE` - 변경일시
- `MOVE_CODE` - 이동 코드
- 기타 상태 정보

### CYNOW에서의 활용
- 상태 변경 이력 조회
- 추이 분석
- 리포트 생성

---

## 테이블 간 관계

```
ma_cylinders (용기 마스터)
  ├─ ITEM_CODE → ma_items.ITEM_CODE (가스 종류)
  ├─ CYLINDER_SPEC_CODE → ma_cylinder_specs.CYLINDER_SPEC_CODE (용기 스펙)
  └─ VALVE_SPEC_CODE → ma_valve_specs.VALVE_SPEC_CODE (밸브 스펙)

tr_latest_cylinder_statuses (최신 상태)
  └─ CYLINDER_NO → ma_cylinders.CYLINDER_NO (용기)
```

---

## CYNOW VIEW 생성 시 필요한 조인

### vw_cynow_cylinder_list
```sql
SELECT 
    c.CYLINDER_NO,
    i.DISPLAY_NAME as gas_name,  -- 또는 FORMAL_NAME
    c.CAPACITY,
    vs.NAME as valve_spec,
    cs.NAME as cylinder_spec,
    -- usage_place는 ma_cylinders 또는 tr_latest에서?
    ls.CONDITION_CODE,
    ls.POSITION_USER_NAME as location
FROM ma_cylinders c
LEFT JOIN ma_items i ON c.ITEM_CODE = i.ITEM_CODE
LEFT JOIN ma_cylinder_specs cs ON c.CYLINDER_SPEC_CODE = cs.CYLINDER_SPEC_CODE
LEFT JOIN ma_valve_specs vs ON c.VALVE_SPEC_CODE = vs.VALVE_SPEC_CODE
LEFT JOIN tr_latest_cylinder_statuses ls ON c.CYLINDER_NO = ls.CYLINDER_NO
```

### vw_cynow_inventory
위 VIEW를 기반으로 GROUP BY하여 집계

---

## 주의사항

1. **일본어 데이터**: 많은 컬럼에 일본어 텍스트가 저장되어 있음 (번역 필요)
   - `POSITION_USER_NAME`
   - `MOVE_DEPARTMENT_NAME`
   - `MOVE_STAFF_NAME`
   - 등

2. **대소문자 구분**: PostgreSQL에서 테이블명/컬럼명은 소문자로 저장됨
   - 쿼리 시 `"fcms_cdc"."ma_cylinders"` 형태로 사용

3. **NULL 처리**: 많은 컬럼이 NULL 허용, 조인 시 주의

4. **데이터 타입**: 
   - `character(n)` - 고정 길이 문자열
   - `character varying(n)` - 가변 길이 문자열
   - `numeric` - 숫자
   - `timestamp without time zone` - 날짜/시간

---

## 다음 단계

1. ✅ 테이블 구조 확인 완료
2. ⏳ VIEW 생성 (`create_postgresql_views` 명령어 실행)
3. ⏳ 번역 데이터 로드 (`load_translations` 명령어 실행)
4. ⏳ 실제 데이터 확인 및 검증
