# Scale Gateway API - 구현 완료 보고서

**CYNOW 프로젝트 - 저울 TCP 데이터 수신 및 캐시 시스템**

구현 날짜: 2025-12-18

---

## 📋 구현 요약

Scale Gateway API가 성공적으로 구현되었습니다. 저울(FG-150KAL)로부터 TCP 연결을 통해 데이터를 수신하고, 최신 안정값(ST)을 메모리에 캐시하여 출하/회수 시스템에 제공하는 모든 기능이 완료되었습니다.

---

## 📁 구현된 파일 목록

### 1. Django 앱 구조

```
devices/
├── __init__.py
├── admin.py                    # ScaleWeightLog Admin 설정
├── apps.py
├── models.py                   # ScaleWeightLog 모델
├── views.py                    # REST API (latest, commit)
├── urls.py                     # URL 라우팅
├── README.md                   # 사용자 가이드
├── TESTING_GUIDE.md           # 테스트 가이드
│
├── scale_gateway/             # 핵심 모듈
│   ├── __init__.py
│   ├── parser.py              # FG-150KAL 데이터 파서
│   ├── state.py               # 스레드 안전 최신값 저장소
│   └── listener.py            # TCP 리스너
│
├── management/
│   ├── __init__.py
│   └── commands/
│       ├── __init__.py
│       └── scale_gateway_listener.py  # Django 커맨드
│
└── migrations/
    ├── __init__.py
    └── 0001_initial.py        # ScaleWeightLog 마이그레이션
```

---

## 🔧 수정된 파일

### config/settings.py

```python
# INSTALLED_APPS에 추가
INSTALLED_APPS = [
    ...
    'orders',   # 주문/출하 관리
    'devices',  # Scale Gateway API
]

# Scale Gateway API 설정 추가
SCALE_GATEWAY_LISTEN_HOST = os.getenv('SCALE_GATEWAY_LISTEN_HOST', '0.0.0.0')
SCALE_GATEWAY_LISTEN_PORT = int(os.getenv('SCALE_GATEWAY_LISTEN_PORT', '4001'))
SCALE_GATEWAY_IDLE_TIMEOUT_SEC = int(os.getenv('SCALE_GATEWAY_IDLE_TIMEOUT_SEC', '10'))
```

### config/urls.py

```python
urlpatterns = [
    ...
    # Scale Gateway API (내부망, POC는 인증 생략, 추후 인증 적용 권장)
    path('api/', include('devices.urls')),
]
```

---

## 🎯 구현된 기능

### 1. TCP 리스너 (devices/scale_gateway/listener.py)

- ✅ 포트 4001에서 TCP 연결 수락
- ✅ CRLF 기반 라인 버퍼링
- ✅ 연결 끊김 시 자동 재대기
- ✅ 파싱 예외 방어 처리
- ✅ UTF-8 디코딩 오류 처리

### 2. 데이터 파서 (devices/scale_gateway/parser.py)

- ✅ FG-150KAL 포맷 파싱: `ST , +000053.26 _kg`
- ✅ 상태 코드 처리: ST (안정), US (불안정), OL (과부하)
- ✅ Decimal 타입 변환
- ✅ 부호 처리 (+/-)
- ✅ 정규식 기반 robust 파싱

### 3. 상태 관리자 (devices/scale_gateway/state.py)

- ✅ 싱글톤 패턴
- ✅ 스레드 안전 (threading.Lock)
- ✅ 최신 안정값(ST) 캐시
- ✅ 수신 시각 기록

### 4. Django Management Command

```bash
python manage.py scale_gateway_listener [--host HOST] [--port PORT] [--scale-id ID]
```

- ✅ 커맨드라인 인자 지원
- ✅ 설정 파일 연동
- ✅ Ctrl+C 안전 종료

### 5. DB 모델 (ScaleWeightLog)

```python
class ScaleWeightLog(models.Model):
    scale_id              # 저울 ID (default="default")
    cylinder_no           # 용기번호 (인덱스)
    event_type            # SHIP | RETURN
    gross_kg              # 보호캡 제외 총무게
    raw_line              # 원본 라인
    received_at           # 수신 시각
    committed_at          # 확정 시각 (auto)
    arrival_shipping_no   # TR_ORDERS 연결 대비
    move_report_no        # TR_MOVE_REPORTS 연결 대비
```

