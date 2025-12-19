# Scale Gateway API

**CYNOW 프로젝트 - 저울 TCP 데이터 수신 및 캐시 시스템**

---

## 📋 개요

Scale Gateway API는 저울(FG-150KAL)로부터 TCP 연결을 통해 데이터를 수신하고, 최신 안정값(ST)을 메모리에 캐시하여 출하/회수 시스템에 제공하는 기능입니다.

### 주요 기능

- **TCP 리스너**: 저울로부터 실시간 데이터 수신
- **데이터 파싱**: FG-150KAL 포맷 파싱 (`ST , +000053.26 _kg`)
- **메모리 캐시**: 최신 안정값(ST)을 스레드 안전하게 저장
- **REST API**: 최신값 조회 및 확정(Commit) API 제공
- **DB 로그**: 출하/회수 확정 시점의 무게를 영구 저장

---

## 🏗️ 아키텍처

```
저울(TCP)  →  Listener  →  Parser  →  State Manager  →  API
                                              ↓
                                         ScaleWeightLog (DB)
```

### 구성 요소

- `devices/scale_gateway/listener.py`: TCP 소켓 리스너
- `devices/scale_gateway/parser.py`: 데이터 파싱 (ST/US/OL 상태)
- `devices/scale_gateway/state.py`: 스레드 안전 최신값 저장소
- `devices/models.py`: ScaleWeightLog 모델 (DB)
- `devices/views.py`: REST API 엔드포인트
- `devices/management/commands/scale_gateway_listener.py`: Django 커맨드

---

## ⚙️ 설정

### settings.py

```python
# Scale Gateway API 설정
SCALE_GATEWAY_LISTEN_HOST = '0.0.0.0'
SCALE_GATEWAY_LISTEN_PORT = 4001
SCALE_GATEWAY_IDLE_TIMEOUT_SEC = 10  # 최신 데이터 유효 시간(초)
```

환경변수로도 설정 가능:

```bash
export SCALE_GATEWAY_LISTEN_HOST=0.0.0.0
export SCALE_GATEWAY_LISTEN_PORT=4001
export SCALE_GATEWAY_IDLE_TIMEOUT_SEC=10
```

---

## 🚀 실행 방법

### 1. 마이그레이션 적용

```bash
cd /path/to/cynow
python manage.py migrate devices
```

### 2. 리스너 실행 (개발/테스트)

```bash
# 기본 설정으로 실행
python manage.py scale_gateway_listener

# 커스텀 설정으로 실행
python manage.py scale_gateway_listener --host 0.0.0.0 --port 4001 --scale-id default
```

### 3. 저울 연결 테스트

저울 또는 시뮬레이터를 포트 4001에 연결:

```bash
# 시뮬레이터 예시 (다른 터미널)
echo "ST , +000053.26 _kg" | nc localhost 4001
```

---

## 📡 API 사용법

### 1. 최신값 조회

**Endpoint**: `GET /api/scale-gateway/latest/`

**응답 (성공)**:

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

**응답 (데이터 없음)**:

```json
{
  "ok": false,
  "error": "no_data",
  "message": "저울 데이터가 없습니다"
}
```

**curl 예시**:

```bash
curl http://localhost:8000/api/scale-gateway/latest/
```

---

### 2. 출하/회수 확정 (커밋)

**Endpoint**: `POST /api/scale-gateway/commit/`

**요청 Body**:

```json
{
  "cylinder_no": "CY123456789",
  "event_type": "SHIP",
  "arrival_shipping_no": "AS20251218-0001",
  "move_report_no": "MR20251218-0001"
}
```

**필수 필드**:
- `cylinder_no`: 용기번호
- `event_type`: `SHIP` (출하) 또는 `RETURN` (회수)

**선택 필드**:
- `arrival_shipping_no`: 입출고번호 (TR_ORDERS 연결용)
- `move_report_no`: 이동보고서번호 (TR_MOVE_REPORTS 연결용)

**응답 (성공)**:

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

**응답 (안정값 없음)**:

```json
{
  "ok": false,
  "error": "no_stable_weight",
  "message": "안정된 저울 데이터(ST)가 없습니다"
}
```

**curl 예시**:

```bash
curl -X POST http://localhost:8000/api/scale-gateway/commit/ \
  -H "Content-Type: application/json" \
  -d '{
    "cylinder_no": "CY123456789",
    "event_type": "SHIP",
    "arrival_shipping_no": "AS20251218-0001"
  }'
```

---

## 🔧 운영 방법

### systemd 유닛 파일 예시

리스너를 systemd 서비스로 등록하여 자동 시작/재시작 관리:

**파일 위치**: `/etc/systemd/system/cynow-scale-gateway.service`

```ini
[Unit]
Description=CYNOW Scale Gateway API - TCP Listener
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=cynow
Group=cynow
WorkingDirectory=/opt/cynow

# 환경변수 파일 로드
EnvironmentFile=/opt/cynow/.env

# 리스너 실행
ExecStart=/opt/cynow/venv/bin/python manage.py scale_gateway_listener

# 재시작 정책
Restart=on-failure
RestartSec=5s
StartLimitInterval=300
StartLimitBurst=5

# 로그 설정
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cynow-scale-gateway

[Install]
WantedBy=multi-user.target
```

