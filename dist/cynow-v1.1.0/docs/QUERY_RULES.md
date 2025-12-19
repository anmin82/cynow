# 조회/집계 시 적용 규칙

## 1. EndUser 결정 우선순위

### 규칙
1. **예외 규칙 확인**: `cy_enduser_policy`에서 `cylinder_type_key`로 정확히 매칭되는 예외가 있으면 해당 `exception_enduser_code` 사용
2. **기본값 적용**: 예외가 없으면 `cy_enduser_policy`의 `default_enduser_code` 사용 (기본값: 'SDC')
3. **하드코딩 폴백**: 정책 테이블에 데이터가 없으면 'SDC' 사용

### 구현 예시
```python
def apply_enduser_policy(cursor, type_key, gas_name, capacity):
    # 1. 예외 규칙 확인
    cursor.execute("""
        SELECT exception_enduser_code, exception_enduser_name
        FROM cy_enduser_policy
        WHERE cylinder_type_key = %s AND is_active = TRUE
        ORDER BY id DESC LIMIT 1
    """, [type_key])
    result = cursor.fetchone()
    if result and result[0]:
        return result[0], result[1]
    
    # 2. 기본값
    cursor.execute("""
        SELECT default_enduser_code, default_enduser_name
        FROM cy_enduser_policy
        WHERE cylinder_type_key IS NULL AND is_active = TRUE
        ORDER BY id DESC LIMIT 1
    """)
    result = cursor.fetchone()
    if result:
        return result[0], result[1]
    
    # 3. 폴백
    return 'SDC', 'SDC'
```

### 주의사항
- `dashboard_cylinder_type_key`는 **enduser를 포함**하여 생성
- 따라서 enduser가 다른 용기는 다른 용기종류로 분리됨
- 예: CF4 YC 440L SDC와 CF4 YC 440L LGD는 다른 `cylinder_type_key`를 가짐

---

## 2. 밸브 Raw vs Dashboard 구분

### Raw 값 (`raw_valve_spec`)
- **용도**: 감사(audit), 이력 추적
- **소스**: FCMS 원본 값 그대로
- **변경**: 절대 변경하지 않음
- **조회**: 감사/디버깅 시에만 사용

### Dashboard 값 (`dashboard_valve_spec`)
- **용도**: 대시보드 표시, 집계, 그룹화
- **소스**: `cy_valve_alias` 정책 적용
- **변경**: 정책 변경 시 재계산됨
- **조회**: 모든 집계/표시 쿼리에서 사용

### 집계 쿼리 예시
```sql
-- ✅ 올바른 방법: dashboard_valve_spec 사용
SELECT 
    dashboard_valve_spec,
    COUNT(*) as qty
FROM cy_cylinder_current
GROUP BY dashboard_valve_spec;

-- ❌ 잘못된 방법: raw_valve_spec 사용 (NERIKI/HAMAI가 분리됨)
SELECT 
    raw_valve_spec,
    COUNT(*) as qty
FROM cy_cylinder_current
GROUP BY raw_valve_spec;
```

### 감사 쿼리 예시
```sql
-- 원본 밸브 정보 확인 (감사용)
SELECT 
    cylinder_no,
    raw_valve_spec,
    dashboard_valve_spec,
    dashboard_valve_format
FROM cy_cylinder_current
WHERE dashboard_valve_spec LIKE '%CGA330%';
```

---

## 3. 용기종류 그룹화 규칙

### 키 생성 로직
```
dashboard_cylinder_type_key = MD5(
    gas_name | 
    capacity | 
    valve_spec(표준화) | 
    cylinder_spec | 
    usage_place | 
    enduser_code  ← 중요!
)
```

### 집계 쿼리
```sql
-- 대시보드 집계 (enduser 포함)
SELECT 
    dashboard_cylinder_type_key,
    dashboard_gas_name,
    dashboard_capacity,
    dashboard_valve_spec,  -- 표준화된 값
    dashboard_cylinder_spec,
    dashboard_enduser_code,  -- enduser 포함!
    dashboard_status,
    COUNT(*) as qty
FROM cy_cylinder_current
WHERE is_available = TRUE
GROUP BY 
    dashboard_cylinder_type_key,
    dashboard_gas_name,
    dashboard_capacity,
    dashboard_valve_spec,
    dashboard_cylinder_spec,
    dashboard_enduser_code,
    dashboard_status
ORDER BY dashboard_gas_name, dashboard_status;
```

---

## 4. 정책 변경 시 재계산

### 정책 변경 후 스냅샷 재생성
```bash
# 전체 재생성 (정책 변경 후)
python manage.py sync_cylinder_snapshot --full

# 또는 증분 갱신 (정책 변경 감지 시)
python manage.py sync_cylinder_snapshot
```

### 정책 버전 관리
- `cy_cylinder_current.policy_version` 필드로 정책 버전 추적
- 정책 변경 시 버전 증가
- 특정 버전 기준으로 스냅샷 재생성 가능

---

## 5. 성능 최적화

### 인덱스 활용
```sql
-- 집계 쿼리 최적화
CREATE INDEX idx_cy_current_agg ON cy_cylinder_current(
    dashboard_cylinder_type_key, 
    dashboard_status, 
    is_available
) WHERE is_available = TRUE;

-- 필터링 최적화
CREATE INDEX idx_cy_current_filter ON cy_cylinder_current(
    LOWER(dashboard_gas_name), 
    LOWER(dashboard_status), 
    dashboard_enduser_code
);
```

### 쿼리 최적화 팁
1. **항상 `dashboard_*` 컬럼 사용**: Raw 값은 감사용으로만
2. **인덱스 활용**: `dashboard_cylinder_type_key`, `dashboard_status` 등
3. **파티셔닝 고려**: 상태별 파티셔닝 (대용량 시)