- ✅ 인덱스: cylinder_no, event_type, arrival_shipping_no, move_report_no
- ✅ Admin 페이지 등록
- ✅ 마이그레이션 생성 및 적용

### 6. REST API

#### 6-1. GET /api/scale-gateway/latest/

최신 저울 데이터 조회

**응답 예시**:
```json
{
  "ok": true,
  "scale_id": "default",
  "status": "ST",
  "weight": 53.26,
  "raw": "ST , +000053.26 _kg",
  "received_at": "2025-12-18T10:11:12+09:00",
  "stale": false
}
```

#### 6-2. POST /api/scale-gateway/commit/

출하/회수 확정

**요청 예시**:
```json
{
  "cylinder_no": "CY123456789",
  "event_type": "SHIP",
  "arrival_shipping_no": "AS20251218-0001",
  "move_report_no": "MR20251218-0001"
}
```

**응답 예시**:
```json
{
  "ok": true,
  "id": 123,
  "cylinder_no": "CY123456789",
  "event_type": "SHIP",
  "gross_kg": 53.26,
  "committed_at": "2025-12-18T10:11:12+09:00"
}
```

### 7. 보안 및 오류 처리

- ✅ CSRF exempt (POC, 주석으로 추후 인증 권장)
- ✅ JSON 파싱 오류 처리
- ✅ 필수 파라미터 검증
- ✅ 안정값 없음 오류 처리
- ✅ Internal error 처리

### 8. 문서화

- ✅ **devices/README.md**: 전체 사용자 가이드
- ✅ **devices/TESTING_GUIDE.md**: 테스트 시나리오 및 명령어
- ✅ **systemd 유닛 파일 예시**: 운영 환경 배포
- ✅ 코드 주석: 모든 모듈에 docstring

---

## 🚀 실행 방법

### 1. 마이그레이션

```bash
cd c:\cynow
python manage.py migrate devices --skip-checks
```

### 2. 리스너 실행

```bash
python manage.py scale_gateway_listener
```

### 3. Django 서버 실행

```bash
python manage.py runserver
```

### 4. 저울 시뮬레이터 (PowerShell)

```powershell
$client = New-Object System.Net.Sockets.TcpClient
$client.Connect("localhost", 4001)
$stream = $client.GetStream()
$writer = New-Object System.IO.StreamWriter($stream)
$writer.WriteLine("ST , +000053.26 _kg")
$writer.Flush()
$writer.Close()
$client.Close()
```

### 5. API 테스트

#### 최신값 조회
```bash
curl http://localhost:8000/api/scale-gateway/latest/
```

#### 출하 확정
```bash
curl -X POST http://localhost:8000/api/scale-gateway/commit/ \
  -H "Content-Type: application/json" \
  -d '{"cylinder_no": "CY123456789", "event_type": "SHIP"}'
```

---

## 📊 데이터 흐름

```
저울(FG-150KAL)
    │
    │ TCP (포트 4001)
    ↓
ScaleGatewayListener
    │
    │ 라인 수신 ("ST , +000053.26 _kg\r\n")
    ↓
ScaleDataParser
    │
    │ 파싱 {'status': 'ST', 'weight': 53.26, ...}
    ↓
ScaleStateManager (메모리 캐시)
    │
    ├─→ GET /api/scale-gateway/latest/
    │   (최신값 조회)
    │
    └─→ POST /api/scale-gateway/commit/
        (확정 + DB 저장)
            ↓
        ScaleWeightLog (DB)
```

---

## 🔐 보안 고려사항

### 현재 상태 (POC)
- API 인증 없음 (`@csrf_exempt`)
- 내부망 전용 가정

### 프로덕션 권장사항
1. **API 인증 추가**
   - Token 기반 인증
   - Session 인증
   - IP 화이트리스트

2. **HTTPS 사용**
   - SSL/TLS 인증서 적용

3. **CSRF 보호**
   - `@csrf_exempt` 제거
   - CSRF 토큰 적용

4. **Rate Limiting**
   - Django Ratelimit 적용

5. **로깅 및 모니터링**
   - 접근 로그
   - 이상 패턴 탐지

---

## 🧪 테스트 시나리오

### ✅ 시나리오 1: 기본 흐름
1. 리스너 시작
2. 저울 데이터 전송 (ST)
3. 최신값 조회 API 호출
4. 출하 확정 API 호출
5. DB에서 로그 확인

