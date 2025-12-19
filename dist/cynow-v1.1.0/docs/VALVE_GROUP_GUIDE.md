# 밸브 그룹 통합 가이드

## 개요

밸브 메이커(제조사)만 다른 경우에도 밸브 그룹으로 통합하여 대시보드에서 동일하게 표시할 수 있습니다.

예: COS CGA330에서 NERIKI와 HAMAI 두 제조사의 밸브를 하나의 그룹으로 통합

## 밸브 그룹 관리 방법

### 방법 1: Django 관리자 페이지 (권장) ⭐

#### 1단계: 밸브 그룹 생성

1. **서버 실행 후 관리자 페이지 접속**
   - http://127.0.0.1:8000/admin/
   - 로그인

2. **밸브 그룹 메뉴 선택**
   - 좌측 메뉴: **Core** → **밸브 그룹** 클릭

3. **그룹 추가**
   - 우측 상단 **밸브 그룹 추가** 버튼 클릭
   - 다음 정보 입력:
     - **그룹명**: 예) `COS_CGA330`
     - **설명**: 예) `COS CGA330 통합 그룹 (NERIKI/HAMAI)`
     - **활성화**: ✅ 체크
   - **저장** 버튼 클릭

#### 2단계: 밸브 매핑 추가

1. **밸브 그룹 매핑 메뉴 선택**
   - 좌측 메뉴: **Core** → **밸브 그룹 매핑** 클릭

2. **매핑 추가**
   - 우측 상단 **밸브 그룹 매핑 추가** 버튼 클릭
   - 다음 정보 입력:
     - **밸브 스펙 코드**: 예) `0000000004`
     - **밸브 스펙명**: 예) `SUS general Y CGA330 Y NERIKI`
     - **그룹**: 위에서 생성한 그룹 선택 (예: `COS_CGA330`)
     - **대표 밸브**: ✅ 체크 (이 그룹의 대표 밸브로 사용됨)
     - **활성화**: ✅ 체크
   - **저장**

3. **다른 메이커 밸브 추가**
   - 다시 **밸브 그룹 매핑 추가** 클릭
   - 다음 정보 입력:
     - **밸브 스펙 코드**: 예) `0000000005`
     - **밸브 스펙명**: 예) `SUS general Y CGA330 Y HAMAI`
     - **그룹**: 같은 그룹 선택 (`COS_CGA330`)
     - **대표 밸브**: ❌ 체크 해제 (대표는 하나만)
     - **활성화**: ✅ 체크
   - **저장**

#### 3단계: 밸브 그룹에서 직접 추가 (더 편리)

1. **밸브 그룹 편집**
   - **Core** → **밸브 그룹** → 생성한 그룹 클릭
   - 하단에 **밸브 그룹 매핑** 섹션이 표시됨

2. **인라인으로 추가**
   - **밸브 그룹 매핑 추가** 버튼 클릭
   - 밸브 정보 입력:
     - **밸브 스펙 코드**: `0000000004`
     - **밸브 스펙명**: `SUS general Y CGA330 Y NERIKI`
     - **대표 밸브**: ✅ 체크
     - **활성화**: ✅ 체크
   - **저장 후 다른 매핑 추가** 클릭하여 HAMAI도 추가

### 방법 2: 관리 명령어 (자동 감지)

```bash
# CGA330 NERIKI/HAMAI 자동 감지 및 그룹 생성
python manage.py load_valve_groups

# 미리보기
python manage.py load_valve_groups --dry-run
```

**참고**: 이 명령어는 CGA330과 NERIKI/HAMAI를 포함한 밸브를 자동으로 찾아서 그룹을 생성합니다.

### 방법 3: 직접 SQL

```sql
-- 1. 그룹 생성
INSERT INTO cy_valve_group (group_name, description, is_active)
VALUES ('COS_CGA330', 'COS CGA330 통합 그룹 (NERIKI/HAMAI)', TRUE)
ON CONFLICT (group_name) DO UPDATE SET is_active = TRUE
RETURNING id;

-- 2. 매핑 추가 (NERIKI를 primary로)
INSERT INTO cy_valve_group_mapping 
(valve_spec_code, valve_spec_name, group_id, is_primary, is_active)
VALUES 
('0000000004', 'SUS general Y CGA330 Y NERIKI', 1, TRUE, TRUE),
('0000000005', 'SUS general Y CGA330 Y HAMAI', 1, FALSE, TRUE)
ON CONFLICT (valve_spec_code, valve_spec_name) 
DO UPDATE SET 
    group_id = EXCLUDED.group_id,
    is_primary = EXCLUDED.is_primary,
    is_active = TRUE;
```

