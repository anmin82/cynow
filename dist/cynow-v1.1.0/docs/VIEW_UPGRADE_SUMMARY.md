# VIEW 업그레이드 요약

## 완료된 작업

### 1. 실제 CDC 테이블 구조 기반 VIEW 생성

**이전**: 단일 테이블 기반 (가정)
**현재**: 실제 테이블 조인 기반

#### 사용된 테이블
- `ma_cylinders` - 용기 마스터 (2,773개)
- `ma_items` - 가스/아이템 마스터 (12개)
- `ma_cylinder_specs` - 용기 스펙 (6개)
- `ma_valve_specs` - 밸브 스펙 (20개)
- `tr_latest_cylinder_statuses` - 최신 상태 (2,773개)

#### VIEW 구조

**vw_cynow_cylinder_list** (2,773개 행)
- 개별 용기 리스트
- 모든 마스터 테이블과 상태 테이블 조인
- 실제 컬럼명 사용

**vw_cynow_inventory** (70개 행)
- 용기종류 × 상태 × 위치별 집계
- `cylinder_type_key`를 SQL에서 MD5로 생성
- GROUP BY로 집계

### 2. 주요 개선사항

#### 컬럼 매핑
- `gas_name`: `ma_items.DISPLAY_NAME` 또는 `FORMAL_NAME`
- `valve_spec`: `ma_valve_specs.NAME`
- `cylinder_spec`: `ma_cylinder_specs.NAME`
- `capacity`: `ma_cylinders.CAPACITY`
- `usage_place`: `ma_cylinders.USE_DEPARTMENT_CODE`
- `status`: `tr_latest_cylinder_statuses.CONDITION_CODE` → 상태명 변환
- `location`: `tr_latest_cylinder_statuses.POSITION_USER_NAME`
- `pressure_due_date`: `ma_cylinders.WITHSTAND_PRESSURE_MAINTE_DATE`
- `last_event_at`: `tr_latest_cylinder_statuses.MOVE_DATE`

#### cylinder_type_key 생성
- **이전**: Python에서 생성 (VIEW 조회 후)
- **현재**: SQL에서 MD5 해시로 생성
- **장점**: 
  - 성능 향상
  - 일관성 보장
  - 인덱스 활용 가능

### 3. 코드 리팩토링

#### 새로운 유틸리티 모듈
- `core/utils/view_helper.py` 생성
  - `extract_valve_type()`: 밸브 형식 추출
  - `group_cylinder_types()`: 용기종류 그룹화
  - `calculate_risk_level()`: 위험도 계산

#### ViewRepository 개선
- `cylinder_type_key` 처리 로직 개선
- PostgreSQL에서 SQL로 생성된 키 사용

#### Dashboard 뷰 개선
- 헬퍼 함수 사용으로 코드 간소화
- `cylinder_type_key` 기반 필터링 개선

### 4. 데이터 검증

생성된 VIEW 데이터:
- `vw_cynow_inventory`: 70개 행 (용기종류 × 상태 × 위치 조합)
- `vw_cynow_cylinder_list`: 2,773개 행 (개별 용기)

샘플 데이터:
- COS 가스: 보관 69개, 분석 7개, 이상 2개, 출하 179개, 폐기 10개
- 위치: 일본어 텍스트 확인 (번역 시스템 적용 필요)

## 다음 단계

1. ✅ VIEW 생성 완료
2. ⏳ 번역 데이터 로드 (`python manage.py load_translations`)
3. ⏳ 웹 페이지에서 데이터 확인
4. ⏳ 추가 기능 테스트

## 사용 방법

### VIEW 재생성
```bash
python manage.py create_postgresql_views --force
```

### 데이터 확인
```bash
python manage.py check_sync_tables
```

### 번역 로드
```bash
python manage.py load_translations
```


