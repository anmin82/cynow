# Debezium 커넥터 복구 방법

## 현재 문제

Debezium 커넥터가 다음 오류로 실패 중:
```
The db history topic is missing. You may attempt to recover it by reconfiguring the connector to recovery.
```

## 해결 방법

### 방법 1: Recovery 모드로 설정 변경 (빠른 복구)

```bash
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
    "table.include.list": "FCMS.MA_ITEMS,FCMS.MA_CYLINDERS,FCMS.MA_CYLINDER_SPECS,FCMS.MA_VALVE_SPECS,FCMS.MA_PARAMETERS,FCMS.TR_LATEST_CYLINDER_STATUSES,FCMS.TR_CYLINDER_STATUS_HISTORIES",
    "snapshot.mode": "recovery"
  }'
```

### 방법 2: 커넥터 재시작

```bash
# 커넥터 재시작
curl -X POST http://localhost:8083/connectors/oracle-fcms-cylcy-min/restart

# 상태 확인
curl -s http://localhost:8083/connectors/oracle-fcms-cylcy-min/status | jq
```

## 동기화되는 테이블

원본 Oracle 테이블:
- `FCMS.MA_CYLINDERS` ⭐ (핵심 - 용기 마스터)
- `FCMS.MA_CYLINDER_SPECS` ⭐ (용기 스펙)
- `FCMS.MA_VALVE_SPECS` ⭐ (밸브 스펙)
- `FCMS.TR_LATEST_CYLINDER_STATUSES` ⭐ (최신 상태)
- `FCMS.MA_ITEMS`
- `FCMS.MA_PARAMETERS`
- `FCMS.TR_CYLINDER_STATUS_HISTORIES`

## PostgreSQL에서 확인

커넥터가 정상 작동하면:

1. **동기화 테이블 확인**:
   ```bash
   python manage.py check_sync_tables
   ```

2. **모든 테이블 목록 확인**:
   ```bash
   python manage.py list_db_tables
   ```

## 테이블명 예상 패턴

Debezium은 일반적으로 다음과 같은 패턴으로 테이블명을 생성합니다:
- `fcms.FCMS.MA_CYLINDERS` (topic.prefix.schema.table)
- 또는 JDBC Sink Connector 설정에 따라 달라질 수 있음

## 다음 단계

1. Debezium 커넥터 복구 (위 방법 중 선택)
2. 커넥터 상태 확인 (`RUNNING` 상태가 될 때까지 대기)
3. PostgreSQL에서 동기화 테이블 확인
4. VIEW 생성:
   ```bash
   python manage.py create_postgresql_views
   ```













