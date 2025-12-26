# Scale Gateway API - 테스트 가이드

**빠른 시작 및 테스트 명령어**

---

## 🚀 빠른 시작

### 1. 마이그레이션 확인

```bash
cd c:\cynow
python manage.py migrate devices --skip-checks
```

출력 예상:
```
Operations to perform:
  Apply all migrations: devices
Running migrations:
  Applying devices.0001_initial... OK
```

---

### 2. 리스너 실행

**터미널 1 (리스너)**:

```bash
cd c:\cynow
python manage.py scale_gateway_listener
```

출력 예상:
```
[Scale Gateway] 리스너 시작 중...
  - 주소: 0.0.0.0:4001
  - 저울 ID: default
[Scale Gateway] 리스너 시작: 0.0.0.0:4001
[Scale Gateway] 포트 4001에서 연결 대기 중...
```

---

### 3. 저울 시뮬레이터 (Windows PowerShell)

**터미널 2 (시뮬레이터)**:

```powershell
# TCP 클라이언트로 데이터 전송
$client = New-Object System.Net.Sockets.TcpClient
$client.Connect("localhost", 4001)
$stream = $client.GetStream()
$writer = New-Object System.IO.StreamWriter($stream)

# ST (안정) 데이터 전송
$writer.WriteLine("ST , +000053.26 _kg")
$writer.Flush()

# 다른 무게 전송
$writer.WriteLine("ST , +000075.50 _kg")
$writer.Flush()

# 종료
$writer.Close()
$client.Close()
```

또는 Python 스크립트로:

```python
# test_scale_simulator.py
import socket
import time

def send_scale_data(host='localhost', port=4001):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((host, port))
    
    # 여러 상태 전송
    data = [
        "US , +000050.12 _kg\r\n",  # 불안정 (무시됨)
        "ST , +000053.26 _kg\r\n",  # 안정 (캐시 저장)
        "ST , +000053.25 _kg\r\n",  # 안정 (업데이트)
        "ST , +000053.27 _kg\r\n",  # 안정 (업데이트)
    ]
    
    for line in data:
        print(f"전송: {line.strip()}")
        client.sendall(line.encode('utf-8'))
        time.sleep(0.5)
    
    client.close()
    print("연결 종료")

if __name__ == '__main__':
    send_scale_data()
```

실행:
```bash
python test_scale_simulator.py
```

---

### 4. API 테스트

**터미널 3 (API 서버)**:

Django 개발 서버가 실행 중이어야 합니다:

```bash
cd c:\cynow
python manage.py runserver
```

**터미널 4 (API 호출)**:

#### 4-1. 최신값 조회

**PowerShell**:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/scale-gateway/latest/" -Method Get
```

**curl (Git Bash 또는 WSL)**:
```bash
curl http://localhost:8000/api/scale-gateway/latest/
```

예상 응답:
```json
{
  "ok": true,
  "scale_id": "default",
  "status": "ST",
  "weight": 53.27,
  "raw": "ST , +000053.27 _kg",
  "received_at": "2025-12-18T11:50:12+09:00",
  "stale": false
}
```

---

#### 4-2. 출하 확정 (커밋)

**PowerShell**:
```powershell
$body = @{
    cylinder_no = "CY123456789"
    event_type = "SHIP"
    arrival_shipping_no = "AS20251218-0001"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/scale-gateway/commit/" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
```

**curl**:
```bash
curl -X POST http://localhost:8000/api/scale-gateway/commit/ \
  -H "Content-Type: application/json" \
  -d '{
    "cylinder_no": "CY123456789",
    "event_type": "SHIP",
    "arrival_shipping_no": "AS20251218-0001"
  }'