### systemd 서비스 관리

```bash
# 서비스 파일 등록
sudo systemctl daemon-reload

# 서비스 활성화 (부팅 시 자동 시작)
sudo systemctl enable cynow-scale-gateway

# 서비스 시작
sudo systemctl start cynow-scale-gateway

# 서비스 상태 확인
sudo systemctl status cynow-scale-gateway

# 로그 확인
sudo journalctl -u cynow-scale-gateway -f

# 서비스 재시작
sudo systemctl restart cynow-scale-gateway

# 서비스 중지
sudo systemctl stop cynow-scale-gateway
```

---

## 📊 데이터 모델

### ScaleWeightLog

출하/회수 확정 시점의 저울 데이터를 기록:

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | BigAutoField | 기본 키 |
| `scale_id` | CharField | 저울 식별자 (기본값: "default") |
| `cylinder_no` | CharField | 용기번호 (인덱스) |
| `event_type` | CharField | SHIP \| RETURN |
| `gross_kg` | Decimal(10,2) | 보호캡 제외 총무게 (kg) |
| `raw_line` | TextField | 원본 라인 ("ST , +000053.26 _kg") |
| `received_at` | DateTimeField | 리스너 수신 시각 |
| `committed_at` | DateTimeField | 확정 시각 (자동) |
| `arrival_shipping_no` | CharField | 입출고번호 (선택, TR_ORDERS 연결용) |
| `move_report_no` | CharField | 이동보고서번호 (선택) |

---

## 🧪 테스트 시나리오

### 1. 리스너 시작

```bash
python manage.py scale_gateway_listener
```

### 2. 저울 데이터 전송 (시뮬레이션)

```bash
echo "ST , +000053.26 _kg" | nc localhost 4001
```

### 3. 최신값 조회

```bash
curl http://localhost:8000/api/scale-gateway/latest/
```

예상 응답:

```json
{
  "ok": true,
  "status": "ST",
  "weight": 53.26,
  ...
}
```

### 4. 출하 확정

```bash
curl -X POST http://localhost:8000/api/scale-gateway/commit/ \
  -H "Content-Type: application/json" \
  -d '{"cylinder_no": "CY001", "event_type": "SHIP"}'
```

예상 응답:

```json
{
  "ok": true,
  "id": 1,
  "cylinder_no": "CY001",
  "event_type": "SHIP",
  "gross_kg": 53.26,
  ...
}
```

### 5. DB 확인

```bash
python manage.py shell

>>> from devices.models import ScaleWeightLog
>>> ScaleWeightLog.objects.all()
<QuerySet [<ScaleWeightLog: CY001 - 출하 - 53.26kg>]>
```

---

## 📝 로그

리스너와 API는 Django 로깅을 사용합니다:

```python
# settings.py에 추가 권장
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'devices': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}
```

로그 예시:

```
[Scale Gateway] 리스너 시작: 0.0.0.0:4001
[Scale Gateway] 포트 4001에서 연결 대기 중...
[Scale Gateway] 연결 수락: ('127.0.0.1', 54321)
[Scale Gateway] ST 업데이트: 53.26 kg
[Scale Gateway API] 커밋 완료: ID=1, 용기=CY001, 이벤트=SHIP, 무게=53.26kg
```

---

## 🔐 보안 권장사항

**현재 상태 (POC)**:
- API 인증 없음 (`@csrf_exempt`)
- 내부망 전용 사용 가정

**프로덕션 권장사항**:
1. API 인증 추가 (Token, Session, IP 화이트리스트)
2. HTTPS 사용
3. CSRF 보호 활성화
4. Rate Limiting 적용

---

## 🐛 트러블슈팅

### 1. 포트가 이미 사용 중

```bash
# 포트 사용 확인
netstat -ano | findstr :4001  # Windows
lsof -i :4001                  # Linux/Mac

# 프로세스 종료 후 재시작
```

### 2. 연결은 되지만 데이터가 없음

- 저울이 ST 상태를 전송하는지 확인
- US/OL 상태는 캐시에 저장되지 않음

### 3. 마이그레이션 오류

```bash
python manage.py makemigrations devices --skip-checks
python manage.py migrate devices --skip-checks
```

---

## 📚 참고

- **저울 모델**: FG-150KAL
- **프로토콜**: TCP (라인 단위, CRLF 종료)
- **포맷**: `<상태> , <부호><숫자> _kg`
- **상태 코드**:
  - `ST`: Stable (안정) - 캐시 저장
  - `US`: Unstable (불안정) - 무시
  - `OL`: Overload (과부하) - 경고 로그

---

## 📞 문의

프로젝트 담당자에게 문의하세요.

---

**Scale Gateway API v1.0**  
CYNOW 프로젝트 - 2025


