# CYNOW 데이터 아키텍처 설계 요약

## 핵심 설계 원칙

1. **FCMS 원천 데이터는 변경하지 않음** - `fcms_cdc` 스키마는 읽기 전용
2. **CYNOW 정책은 별도 테이블로 관리** - 운영 규칙과 원천 데이터 분리
3. **대시보드는 스냅샷 테이블만 조회** - VIEW 대신 `cy_cylinder_current` 사용
4. **Raw 값과 Dashboard 값 명확히 분리** - 감사용 vs 운영용

## 테이블 구조

### 정책 테이블 (CYNOW 전용)

1. **cy_enduser_default** - EndUser 기본값 (기본값 + 예외 구조)
2. **cy_enduser_exception** - EndUser 예외 (특정 용기번호만)
3. **cy_valve_group** - 밸브 그룹 정의
4. **cy_valve_group_mapping** - 밸브 → 그룹 매핑

### 스냅샷 테이블

**cy_cylinder_current** - 대시보드 조회 전용
- Raw 값: `raw_*` 접두사 (FCMS 원본)
- Dashboard 값: `dashboard_*` 접두사 (정책 적용)
- 집계용: `cylinder_type_key`, `is_available` 등

## EndUser 결정 우선순위

1. **예외 테이블** (`cy_enduser_exception`) - 용기번호 직접 매칭
2. **기본값 테이블** (`cy_enduser_default`) - 가스명/용량/스펙 매칭 (NULL = 와일드카드)
3. **최종 기본값** - 'SDC'

## 밸브 표준화 규칙

- **Raw 값**: `raw_valve_spec_name` (FCMS 원본, 감사용)
- **Dashboard 값**: `dashboard_valve_spec_name` (그룹의 primary 밸브 또는 원본)
- **그룹화**: `dashboard_valve_group_name` 사용
- **집계**: 그룹명 또는 표준화된 밸브명으로 그룹화

## 갱신 전략

### 권장: CDC 이벤트 기반 (Trigger)
- `ma_cylinders` 또는 `tr_latest_cylinder_statuses` 변경 시 자동 동기화
- 실시간 반영

### 대안: 배치 갱신
- 5분 간격 증분 갱신
- 일 1회 전체 갱신 (정합성 검증)

## 조회 규칙

### 대시보드/집계
- **항상 Dashboard 값 사용**: `dashboard_*` 컬럼
- **cylinder_type_key 기준 그룹화**: Dashboard 값 기준 MD5 해시
- **밸브 그룹화**: `dashboard_valve_group_name` 우선, 없으면 `dashboard_valve_spec_name`

### 감사/이력
- **Raw 값 사용**: `raw_*` 컬럼
- **원천 추적**: `cylinder_type_key_raw` (Raw 값 기준)

## 마이그레이션 체크리스트

- [ ] 1. 정책 테이블 생성
- [ ] 2. 초기 정책 데이터 입력
- [ ] 3. cy_cylinder_current 테이블 생성
- [ ] 4. 초기 스냅샷 생성
- [ ] 5. Trigger 설정
- [ ] 6. Repository 레이어 전환
- [ ] 7. 검증 및 모니터링
- [ ] 8. 기존 VIEW 제거 (선택)

## 성능 개선 효과

- **조회 성능**: 인덱스 최적화된 테이블 직접 조회
- **집계 성능**: 미리 계산된 `cylinder_type_key` 사용
- **확장성**: 정책 변경 시 스냅샷만 재생성