```

예상 응답:
```json
{
  "ok": true,
  "id": 1,
  "cylinder_no": "CY123456789",
  "event_type": "SHIP",
  "gross_kg": 53.27,
  "committed_at": "2025-12-18T11:52:30+09:00"
}
```

---

#### 4-3. 회수 확정

```powershell
$body = @{
    cylinder_no = "CY987654321"
    event_type = "RETURN"
    move_report_no = "MR20251218-0001"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/scale-gateway/commit/" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
```

---

### 5. DB 확인

Django shell로 데이터 확인:

```bash
cd c:\cynow
python manage.py shell
```

```python
from devices.models import ScaleWeightLog

# 전체 로그 조회
logs = ScaleWeightLog.objects.all()
for log in logs:
    print(f"{log.id}: {log.cylinder_no} - {log.event_type} - {log.gross_kg}kg")

# 최근 로그
latest = ScaleWeightLog.objects.first()
print(f"최근 로그: {latest}")
print(f"용기번호: {latest.cylinder_no}")
print(f"무게: {latest.gross_kg}kg")
print(f"원본: {latest.raw_line}")
print(f"확정시각: {latest.committed_at}")

# 특정 용기 로그
cy_logs = ScaleWeightLog.objects.filter(cylinder_no="CY123456789")
print(f"CY123456789 로그: {cy_logs.count()}개")

# 출하 로그만
ship_logs = ScaleWeightLog.objects.filter(event_type="SHIP")
print(f"출하 로그: {ship_logs.count()}개")
```

---

### 6. Admin 페이지 확인

1. 슈퍼유저 생성 (없으면):
```bash
python manage.py createsuperuser --skip-checks
```

2. 브라우저에서 접속:
```
http://localhost:8000/admin/
```

3. 로그인 후 "Devices" → "저울 무게 로그" 메뉴에서 확인

---

## 🧪 전체 시나리오 테스트

### 시나리오 1: 출하 프로세스

```bash
# 1. 리스너 실행 (터미널 1)
python manage.py scale_gateway_listener

# 2. Django 서버 실행 (터미널 2)
python manage.py runserver

# 3. 저울 데이터 전송 (터미널 3)
python test_scale_simulator.py

# 4. 최신값 조회 (터미널 4)
curl http://localhost:8000/api/scale-gateway/latest/

# 5. 출하 확정
curl -X POST http://localhost:8000/api/scale-gateway/commit/ \
  -H "Content-Type: application/json" \
  -d '{"cylinder_no": "CY001", "event_type": "SHIP"}'

# 6. DB 확인
python manage.py shell
>>> from devices.models import ScaleWeightLog
>>> ScaleWeightLog.objects.filter(cylinder_no="CY001")
```

---

### 시나리오 2: Stale 데이터 테스트

```bash
# 1. 저울 데이터 전송
echo "ST , +000053.26 _kg" | nc localhost 4001

# 2. 즉시 조회 (stale: false)
curl http://localhost:8000/api/scale-gateway/latest/

# 3. 10초 대기
sleep 10

# 4. 다시 조회 (stale: true)
curl http://localhost:8000/api/scale-gateway/latest/
```

---

### 시나리오 3: 안정값 없이 커밋 시도

```bash
# 1. 리스너 실행 중이지만 데이터 없음

# 2. 커밋 시도
curl -X POST http://localhost:8000/api/scale-gateway/commit/ \
  -H "Content-Type: application/json" \
  -d '{"cylinder_no": "CY001", "event_type": "SHIP"}'

# 예상 응답:
# {
#   "ok": false,
#   "error": "no_stable_weight",
#   "message": "안정된 저울 데이터(ST)가 없습니다"
# }
```

---

## 📊 모니터링

### 리스너 로그 확인

```bash
# 리스너 실행 시 출력 확인
python manage.py scale_gateway_listener

# 예상 로그:
# [Scale Gateway] 리스너 시작: 0.0.0.0:4001
# [Scale Gateway] 포트 4001에서 연결 대기 중...
# [Scale Gateway] 연결 수락: ('127.0.0.1', 54321)
# [Scale Gateway] ST 업데이트: 53.26 kg
```

### API 로그 확인

Django 서버 출력에서 확인:

```
[18/Dec/2025 11:52:30] "GET /api/scale-gateway/latest/ HTTP/1.1" 200 ...
[18/Dec/2025 11:52:35] "POST /api/scale-gateway/commit/ HTTP/1.1" 200 ...
[Scale Gateway API] 커밋 완료: ID=1, 용기=CY001, 이벤트=SHIP, 무게=53.26kg
```

---

## 🐛 문제 해결

### 문제 1: 포트 4001이 이미 사용 중

```bash
# Windows
netstat -ano | findstr :4001
taskkill /PID <PID> /F

# 또는 다른 포트로 실행
python manage.py scale_gateway_listener --port 4002
```

### 문제 2: 리스너가 데이터를 받지 못함

- 방화벽 확인
- 포트 번호 일치 확인
- 로컬호스트 연결 테스트: `telnet localhost 4001`

### 문제 3: API 404 오류

```bash
# URL 패턴 확인
python manage.py show_urls | grep scale

# 올바른 URL:
# /api/scale-gateway/latest/
# /api/scale-gateway/commit/
```

---

## ✅ 체크리스트

- [ ] 마이그레이션 적용 완료
- [ ] 리스너 실행 확인
- [ ] 저울 시뮬레이터로 데이터 전송
- [ ] 최신값 조회 API 성공
- [ ] 출하 확정 API 성공
- [ ] DB에 로그 저장 확인
- [ ] Admin 페이지에서 로그 확인

---

**모든 테스트가 성공하면 Scale Gateway API가 정상 작동합니다!** 🎉



















