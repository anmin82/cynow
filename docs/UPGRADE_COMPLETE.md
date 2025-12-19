# CYNOW 모델 리팩토링 및 기능 업그레이드 완료

## 완료된 작업

### 1. 실제 CDC 테이블 구조 기반 VIEW 생성 ✅

**이전**: 가정된 테이블 구조
**현재**: 실제 CDC 테이블 조인 기반

#### 생성된 VIEW

**vw_cynow_cylinder_list** (2,773개 행)
- `ma_cylinders` + `ma_items` + `ma_cylinder_specs` + `ma_valve_specs` + `tr_latest_cylinder_statuses` 조인
- 개별 용기 정보 제공
- 실제 컬럼명 사용

**vw_cynow_inventory** (70개 행)
- 용기종류 × 상태 × 위치별 집계
- `cylinder_type_key`를 SQL에서 MD5로 생성
- 집계된 수량 정보

### 2. 컬럼 매핑 개선 ✅

| CYNOW 필드 | CDC 테이블/컬럼 | 비고 |
|-----------|----------------|------|
| `gas_name` | `ma_items.DISPLAY_NAME` 또는 `FORMAL_NAME` | 가스명 |
| `capacity` | `ma_cylinders.CAPACITY` | 용량 |
| `valve_spec` | `ma_valve_specs.NAME` | 밸브 스펙명 |
| `cylinder_spec` | `ma_cylinder_specs.NAME` | 용기 스펙명 |
| `usage_place` | `ma_cylinders.USE_DEPARTMENT_CODE` | 사용 부서 코드 |
| `status` | `tr_latest_cylinder_statuses.CONDITION_CODE` → 변환 | 상태 코드 → 상태명 |
| `location` | `tr_latest_cylinder_statuses.POSITION_USER_NAME` | 위치 (일본어) |
| `pressure_due_date` | `ma_cylinders.WITHSTAND_PRESSURE_MAINTE_DATE` | 내압 유지일 |
| `last_event_at` | `tr_latest_cylinder_statuses.MOVE_DATE` | 이동일시 |

### 3. 코드 리팩토링 ✅

#### 새로운 유틸리티 모듈
- `core/utils/view_helper.py`
  - `extract_valve_type()`: 밸브 형식 추출 (CGA/DISS/DIN)
  - `group_cylinder_types()`: 용기종류 그룹화
  - `calculate_risk_level()`: 위험도 계산

#### 개선된 모듈
- `dashboard/views.py`: 헬퍼 함수 사용으로 코드 간소화
- `alerts/views.py`: 위험도 계산 로직 개선
- `core/repositories/view_repository.py`: `cylinder_type_key` 처리 개선

### 4. 기능 개선 ✅

#### cylinder_type_key 생성
- **이전**: Python에서 생성 (VIEW 조회 후)
- **현재**: SQL에서 MD5 해시로 생성
- **장점**: 
  - 성능 향상
  - 일관성 보장
  - 인덱스 활용 가능

#### 위험도 계산 개선
- 비율 기반 계산 추가
- 더 정확한 위험도 판단
- 헬퍼 함수로 재사용 가능

### 5. 데이터 검증 ✅

생성된 VIEW:
- `vw_cynow_inventory`: 70개 행
- `vw_cynow_cylinder_list`: 2,773개 행

샘플 데이터 확인:
- COS 가스: 보관 69개, 분석 7개, 이상 2개, 출하 179개, 폐기 10개
- 위치 정보: 일본어 텍스트 확인 (번역 시스템 적용 필요)

## 업그레이드된 기능

### 대시보드
- 실제 데이터 기반 표시
- 용기종류별 정확한 집계
- 상태별 수량 표시

### 알림
- 개선된 위험도 계산
- 비율 기반 판단
- 더 정확한 알림 메시지

### 용기 리스트
- 실제 용기 데이터 표시
- 필터링 기능 개선
- 상세 정보 표시

## 다음 단계

1. ✅ VIEW 생성 완료
2. ⏳ 번역 데이터 로드: `python manage.py load_translations`
3. ⏳ 웹 페이지에서 데이터 확인
4. ⏳ 추가 기능 테스트

## 사용 방법

### VIEW 재생성
```bash
python manage.py create_postgresql_views --force
```

### 번역 데이터 로드
```bash
python manage.py load_translations
```

### 데이터 확인
```bash
python manage.py check_sync_tables
```

## 주요 변경사항 요약

1. **VIEW 생성**: 실제 테이블 조인 기반으로 재작성
2. **컬럼 매핑**: 실제 CDC 테이블 컬럼명 사용
3. **코드 리팩토링**: 헬퍼 함수로 중복 제거
4. **성능 개선**: SQL에서 `cylinder_type_key` 생성
5. **기능 개선**: 위험도 계산, 그룹화 로직 개선