## 밸브 스펙명 확인 방법

관리자 페이지에서 밸브 스펙을 확인하려면:

1. **PostgreSQL에 직접 접속**하여 확인:
```sql
SELECT "VALVE_SPEC_CODE", "NAME"
FROM "fcms_cdc"."ma_valve_specs"
WHERE "NAME" LIKE '%CGA330%'
ORDER BY "NAME";
```

2. **또는 관리 명령어로 확인**:
```bash
python manage.py load_valve_groups --dry-run
```

## 동작 원리

### 그룹화 규칙

1. **같은 그룹에 속한 밸브들**:
   - 대시보드에서는 **대표 밸브(primary)**의 이름으로 표시
   - 집계 시 하나의 그룹으로 처리

2. **Raw 값은 유지**:
   - `raw_valve_spec_name`: 원본 밸브명 유지 (감사용)
   - `dashboard_valve_spec_name`: 그룹의 대표 밸브명 사용

3. **그룹화 예시**:
   - NERIKI: `SUS general Y CGA330 Y NERIKI` (대표)
   - HAMAI: `SUS general Y CGA330 Y HAMAI`
   - → 대시보드 표시: `SUS general Y CGA330 Y NERIKI` (대표 밸브)
   - → 그룹명: `COS_CGA330`

## 확인 방법

### 1. 관리자 페이지에서 확인

- **Core** → **밸브 그룹**: 그룹 목록 확인
- **Core** → **밸브 그룹 매핑**: 매핑 목록 확인

### 2. 스냅샷 테이블에서 확인

```sql
SELECT 
    raw_valve_spec_name,
    dashboard_valve_spec_name,
    dashboard_valve_group_name,
    COUNT(*) as qty
FROM cy_cylinder_current
WHERE dashboard_valve_group_name = 'COS_CGA330'
GROUP BY raw_valve_spec_name, dashboard_valve_spec_name, dashboard_valve_group_name;
```

### 3. 대시보드에서 확인

- http://127.0.0.1:8000/dashboard/
- 밸브 스펙이 그룹의 대표 밸브명으로 표시되는지 확인

## 다른 밸브 그룹 추가 예시

### 예시 1: 다른 CGA 타입

```sql
-- 그룹 생성
INSERT INTO cy_valve_group (group_name, description, is_active)
VALUES ('CGA350_GROUP', 'CGA350 통합 그룹', TRUE);

-- 매핑 추가
INSERT INTO cy_valve_group_mapping 
(valve_spec_code, valve_spec_name, group_id, is_primary, is_active)
SELECT 
    vs."VALVE_SPEC_CODE",
    vs."NAME",
    (SELECT id FROM cy_valve_group WHERE group_name = 'CGA350_GROUP'),
    CASE WHEN vs."NAME" LIKE '%MAKER1%' THEN TRUE ELSE FALSE END,
    TRUE
FROM "fcms_cdc"."ma_valve_specs" vs
WHERE vs."NAME" LIKE '%CGA350%';
```

### 예시 2: 관리자 페이지에서

1. **밸브 그룹 추가**: `CGA350_GROUP`
2. **밸브 그룹 매핑 추가**:
   - 각 메이커의 CGA350 밸브를 하나씩 추가
   - 첫 번째를 **대표 밸브**로 설정

## 주의사항

1. **대표 밸브는 하나만**: 각 그룹당 하나의 primary 밸브만 설정
2. **스냅샷 갱신**: 그룹 추가 후 스냅샷이 자동으로 갱신됩니다 (Trigger 설정 시)
3. **Raw 값 보존**: 원본 밸브 정보는 `raw_valve_spec_name`에 유지됨

## 스냅샷 갱신

그룹 추가 후 스냅샷 갱신:

```bash
# 전체 갱신
python manage.py sync_cylinder_current

# 증분 갱신
python manage.py sync_cylinder_current --incremental
```

