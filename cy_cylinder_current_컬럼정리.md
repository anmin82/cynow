# cy_cylinder_current 테이블 컬럼 정리

## 테이블 개요
- **목적**: 용기 현재 상태 스냅샷 (대시보드 조회 전용)
- **Primary Key**: `cylinder_no` (VARCHAR(20))
- **특징**: FCMS 원본 데이터와 CYNOW 정책이 적용된 Dashboard 값을 분리하여 저장

---

## 1. 식별자

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `cylinder_no` | VARCHAR(20) | 용기번호 (Primary Key) |

---

## 2. FCMS Raw 값 (원천 데이터, 감사/이력용)

**목적**: FCMS에서 동기화된 원본 데이터 (변경 불가, 감사 추적용)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `raw_gas_name` | VARCHAR(100) | 원본 가스명 |
| `raw_capacity` | NUMERIC | 원본 용량 |
| `raw_valve_spec_code` | VARCHAR(50) | 원본 밸브 스펙 코드 |
| `raw_valve_spec_name` | VARCHAR(200) | 원본 밸브 스펙 이름 |
| `raw_cylinder_spec_code` | VARCHAR(50) | 원본 용기 스펙 코드 |
| `raw_cylinder_spec_name` | VARCHAR(200) | 원본 용기 스펙 이름 |
| `raw_usage_place` | VARCHAR(50) | 원본 사용처 코드 |
| `raw_location` | VARCHAR(100) | 원본 위치 |
| `raw_condition_code` | VARCHAR(10) | 원본 상태 코드 |
| `raw_position_user_name` | VARCHAR(100) | 원본 위치 사용자명 |

---

## 3. CYNOW Dashboard 값 (정책 적용된 값, 운영/집계용)

**목적**: CYNOW 정책(EndUser 정책, Valve 그룹화 등)이 적용된 대시보드 표시용 값

### 3.1 가스 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `dashboard_gas_name` | VARCHAR(100) | 정책 적용된 가스명 (번역 포함) |
| `dashboard_capacity` | NUMERIC | 정책 적용된 용량 |

### 3.2 밸브 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `dashboard_valve_spec_code` | VARCHAR(50) | 정책 적용된 밸브 스펙 코드 |
| `dashboard_valve_spec_name` | VARCHAR(200) | 정책 적용된 밸브 스펙 이름 |
| `dashboard_valve_group_name` | VARCHAR(100) | 밸브 그룹 이름 (밸브 표준화 정책 적용 시) |

### 3.3 용기 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `dashboard_cylinder_spec_code` | VARCHAR(50) | 정책 적용된 용기 스펙 코드 |
| `dashboard_cylinder_spec_name` | VARCHAR(200) | 정책 적용된 용기 스펙 이름 |

### 3.4 EndUser 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `dashboard_enduser` | VARCHAR(50) | EndUser 정책 적용된 최종 EndUser 코드 (SDC, LGD 등) |

### 3.5 상태 정보
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `dashboard_status` | VARCHAR(20) | 정책 적용된 상태 (보관, 충전, 분석, 창입, 출하, 이상, 정비, 폐기, 기타) |

### 3.6 위치 정보 (대시보드 미사용)
| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `dashboard_location` | VARCHAR(100) | 정책 적용된 위치 (번역 포함) - 대시보드에서는 사용하지 않음, 용기 리스트 등에서만 사용 |
| ~~`dashboard_usage_place`~~ | VARCHAR(50) | ~~정책 적용된 사용처 - 제거됨, `dashboard_enduser` 사용~~ |

---

## 4. 집계/예측용 필드

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `cylinder_type_key` | VARCHAR(32) | 정책 적용 후 생성된 용기종류 키 (MD5 해시) - EndUser 포함 |
| `cylinder_type_key_raw` | VARCHAR(32) | Raw 값 기준 용기종류 키 (MD5 해시) - 감사용 |

---

