# CYNOW (CYLINDER NOW) - 용기 관리 시스템

FCMS(Oracle) → Debezium/Kafka → PostgreSQL(동기화 테이블 + VIEW)를 진실 데이터로 삼아 용기 수량을 통제/보고하는 시스템입니다.

## 설치 및 실행

### 1. 가상환경 생성 및 활성화
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### 2. 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. 환경 변수 설정
`.env` 파일을 생성하고 필요한 설정을 추가하세요 (선택사항).

### 4. 데이터베이스 마이그레이션
```bash
python manage.py migrate
```

### 5. 모의 VIEW 및 샘플 데이터 생성
```bash
# 모의 VIEW 생성
python manage.py create_mock_views

# 샘플 데이터 로드 (전체)
python manage.py load_sample_data

# 샘플 데이터 로드 (제한 - 테스트용)
python manage.py load_sample_data --limit 100
```

**참고**: `V_CYLCY_CDC_MIN_202512141804.md` 파일이 프로젝트 루트에 있어야 합니다.

### 6. 권한 생성
```bash
python manage.py create_permissions
```

### 7. 관리자 계정 생성
```bash
python manage.py createsuperuser
```

### 8. 서버 실행
```bash
python manage.py runserver
```

## 주요 기능

- **대시보드**: 모든 용기종류 현황을 한눈에 확인 (가용수량, 위험도 표시)
- **현황**: 용기종류별 상세 현황 (상태별/위치별 수량)
- **요약**: 용기종류별 통계 및 그래프 (상태별 분포, Top 10 가스명)
- **용기**: 용기번호별 리스트 및 상세 정보 (필터링 지원)
- **알림**: 위험도 기준 알림 (HIGH/MEDIUM/LOW)
- **보고서**: 주간/월간 보고서
- **이력**: 변화 이력 및 분석 (필터링, 엑셀 다운로드)
- **계획**: 출하 계획(FORECAST) 및 투입 계획(SCHEDULED) 입력 (로그인 필요)
- **스냅샷**: 정기 스냅샷(매일 00:05) 및 수동 스냅샷 저장

## URL 구조

### 공개 메뉴 (익명 접근 가능)
- `/` - 대시보드
- `/detail/` - 현황
- `/summary/` - 요약
- `/cylinders/` - 용기 리스트
- `/alerts/` - 알림
- `/reports/weekly/` - 주간 보고서
- `/reports/monthly/` - 월간 보고서
- `/history/` - 이력 분석

### 로그인 필요
- `/accounts/login/` - 로그인
- `/plans/forecast/` - 출하 계획
- `/plans/scheduled/` - 투입 계획
- `/history/snapshot/manual/` - 수동 스냅샷

## Phase 2: PostgreSQL 전환

실제 PostgreSQL 서버로 전환할 때는:

1. `.env` 파일에서 `DB_ENGINE=postgresql` 설정
2. PostgreSQL 연결 정보 설정
3. `core/repositories/view_repository.py`에서 실제 VIEW 조회 로직 구현
4. 실제 동기화 테이블명에 맞게 VIEW 생성 SQL 수정

## 개발 상태

- Phase 1 (SQLite 기반 개발): ✅ 완료
  - ✅ Django 프로젝트 및 앱 구조
  - ✅ DB 모델 및 마이그레이션
  - ✅ VIEW 추상화 레이어 (Repository 패턴)
  - ✅ 상태 매핑 유틸리티
  - ✅ 샘플 데이터 로딩
  - ✅ 인증 및 권한
  - ✅ 모든 메뉴 기능 구현
  - ✅ Plans 폼 (FORECAST/SCHEDULED)
  - ✅ History 스냅샷 (정기/수동)
  - ✅ 엑셀 다운로드
- Phase 2 (PostgreSQL 전환): ⏳ 대기 중

## Management Commands

- `create_mock_views`: SQLite 모의 VIEW 생성
- `load_sample_data`: 샘플 데이터 로드
- `create_permissions`: 커스텀 권한 생성
- `take_daily_snapshot`: 정기 스냅샷 적재 (cron 설정 필요)
- `check_kafka_sink`: Kafka PostgreSQL Sink Connector 상태 확인 및 문제 진단
- `check_sync_tables`: PostgreSQL에서 FCMS 동기화 테이블 확인
- `test_db_connection`: PostgreSQL 연결 테스트

## 문제 해결

### Kafka Sink Connector Task 실패

- **빠른 해결**: `docs/KAFKA_SINK_QUICK_FIX.md`
- **스키마 진화 실패**: `docs/SCHEMA_EVOLUTION_FIX.md` (가장 흔한 문제)
- **전체 가이드**: `docs/postgresql_sink_troubleshooting.md`
- **자동 수정 스크립트**: `scripts/fix_schema_evolution.sh`

