# CYNOW 기능 업그레이드 요약

## 완료된 주요 업그레이드

### 1. 실제 CDC 테이블 구조 기반 VIEW 생성 ✅

#### 생성된 VIEW
- **vw_cynow_cylinder_list**: 2,773개 행 (개별 용기)
- **vw_cynow_inventory**: 70개 행 (용기종류 × 상태 × 위치 집계)

#### 테이블 조인 구조
```
ma_cylinders (용기 마스터)
  ├─ LEFT JOIN ma_items (가스 정보)
  ├─ LEFT JOIN ma_cylinder_specs (용기 스펙)
  ├─ LEFT JOIN ma_valve_specs (밸브 스펙)
  └─ LEFT JOIN tr_latest_cylinder_statuses (최신 상태)
```

### 2. 컬럼 매핑 개선 ✅

| 필드 | 소스 | 설명 |
|------|------|------|
| `gas_name` | `ma_items.DISPLAY_NAME` / `FORMAL_NAME` | 가스명 (일본어 가능) |
| `capacity` | `ma_cylinders.CAPACITY` | 용량 (numeric) |
| `valve_spec` | `ma_valve_specs.NAME` | 밸브 스펙명 (예: "CGA330") |
| `cylinder_spec` | `ma_cylinder_specs.NAME` | 용기 스펙명 (예: "BN SUS WELDING") |
| `usage_place` | `ma_cylinders.USE_DEPARTMENT_CODE` | 사용 부서 코드 |
| `status` | `tr_latest_cylinder_statuses.CONDITION_CODE` → 변환 | 상태 코드 → 상태명 |
| `location` | `tr_latest_cylinder_statuses.POSITION_USER_NAME` | 위치 (일본어) |
| `pressure_due_date` | `ma_cylinders.WITHSTAND_PRESSURE_MAINTE_DATE` | 내압 유지일 |
| `last_event_at` | `tr_latest_cylinder_statuses.MOVE_DATE` | 이동일시 |

### 3. 코드 리팩토링 ✅

#### 새로운 모듈
- `core/utils/view_helper.py`
  - `extract_valve_type()`: 밸브 형식 추출
  - `group_cylinder_types()`: 용기종류 그룹화
  - `calculate_risk_level()`: 위험도 계산

#### 개선된 모듈
- `dashboard/views.py`: 헬퍼 함수 사용
- `alerts/views.py`: 위험도 계산 개선
- `core/repositories/view_repository.py`: `cylinder_type_key` 처리 개선

### 4. 성능 개선 ✅

#### cylinder_type_key 생성
- **이전**: Python에서 생성 (VIEW 조회 후)
- **현재**: SQL에서 MD5 해시로 생성
- **효과**: 
  - 쿼리 성능 향상
  - 일관성 보장
  - 인덱스 활용 가능

### 5. 기능 개선 ✅

#### 위험도 계산
- 비율 기반 계산 추가
- 더 정확한 위험도 판단
- 4단계 위험도 (HIGH, MEDIUM, LOW, NORMAL)

#### 용기종류 그룹화
- `cylinder_type_key` 기반 그룹화
- 밸브 형식 추출 (CGA/DISS/DIN)
- 상태별 집계 개선

## 확인된 데이터

### 가스 종류
- CF4
- CLF3
- COS
- COS 4N KDK

### 밸브 스펙
- CGA320, CGA330, CGA716, CGA722
- JIS-R
- BRASS, SUS 재질

### 용기 스펙
- BN (Bottle Neck)
- YC (Yoke)
- 재질: SUS, Mn-St, CR-Mo

### 위치
- KDKK
- 工場倉庫 (공장 창고) - 일본어

## 번역 시스템

### 발견된 일본어 데이터
- 위치명: `工場倉庫` (공장 창고)
- 기타 필드에도 일본어 포함 가능

### 번역 로드 결과
- `gas_name`: 4개
- `valve_spec`: 8개
- `cylinder_spec`: 5개
- `usage_place`: 1개
- `location`: 2개
- **총 20개** 번역 엔트리 생성

## 다음 단계

1. ✅ VIEW 생성 완료
2. ✅ 번역 데이터 로드 완료
3. ⏳ 관리자 페이지에서 번역 수정
4. ⏳ 웹 페이지에서 데이터 확인
5. ⏳ 추가 기능 테스트

## 사용 가이드

### VIEW 재생성
```bash
python manage.py create_postgresql_views --force
```

### 번역 관리
1. `/admin/core/translation/` 접속
2. 일본어 원문 찾기
3. 한국어 번역 입력
4. 활성화 체크
5. 저장

### 데이터 확인
```bash
# 테이블 확인
python manage.py check_sync_tables

# VIEW 확인
python manage.py test_db_connection
```

## 주요 개선 효과

1. **정확성**: 실제 데이터 기반으로 정확한 정보 제공
2. **성능**: SQL에서 집계 및 키 생성으로 성능 향상
3. **유지보수성**: 헬퍼 함수로 코드 중복 제거
4. **확장성**: 새로운 필드 추가 용이
5. **번역**: 일본어 데이터를 한국어로 표시 가능


