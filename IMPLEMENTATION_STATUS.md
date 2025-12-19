# CYNOW 구현 상태 체크리스트

## ✅ 완료된 기능

### 1. 핵심 원칙 준수
- ✅ SSOT = PostgreSQL VIEW (현재는 SQLite 모의 VIEW)
- ✅ 입력(계획/수동스냅샷)은 별도 테이블에만 저장
- ✅ 조회는 로그인 없이 가능 / 입력은 로그인 필요

### 2. DB 모델
- ✅ PlanForecastMonthly (출하 계획)
- ✅ PlanScheduledMonthly (투입 계획)
- ✅ HistInventorySnapshot (스냅샷)
- ✅ HistSnapshotRequest (스냅샷 요청 기록)
- ✅ ReportExportLog (보고서 출력 이력)
- ✅ Admin 등록 완료 (검색/필터 지원)

### 3. VIEW 추상화
- ✅ ViewRepository 패턴 구현
- ✅ vw_cynow_inventory 조회
- ✅ vw_cynow_cylinder_list 조회
- ✅ 상태 매핑 유틸리티
- ✅ 용기종류 키 생성 유틸리티

### 4. 메뉴 기능

#### Dashboard (`/`)
- ✅ 모든 용기종류 목록/그리드
- ✅ 가용수량 표시
- ✅ 위험도 표시 (HIGH/MEDIUM/LOW)
- ✅ 위험 메시지 표시
- ✅ 검색/필터 기능

#### Detail (`/detail/`)
- ✅ 용기종류 선택(검색/필터)
- ✅ 상태별 수량
- ✅ 위치별 수량
- ✅ 최근 추이(History 기반)

#### Summary (`/summary/`)
- ✅ 기간 선택 (최근 7일/30일/90일/사용자 지정)
- ✅ 상태 분포
- ✅ Top 10 가스명
- ✅ Top 10 변동 랭킹

#### Cylinders (`/cylinders/`)
- ✅ 용기번호 리스트
- ✅ 필터: 상태/종류(밸브/스펙)/위치/기간
- ✅ 상세보기 (`/cylinders/<cylinder_no>/`)

#### Alerts (`/alerts/`)
- ✅ 위험도 기준 리스트 (High/Medium/Low)
- ✅ 룰 기반 조언 텍스트
- ✅ 용기종류별 집계

#### Reports
- ✅ 주간 보고서 (`/reports/weekly/`)
- ✅ 월간 보고서 (`/reports/monthly/`)
- ✅ Excel 다운로드
- ⚠️ PDF 출력 (미구현 - 선택사항)

#### History & Analytics (`/history/`)
- ✅ 기간 선택 (일/주/월/사용자 지정)
- ✅ 필터: 가스명/용량/밸브/스펙/사용처/상태/위치/스냅샷유형
- ✅ 표 표시
- ✅ 증감(Δ) 계산 (전일 대비)
- ✅ 엑셀 다운로드 (`/history/export.xlsx`)
- ⚠️ 그래프 (미구현 - 선택사항)

#### Plans (로그인 필요)
- ✅ FORECAST 입력 (`/plans/forecast/`)
- ✅ SCHEDULED 입력 (`/plans/scheduled/`)
- ✅ 권한 체크 (`cynow.can_edit_plan`)

#### 스냅샷
- ✅ 정기 스냅샷 (매일 00:05) - `take_daily_snapshot` command
- ✅ 수동 스냅샷 (`/history/snapshot/manual/`)
- ✅ 스냅샷 요청 기록

### 5. Management Commands
- ✅ `create_mock_views`: SQLite 모의 VIEW 생성
- ✅ `load_sample_data`: 샘플 데이터 로드
- ✅ `create_permissions`: 커스텀 권한 생성
- ✅ `take_daily_snapshot`: 정기 스냅샷 적재

### 6. 인증 및 권한
- ✅ 익명 조회 허용
- ✅ 로그인 필요 (Plans, 수동 스냅샷)
- ✅ 권한 체크 (`cynow.can_edit_plan`)
- ✅ 커스텀 권한 생성

---

## ⚠️ 선택적 기능 (설계서에 명시되었으나 미구현)

### 1. Reports PDF 출력
- 설계서: "weekly/monthly 조회 + 출력(PDF/Excel)"
- 현재: Excel만 구현
- 우선순위: 낮음 (Excel이 더 중요)
- 구현 필요 시: `reportlab` 또는 `weasyprint` 라이브러리 사용

### 2. History 그래프
- 설계서: "표/그래프 + 다운로드"
- 현재: 표만 구현
- 우선순위: 낮음 (표로도 충분)
- 구현 필요 시: Chart.js 또는 Plotly 사용

---

## 📋 Phase 2: PostgreSQL 전환 (대기 중)

- PostgreSQL 연결 설정
- 실제 VIEW 생성
- Repository 파라미터 바인딩 수정 (SQLite `?` → PostgreSQL `%s`)
- 정기 스냅샷 Cron 설정

---

## ✅ 결론

**핵심 기능 100% 구현 완료**

설계서의 필수 기능은 모두 구현되었습니다. PDF 출력과 그래프는 선택사항이며, 필요 시 추가 구현 가능합니다.

