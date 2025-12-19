# CYNOW 데이터 아키텍처 설계 완료

## 설계 개요

FCMS 원천 데이터를 기반으로 CYNOW 운영 정책을 적용한 스냅샷 테이블 구조로 전환하여 대시보드 성능을 개선합니다.

## 핵심 설계 원칙

1. **FCMS 원천 데이터는 변경하지 않음** - `fcms_cdc` 스키마는 읽기 전용
2. **CYNOW 정책은 별도 테이블로 관리** - 운영 규칙과 원천 데이터 분리
3. **대시보드는 스냅샷 테이블만 조회** - VIEW 대신 `cy_cylinder_current` 사용
4. **Raw 값과 Dashboard 값 명확히 분리** - 감사용 vs 운영용

## 생성된 파일

### SQL 파일
- `sql/create_cynow_policy_tables.sql` - 정책 테이블 DDL
- `sql/create_cy_cylinder_current.sql` - 스냅샷 테이블 DDL
- `sql/create_sync_triggers.sql` - 자동 동기화 Trigger 및 함수

### Django 코드
- `core/models.py` - EndUserDefault, EndUserException, ValveGroup, ValveGroupMapping 모델
- `core/admin.py` - 관리자 페이지 등록
- `core/repositories/cylinder_repository.py` - 스냅샷 테이블 조회용 Repository
- `core/management/commands/sync_cylinder_current.py` - 스냅샷 동기화 명령어
- `core/management/commands/load_enduser_defaults.py` - EndUser 기본값 로드
- `core/management/commands/load_valve_groups.py` - 밸브 그룹 로드
- `core/management/commands/verify_cylinder_current.py` - 스냅샷 검증

### 문서
- `docs/CYNOW_DATA_ARCHITECTURE.md` - 상세 설계 문서
- `docs/MIGRATION_GUIDE.md` - 마이그레이션 가이드
- `docs/DATA_ARCHITECTURE_SUMMARY.md` - 요약 문서
- `docs/QUICK_START_SNAPSHOT.md` - 빠른 시작 가이드

## 테이블 구조

### 정책 테이블
1. **cy_enduser_default** - EndUser 기본값 (기본값 + 예외 구조)
2. **cy_enduser_exception** - EndUser 예외 (특정 용기번호만)
3. **cy_valve_group** - 밸브 그룹 정의
4. **cy_valve_group_mapping** - 밸브 → 그룹 매핑

### 스냅샷 테이블
**cy_cylinder_current** - 대시보드 조회 전용
- Raw 값: `raw_*` 접두사 (FCMS 원본)
- Dashboard 값: `dashboard_*` 접두사 (정책 적용)
- 집계용: `cylinder_type_key`, `is_available` 등

## 적용 규칙

### EndUser 결정 우선순위
1. **예외 테이블** (`cy_enduser_exception`) - 용기번호 직접 매칭
2. **기본값 테이블** (`cy_enduser_default`) - 가스명/용량/스펙 매칭 (NULL = 와일드카드)
3. **최종 기본값** - 'SDC'

### 밸브 표준화
- **Raw 값**: `raw_valve_spec_name` (FCMS 원본, 감사용)
- **Dashboard 값**: `dashboard_valve_spec_name` (그룹의 primary 밸브 또는 원본)
- **그룹화**: `dashboard_valve_group_name` 사용

### 사용처 파싱
- location과 조합하여 "KDKK/LGD" 형식으로 표시
- 이미 "/"가 포함되어 있으면 그대로 사용

## 다음 단계

1. 마이그레이션 실행: `python manage.py migrate`
2. 정책 테이블 생성: SQL 파일 실행
3. 초기 데이터 입력: 관리 명령어 실행
4. 스냅샷 생성: `python manage.py sync_cylinder_current`
5. Repository 전환: ViewRepository → CylinderRepository

