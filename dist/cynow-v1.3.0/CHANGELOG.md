# CYNOW 변경 이력

## [1.3.0] - 2025-12-18

### ✨ 신규 기능
- **Scale Gateway API**: 저울(FG-150KAL) TCP 데이터 수신 및 캐시 시스템
  - TCP 리스너 (포트 4001)
  - FG-150KAL 포맷 파싱 (`ST , +000053.26 _kg`)
  - 스레드 안전 최신값 메모리 캐시
  - REST API 엔드포인트:
    - `GET /api/scale-gateway/latest/` - 최신 저울 데이터 조회
    - `POST /api/scale-gateway/commit/` - 출하/회수 확정 (DB 저장)
  - ScaleWeightLog 모델 - 출하/회수 시점 무게 기록
  - Django Management Command: `python manage.py scale_gateway_listener`
  - systemd 유닛 파일 지원
  - Stale 데이터 감지 (10초 이상 수신 없음)
  - 확장 대비: `arrival_shipping_no`, `move_report_no` 컬럼

### 📱 장비 연동
- **FG-150KAL 저울**: TCP 연결을 통한 실시간 무게 측정
- **상태 코드 지원**:
  - `ST` (Stable): 안정 상태 - 캐시에 저장
  - `US` (Unstable): 불안정 상태 - 무시
  - `OL` (Overload): 과부하 - 경고 로그

### 🔧 기술적 개선
- **스레드 안전**: threading.Lock을 사용한 멀티스레드 환경 지원
- **방어적 파싱**: CRLF/UTF-8 디코딩 오류 처리
- **자동 재연결**: TCP 연결 끊김 시 자동 재대기

### 📦 데이터베이스
- `devices` 앱 추가
- `scale_weight_log` 테이블 추가
  - 용기별, 이벤트별 무게 기록
  - TR_ORDERS, TR_MOVE_REPORTS 연결 대비

### 📝 문서
- `devices/README.md` - 전체 사용자 가이드
- `devices/TESTING_GUIDE.md` - 테스트 시나리오
- `SCALE_GATEWAY_IMPLEMENTATION.md` - 구현 완료 보고서
- systemd 유닛 파일 예시

---

## [1.2.0] - 2025-12-17

### ✨ 신규 기능
- **QR코드 PDF 출력**: 용기 리스트에서 QR코드 PDF 다운로드 기능 추가
  - A4 용지에 한 줄 10개씩 QR코드 출력 (약 1cm x 1cm)
  - 각 QR코드 하단에 용기번호 표시
  - 최대 1,000건까지 지원
- **출력 드롭다운 메뉴**: 기존 "엑셀" 버튼을 "출력" 드롭다운으로 변경
  - 엑셀, QR 선택 가능

### 🔧 버그 수정
- **대시보드 필터링 수정**: 
  - `cylinder_type_key` 기준으로 그룹화하여 정확한 필터링 보장
  - 다른 가스가 섞여 나오던 문제 해결
- **엑셀 다운로드 수정**: 
  - 다중 필터(gases, locations, statuses) 지원 추가
  - 한글 파일명 인코딩 문제 수정 (RFC 5987 형식)

### 📦 의존성 추가
- `qrcode==8.2` - QR코드 생성
- `reportlab==4.4.6` - PDF 생성
- `Pillow==12.0.0` - 이미지 처리

---

## [1.1.0] - 2025-12-16

### 🔧 버그 수정
- **WHERE 절 중복 오류 수정**: Repository 쿼리에서 WHERE 절이 중복 추가되던 버그 수정
- **밸브 재질 추출 수정**: 밸브 그룹명 대신 원본 밸브 스펙에서 재질 추출하도록 변경

### ✨ 개선 사항
- **EndUser NULL 방지**: 가스명별 Fallback 정책 추가 (정책 없는 경우에도 기본 EndUser 적용)
- **다국어 번역 시스템 개선**: 
  - 모델 필드명 변경: `japanese_text`/`korean_text` → `source_text`/`display_ko`/`display_ja`/`display_en`
  - 한국어 기본 언어, 일본어/영어 선택 가능
  - 언어별 표시명 지원 (`get_display(lang)` 메서드)

### 📝 정책 업데이트
- COS → SEC (Fallback)
- CLF3 → SEC (Fallback)
- CF4 → SDC (Fallback)
- 위치 번역: 天安工場 → 천안공장

---

## [1.0.0] - 2025-12-16

### 🎉 첫 번째 릴리스

#### 주요 기능
- **대시보드**: 용기종류별 현황 카드 및 상세 테이블
- **용기 리스트**: 페이지네이션, 필터링 지원
- **상세 현황**: 용기종류별 상태 분포, 추이 그래프

#### 정책 관리
- **EndUser 정책**: 가스명별 기본 EndUser 설정, 용기별 예외 지정
- **밸브 그룹화**: 동일 밸브 표준화 (HAMAI/NERIKI → 그룹)
- **다국어 번역**: FCMS 원본 → 한국어 표시명 (일본어/영어 확장 가능)

#### 데이터 아키텍처
- **CDC 연동**: Debezium을 통한 FCMS 실시간 동기화
- **스냅샷 테이블**: `cy_cylinder_current` - 대시보드 조회 최적화
- **트리거 기반 동기화**: 자동 스냅샷 갱신

#### EndUser 기본값
- COS → SEC
- CLF3 → SEC
- CF4 → SDC

---

## 향후 계획
- [ ] 히스토리 분석 기능
- [ ] 리포트 생성
- [ ] 예측 기능
- [ ] 다국어 UI (일본어/영어)