### ✅ 시나리오 2: Stale 데이터
1. 저울 데이터 전송
2. 10초 대기
3. 최신값 조회 (stale: true)

### ✅ 시나리오 3: 안정값 없음
1. 리스너 실행 (데이터 없음)
2. 커밋 시도
3. 오류 응답 확인 (no_stable_weight)

### ✅ 시나리오 4: 불안정 상태
1. US 데이터 전송
2. 최신값 조회
3. 데이터 없음 확인 (ST만 캐시)

### ✅ 시나리오 5: 연결 끊김
1. 저울 연결
2. 데이터 전송
3. 연결 종료
4. 리스너 재대기 확인

---

## 📈 확장 가능성

### 1. 다중 저울 지원
- `scale_id`로 여러 저울 구분
- 각 저울별 최신값 관리

### 2. 웹소켓 실시간 푸시
- 저울 데이터 실시간 브로드캐스트
- 대시보드에서 실시간 모니터링

### 3. 데이터 분석
- 측정 히스토리 분석
- 용기별 무게 추이
- 이상치 탐지

### 4. TR_ORDERS 연동
- `arrival_shipping_no`로 자동 연결
- 출하 문서에 자동 무게 입력

### 5. TR_MOVE_REPORTS 연동
- `move_report_no`로 이동보고서 연결
- 회수 무게 자동 기록

---

## 📝 환경 설정 예시

### .env 파일

```bash
# Scale Gateway API
SCALE_GATEWAY_LISTEN_HOST=0.0.0.0
SCALE_GATEWAY_LISTEN_PORT=4001
SCALE_GATEWAY_IDLE_TIMEOUT_SEC=10
```

### systemd 유닛 파일

```ini
[Unit]
Description=CYNOW Scale Gateway API - TCP Listener
After=network.target postgresql.service

[Service]
Type=simple
User=cynow
Group=cynow
WorkingDirectory=/opt/cynow
EnvironmentFile=/opt/cynow/.env
ExecStart=/opt/cynow/venv/bin/python manage.py scale_gateway_listener
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

---

## 🎉 구현 완료 체크리스트

- ✅ Django 앱 생성 (`devices`)
- ✅ scale_gateway 모듈 구조
- ✅ settings.py 설정 추가
- ✅ parser.py 구현 (FG-150KAL 포맷)
- ✅ state.py 구현 (스레드 안전 캐시)
- ✅ listener.py 구현 (TCP 리스너)
- ✅ management command 구현
- ✅ ScaleWeightLog 모델 추가
- ✅ 마이그레이션 생성 및 적용
- ✅ REST API views 구현 (latest, commit)
- ✅ URL 라우팅 추가
- ✅ Admin 페이지 등록
- ✅ README 작성 (사용자 가이드)
- ✅ TESTING_GUIDE 작성
- ✅ systemd 유닛 파일 예시
- ✅ 코드 주석 완료

---

## 📚 참고 문서

1. **devices/README.md**: 전체 사용자 가이드 및 운영 방법
2. **devices/TESTING_GUIDE.md**: 테스트 명령어 및 시나리오
3. **이 문서**: 구현 완료 보고서

---

## 🔗 API 엔드포인트 요약

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/scale-gateway/latest/` | 최신 저울 데이터 조회 |
| POST | `/api/scale-gateway/commit/` | 출하/회수 확정 (DB 저장) |

---

## 👥 사용 대상

- **출하 담당자**: POP에서 출하 확정 시 저울 무게 자동 입력
- **회수 담당자**: 회수 확정 시 저울 무게 자동 입력
- **시스템 관리자**: 리스너 운영 및 모니터링
- **개발자**: API 연동 및 확장 개발

---

## 🐛 알려진 제한사항

1. **단일 연결 지원**: POC로 한 번에 하나의 저울만 연결 (추후 확장 가능)
2. **인증 없음**: 내부망 전용, 프로덕션에서는 인증 추가 필요
3. **메모리 캐시**: 서버 재시작 시 최신값 소실 (DB는 유지)

---

## 📞 문의

프로젝트 담당자에게 문의하세요.

---

**Scale Gateway API v1.0**  
**구현 완료일**: 2025-12-18  
**프로젝트**: CYNOW  
**상태**: ✅ 완료

---

**모든 요구사항이 성공적으로 구현되었습니다!** 🎉


