# Kafka → PostgreSQL Sink Connector 빠른 해결 가이드

## 문제: Sink Connector Task가 계속 죽어버림

### 빠른 진단

```bash
# 1. Sink Connector 상태 확인
python manage.py check_kafka_sink

# 또는 직접 확인
curl -s http://localhost:8083/connectors/postgresql-sink-fcms/status | jq
```

### 가장 흔한 원인과 해결

#### 1. 스키마 진화 실패 (가장 흔함) ⚠️

**증상**: 
```
Cannot ALTER table 'fcms.xxx' because field 'XXX' is not optional but has no default value
```

**원인**: Debezium JDBC Sink Connector가 스키마 변경을 자동 적용하려 할 때, NOT NULL이고 기본값이 없는 새 필드 때문에 실패

**빠른 해결**:
```bash
# 실패한 커넥터 확인
curl -s http://localhost:8083/connectors | jq -r '.[]' | while read c; do
  STATE=$(curl -s http://localhost:8083/connectors/$c/status | jq -r '.tasks[0].state')
  if [ "$STATE" = "FAILED" ]; then
    echo "Failed: $c"
    # auto.evolve 비활성화
    curl -X PUT http://localhost:8083/connectors/$c/config \
      -H "Content-Type: application/json" \
      -d "$(curl -s http://localhost:8083/connectors/$c/config | jq '. + {"auto.evolve": "false"}')"
    # Task 재시작
    curl -X POST http://localhost:8083/connectors/$c/tasks/0/restart
  fi
done
```

**또는 개별 수정**:
```bash
# 예시: sink_dev_ma_cylinders
curl -X PUT http://localhost:8083/connectors/sink_dev_ma_cylinders/config \
  -H "Content-Type: application/json" \
  -d '{"auto.evolve": "false"}'
curl -X POST http://localhost:8083/connectors/sink_dev_ma_cylinders/tasks/0/restart
```

#### 2. 스키마 불일치

**증상**: Task가 시작되자마자 죽거나, 스키마 관련 오류 메시지

**해결**:
```bash
curl -X PUT http://localhost:8083/connectors/postgresql-sink-fcms/config \
  -H "Content-Type: application/json" \
  -d '{
    "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
    "connection.url": "jdbc:postgresql://10.78.30.98:5434/cynow",
    "connection.user": "postgres",
    "connection.password": "postgres",
    "topics": "fcms.FCMS.MA_CYLINDERS,fcms.FCMS.MA_CYLINDER_SPECS,fcms.FCMS.MA_VALVE_SPECS,fcms.FCMS.TR_LATEST_CYLINDER_STATUSES,fcms.FCMS.MA_ITEMS,fcms.FCMS.MA_PARAMETERS,fcms.FCMS.TR_CYLINDER_STATUS_HISTORIES",
    "auto.create": "true",
    "auto.evolve": "true",
    "insert.mode": "upsert",
    "pk.mode": "record_value",
    "pk.fields": "CYLINDER_NO",
    "table.name.format": "${topic}",
    "transforms": "unwrap,route",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.drop.tombstones": "false",
    "transforms.unwrap.delete.handling.mode": "rewrite",
    "transforms.route.type": "org.apache.kafka.connect.transforms.RegexRouter",
    "transforms.route.regex": "fcms\\.FCMS\\.(.*)",
    "transforms.route.replacement": "$1",
    "errors.tolerance": "all",
    "errors.log.enable": "true"
  }'
```

#### 3. 연결 타임아웃

**증상**: 연결 관련 오류 메시지

**해결**: 연결 URL에 타임아웃 추가
```json
"connection.url": "jdbc:postgresql://10.78.30.98:5434/cynow?connectTimeout=30&socketTimeout=60",
"connection.attempts": "3",
"connection.backoff.ms": "10000"
```

#### 4. 메모리 부족

**증상**: OOM 오류 또는 메모리 관련 오류

**해결**: 배치 크기 줄이기
```json
"batch.size": "100",
"max.retries": "10",
"retry.backoff.ms": "3000"
```

### 자동 재시작

```bash
# 커넥터 재시작
curl -X POST http://localhost:8083/connectors/postgresql-sink-fcms/restart

# 특정 Task 재시작
curl -X POST http://localhost:8083/connectors/postgresql-sink-fcms/tasks/0/restart

# 자동 진단 및 재시작 시도
python manage.py check_kafka_sink --fix
```

### 상세 가이드

더 자세한 문제 해결 방법은 `docs/postgresql_sink_troubleshooting.md`를 참조하세요.



