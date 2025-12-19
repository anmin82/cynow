# PostgreSQL 빠른 전환 가이드

## 즉시 실행

### 1. .env 파일 생성/수정

프로젝트 루트에 `.env` 파일이 없으면 생성하고, 있으면 수정하세요:

```env
DB_ENGINE=postgresql
DB_NAME=cycy_db
DB_USER=실제_사용자명
DB_PASSWORD=실제_비밀번호
DB_HOST=10.78.30.98
DB_PORT=5434
```

### 2. 연결 테스트

```bash
python manage.py test_db_connection
```

성공하면 PostgreSQL 버전과 테이블 목록이 표시됩니다.

### 3. 마이그레이션 실행

```bash
python manage.py migrate
```

### 4. CDC 테이블 확인

```bash
python manage.py check_sync_tables
```

### 5. VIEW 생성

```bash
python manage.py create_postgresql_views
```

## 완료!

이제 PostgreSQL을 사용합니다. 웹 서버를 실행하면 PostgreSQL 데이터베이스를 사용합니다.

```bash
python manage.py runserver
```

## 되돌리기 (SQLite로 복귀)

`.env` 파일에서:
```env
DB_ENGINE=sqlite3
```

또는 `DB_ENGINE` 라인을 삭제/주석 처리
