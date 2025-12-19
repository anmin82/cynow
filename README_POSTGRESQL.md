# PostgreSQL 전환 완료 상황

## 완료된 작업

1. ✅ **환경 설정**
   - `requirements.txt`에 `psycopg2-binary` 추가
   - `.env` 파일 생성 (사용자가 연결 정보 입력)

2. ✅ **코드 수정**
   - `core/repositories/view_repository.py`: PostgreSQL 호환 수정 (플레이스홀더 `%s` 지원)

3. ✅ **데이터베이스 생성**
   - PostgreSQL 데이터베이스 `cynow` 생성 완료
   - 연결 테스트 성공

4. ✅ **Django 마이그레이션**
   - 모든 앱 테이블 생성 완료:
     - `plan_forecast_monthly` (출하 계획)
     - `plan_scheduled_monthly` (투입 계획)
     - `hist_inventory_snapshot` (변화 이력 스냅샷)
     - `hist_snapshot_request` (스냅샷 요청 기록)
     - `report_export_log` (보고서 출력 이력)

## 대기 중인 작업

### VIEW 생성 (동기화 테이블 필요)

현재 PostgreSQL 데이터베이스에는 Django 앱 테이블만 있고, **FCMS에서 동기화된 소스 테이블이 아직 없습니다**.

VIEW 생성을 위해서는:

1. **Debezium/Kafka를 통한 동기화 확인**
   - FCMS Oracle DB (10.78.30.18) → Kafka → PostgreSQL (10.78.30.98:5434)
   - 동기화 테이블이 PostgreSQL에 생성되었는지 확인

2. **실제 테이블명 확인**
   ```bash
   python manage.py list_db_tables
   ```
   또는 PostgreSQL에 직접 접속하여 확인

3. **VIEW 생성 실행**
   ```bash
   python manage.py create_postgresql_views
   ```
   
   또는 수동으로 SQL 실행:
   - `sql/create_views.sql` 파일 참고
   - 실제 테이블명과 컬럼명에 맞춰 수정 후 실행

## 준비된 도구

### 1. 연결 테스트
```bash
python manage.py test_db_connection
```

### 2. 데이터베이스 목록 확인
```bash
python manage.py list_db_tables
```

### 3. VIEW 생성 (자동)
```bash
python manage.py create_postgresql_views
```

### 4. VIEW 생성 (수동)
`sql/create_views.sql` 파일을 편집하여 PostgreSQL에서 직접 실행

## 다음 단계

1. **동기화 테이블 확인**
   - Debezium/Kafka 연결 상태 확인
   - PostgreSQL에 동기화 테이블 생성 여부 확인
   - 실제 테이블명과 컬럼명 확인

2. **VIEW 생성**
   - 동기화 테이블이 준비되면 `create_postgresql_views` 명령 실행
   - 또는 `sql/create_views.sql`을 수정하여 수동 생성

3. **검증**
   ```python
   python manage.py shell
   ```
   ```python
   from core.repositories.view_repository import ViewRepository
   
   # 인벤토리 VIEW 조회
   inventory = ViewRepository.get_inventory_view()
   print(f"인벤토리 행 수: {len(inventory)}")
   
   # 용기 리스트 VIEW 조회
   cylinders = ViewRepository.get_cylinder_list_view(limit=10)
   print(f"용기 리스트: {len(cylinders)}")
   ```

## 참고 문서

- `POSTGRESQL_SETUP.md`: 상세 설정 가이드
- `CYNOW_설계서_v1.0.md`: 전체 시스템 설계서
- `sql/create_views.sql`: VIEW 생성 SQL 템플릿