## 5. 상태/위치 정보 (원본)

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `condition_code` | VARCHAR(10) | 상태 코드 (FCMS 원본) |
| `move_date` | TIMESTAMP | 이동일시 |
| `pressure_due_date` | TIMESTAMP | 내압 |
| `last_event_at` | TIMESTAMP | 마지막 이벤트 시각 |

---

## 6. 메타데이터

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `source_updated_at` | TIMESTAMP | FCMS 원본 데이터 갱신 시각 |
| `snapshot_updated_at` | TIMESTAMP | 스냅샷 갱신 시각 (기본값: NOW()) |

---

## 7. 인덱스용 파생 필드

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| `status_category` | VARCHAR(20) | 상태 카테고리 ('가용', '비가용') |
| `is_available` | BOOLEAN | 가용 여부 (보관/충전 상태일 때 TRUE, 정비/폐기는 FALSE) |

---

## 주요 인덱스

1. **Primary Key**: `cylinder_no`
2. **단일 컬럼 인덱스**:
   - `idx_cy_cylinder_current_type_key` (cylinder_type_key)
   - `idx_cy_cylinder_current_status` (dashboard_status)
   - `idx_cy_cylinder_current_enduser` (dashboard_enduser)
   - `idx_cy_cylinder_current_location` (dashboard_location)
   - `idx_cy_cylinder_current_available` (is_available) WHERE is_available = TRUE
   - `idx_cy_cylinder_current_gas` (dashboard_gas_name)
   - `idx_cy_cylinder_current_updated` (snapshot_updated_at)

3. **복합 인덱스**:
   - `idx_cy_cylinder_current_dashboard_lookup` (dashboard_gas_name, dashboard_capacity, dashboard_valve_group_name, dashboard_cylinder_spec_name, dashboard_enduser, dashboard_status)

---

## 컬럼 사용 현황

### 대시보드 조회에서 주로 사용되는 컬럼
- `dashboard_gas_name`
- `dashboard_capacity`
- `COALESCE(dashboard_valve_group_name, dashboard_valve_spec_name)` (밸브 스펙)
- `dashboard_cylinder_spec_name` (용기 스펙)
- `dashboard_status` (상태: 보관, 충전, 분석, 창입, 출하, 이상, 정비, 폐기)
- `dashboard_enduser` (EndUser)
- `cylinder_type_key` (용기종류 키)
- `is_available` (가용 여부: 보관/충전만 TRUE)

### 필터링에 사용되는 컬럼
- `dashboard_gas_name`
- `dashboard_status`
- `dashboard_enduser`
- `cylinder_type_key`
- `last_event_at` (기간 필터)

### 기타 기능에서 사용되는 컬럼 (대시보드 미사용)
- `dashboard_location` (용기 리스트 페이지 등에서 사용)

---

## 주의사항

1. **Raw vs Dashboard 구분**: 
   - `raw_*` 컬럼은 FCMS 원본 데이터 (변경 불가)
   - `dashboard_*` 컬럼은 CYNOW 정책이 적용된 값 (대시보드 표시용)

2. **Valve 그룹화**: 
   - `dashboard_valve_group_name`이 있으면 그룹화된 밸브 이름 사용
   - 없으면 `dashboard_valve_spec_name` 사용

3. **EndUser 정책**: 
   - `dashboard_enduser`는 EndUser 정책(기본값/예외)이 적용된 최종 값
   - ~~`dashboard_usage_place`는 제거됨, `dashboard_enduser` 사용~~

4. **용기종류 키**: 
   - `cylinder_type_key`: 정책 적용 후 생성 (EndUser 포함)
   - `cylinder_type_key_raw`: Raw 값 기준 (감사용)

5. **상태 구분**:
   - **정비 (950, 952)**: 사용불가 상태이지만 정비 후 공용기로 사용 가능한 자원
   - **폐기 (990)**: 실제 폐기된 용기 (삭제하지 않고 폐기 상태로 기록)
   - 정비와 폐기는 모두 `is_available = FALSE` (가용 수량에 포함되지 않음)
   - 위험도 계산 시 폐기 수량만 HIGH 위험도에 영향을 줌 (정비는 영향 없음)
