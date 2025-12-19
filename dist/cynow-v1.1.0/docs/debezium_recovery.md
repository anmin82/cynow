# Debezium 커넥터 복구 가이드

## 현재 문제

```
The db history topic is missing. You may attempt to recover it by reconfiguring the connector to recovery.
```

## 해결 방법

### 방법 1: Recovery 모드로 커넥터 재설정 (권장)

```bash
# 커넥터 설정 가져오기
curl -s http://localhost:8083/connectors/oracle-fcms-cylcy-min/config > connector-config.json

# snapshot.mode를 recovery로 변경
# snapshot.mode: "recovery"로 수정

# 커넥터 재설정
curl -X PUT http://localhost:8083/connectors/oracle-fcms-cylcy-min/config \
  -H "Content-Type: application/json" \
  -d @connector-config.json

# 또는 직접 수정
curl -X PUT http://localhost:8083/connectors/oracle-fcms-cylcy-min/config \
  -H "Content-Type: application/json" \
  -d '{
    "connector.class": "io.debezium.connector.oracle.OracleConnector",
    "database.user": "FCMS",
    "database.dbname": "FCMSDB",
    "tasks.max": "1",
    "database.connection.adapter": "logminer",
    "log.mining.dictionary": "online_catalog",
    "schema.history.internal.kafka.bootstrap.servers": "kafka:29092",
    "database.port": "1521",
    "include.schema.changes": "false",
    "topic.prefix": "fcms",
    "schema.history.internal.kafka.topic": "dbhistory.fcms.cylcy.min",
    "database.hostname": "10.78.30.18",
    "log.mining.continuous.mine": "true",
    "database.password": "FCMS",
    "name": "oracle-fcms-cylcy-min",
    "table.include.list": "FCMS.MA_ITEMS,FCMS.MA_CYLINDERS,FCMS.MA_CYLINDER_SPECS,FCMS.MA_VALVE_SPECS,FCMS.MA_PARAMETERS,FCMS.TR_LATEST_CYLINDER_STATUSES,FCMS.TR_CYLINDER_STATUS_HISTORIES",
    "snapshot.mode": "recovery"
  }'
```

### 방법 2: 커넥터 재시작 (initial snapshot)

```bash
# 커넥터 삭제
curl -X DELETE http://localhost:8083/connectors/oracle-fcms-cylcy-min

# schema history topic 삭제 (필요한 경우)
# kafka-topics.sh --delete --topic dbhistory.fcms.cylcy.min --bootstrap-server localhost:9092

# 커넥터 재생성 (snapshot.mode: "initial")
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d '{
    "name": "oracle-fcms-cylcy-min",
    "config": {
      "connector.class": "io.debezium.connector.oracle.OracleConnector",
      "database.user": "FCMS",
      "database.dbname": "FCMSDB",
      "tasks.max": "1",
      "database.connection.adapter": "logminer",
      "log.mining.dictionary": "online_catalog",
      "schema.history.internal.kafka.bootstrap.servers": "kafka:29092",
      "database.port": "1521",
      "include.schema.changes": "false",
      "topic.prefix": "fcms",
      "schema.history.internal.kafka.topic": "dbhistory.fcms.cylcy.min",
      "database.hostname": "10.78.30.18",
      "log.mining.continuous.mine": "true",
      "database.password": "FCMS",
      "table.include.list": "FCMS.MA_ITEMS,FCMS.MA_CYLINDERS,FCMS.MA_CYLINDER_SPECS,FCMS.MA_VALVE_SPECS,FCMS.MA_PARAMETERS,FCMS.TR_LATEST_CYLINDER_STATUSES,FCMS.TR_CYLINDER_STATUS_HISTORIES",
      "snapshot.mode": "initial"
    }
  }'
```

## 동기화되는 테이블 목록

원본 Oracle 테이블:
- `FCMS.MA_ITEMS`
- `FCMS.MA_CYLINDERS` ⭐ (핵심 - 용기 마스터)
- `FCMS.MA_CYLINDER_SPECS` ⭐ (용기 스펙)
- `FCMS.MA_VALVE_SPECS` ⭐ (밸브 스펙)
- `FCMS.MA_PARAMETERS`
- `FCMS.TR_LATEST_CYLINDER_STATUSES` ⭐ (최신 상태)
- `FCMS.TR_CYLINDER_STATUS_HISTORIES`

## PostgreSQL에서 테이블명 확인

Debezium은 일반적으로 다음과 같은 패턴으로 테이블명을 생성합니다:
- `topic.prefix.schema.table` 형식
- 예: `fcms.FCMS.MA_CYLINDERS`

JDBC Sink Connector가 있다면 설정된 테이블명을 확인해야 합니다.

## 커넥터 상태 확인

```bash
# 커넥터 상태 확인
curl -s http://localhost:8083/connectors/oracle-fcms-cylcy-min/status | jq

# 커넥터 재시작
curl -X POST http://localhost:8083/connectors/oracle-fcms-cylcy-min/restart

# 특정 태스크 재시작
curl -X POST http://localhost:8083/connectors/oracle-fcms-cylcy-min/tasks/0/restart
```




