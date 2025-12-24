# 🔧 CDC 제품코드 테이블 추가 가이드

## 📋 개요

FCMS Oracle에서 제품코드 관련 테이블을 CDC로 PostgreSQL에 동기화합니다.

### 추가할 테이블

| 테이블명 | 설명 | PK |
|---------|------|-----|
| `MA_SELECTION_PATTERNS` | 제품코드 마스터 | `SELECTION_PATTERN_CODE` |
| `MA_SELECTION_PATTERN_DETAILS` | 용기/밸브 스펙 상세 | `SELECTION_PATTERN_CODE` + `SEQ_NO` |

### 주요 컬럼

**MA_SELECTION_PATTERNS**
```
SELECTION_PATTERN_CODE  -- PK, 제품 패턴 코드
TRADE_CONDITION_NO      -- 제품코드 (KF001, KF013 등)
PRIMARY_STORE_USER_CODE -- 고객코드 (KDKK)
CUSTOMER_USER_CODE      -- 엔드유저코드
```

**MA_SELECTION_PATTERN_DETAILS**
```
SELECTION_PATTERN_CODE  -- FK
SEQ_NO                  -- 순번
CYLINDER_SPEC_CODE      -- 용기스펙 코드
VALVE_SPEC_CODE         -- 밸브스펙 코드
```

---

## 🚀 서버 작업 순서

### 1단계: 현재 Debezium 설정 확인

```bash
# Kafka Connect에서 현재 커넥터 설정 확인
curl -s http://localhost:8083/connectors/oracle-fcms-cylcy-main/config | jq .
```

### 2단계: 테이블 목록 업데이트

현재 설정에서 `table.include.list`를 찾아서 새 테이블 추가:

```json
{
  "table.include.list": "FCMS.MA_CYLINDERS,FCMS.TR_LATEST_CYLINDER_STATUSES,FCMS.MA_ITEMS,FCMS.MA_CYLINDER_SPECS,FCMS.MA_VALVE_SPECS,FCMS.MA_SELECTION_PATTERNS,FCMS.MA_SELECTION_PATTERN_DETAILS"
}
```

### 3단계: 커넥터 업데이트

**방법 A: 커넥터 재생성 (권장)**

```bash
# 1. 커넥터 삭제
curl -X DELETE http://localhost:8083/connectors/oracle-fcms-cylcy-main

# 2. 새 설정으로 커넥터 생성
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @connector-config-updated.json
```

**방법 B: 설정만 업데이트**

```bash
curl -X PUT http://localhost:8083/connectors/oracle-fcms-cylcy-main/config \
  -H "Content-Type: application/json" \
  -d '{
    ... 기존 설정 ...,
    "table.include.list": "FCMS.MA_CYLINDERS,...,FCMS.MA_SELECTION_PATTERNS,FCMS.MA_SELECTION_PATTERN_DETAILS"
  }'
```

### 4단계: 동기화 확인

```bash
# PostgreSQL에서 테이블 확인
psql -U cynow -d cynow_db -c "SELECT COUNT(*) FROM fcms_cdc.ma_selection_patterns;"
psql -U cynow -d cynow_db -c "SELECT COUNT(*) FROM fcms_cdc.ma_selection_pattern_details;"
```

---

## 📊 PostgreSQL VIEW 생성

CDC 동기화 후 조회용 VIEW 생성:

```sql
-- 제품코드 + 상세 정보 조인 VIEW
CREATE OR REPLACE VIEW vw_product_codes AS
SELECT 
    sp."SELECTION_PATTERN_CODE" as selection_pattern_code,
    sp."TRADE_CONDITION_NO" as trade_condition_no,
    sp."PRIMARY_STORE_USER_CODE" as primary_store_user_code,
    sp."CUSTOMER_USER_CODE" as customer_user_code,
    spd."CYLINDER_SPEC_CODE" as cylinder_spec_code,
    spd."VALVE_SPEC_CODE" as valve_spec_code,
    -- 조인해서 이름 가져오기
    cs."NAME" as cylinder_spec_name,
    vs."NAME" as valve_spec_name,
    i."DISPLAY_NAME" as gas_name,
    c."CAPACITY" as capacity
FROM "fcms_cdc"."ma_selection_patterns" sp
LEFT JOIN "fcms_cdc"."ma_selection_pattern_details" spd 
    ON sp."SELECTION_PATTERN_CODE" = spd."SELECTION_PATTERN_CODE"
LEFT JOIN "fcms_cdc"."ma_cylinder_specs" cs 
    ON spd."CYLINDER_SPEC_CODE" = cs."CYLINDER_SPEC_CODE"
LEFT JOIN "fcms_cdc"."ma_valve_specs" vs 
    ON spd."VALVE_SPEC_CODE" = vs."VALVE_SPEC_CODE"
-- 가스명, 용량은 추가 조인 필요 (ITEM_CODE 연결)
LEFT JOIN "fcms_cdc"."ma_cylinders" c 
    ON spd."CYLINDER_SPEC_CODE" = c."CYLINDER_SPEC_CODE"
    AND spd."VALVE_SPEC_CODE" = c."VALVE_SPEC_CODE"
LEFT JOIN "fcms_cdc"."ma_items" i 
    ON c."ITEM_CODE" = i."ITEM_CODE";
```

---

## 🔄 CYNOW 동기화 명령어

CDC 테이블 추가 후 CYNOW에서 동기화:

```bash
cd /opt/cynow/cynow
source venv/bin/activate
python manage.py sync_product_codes
```

---

## ⚠️ 주의사항

1. **Debezium 재시작 필요**: 테이블 추가 시 커넥터 재시작 필요
2. **초기 스냅샷**: 새 테이블은 처음에 전체 스냅샷 수행 (시간 소요)
3. **스키마 변경**: Oracle 테이블 스키마 변경 시 Debezium 스키마 레지스트리 업데이트 필요
4. **백업 시간 회피**: 새벽 2시 Oracle 백업 시간에는 작업 피할 것

