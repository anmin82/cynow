# CDC DELETE 이벤트 처리 문제 해결 가이드

## 문제 상황
오라클에서 용기를 삭제했는데, 카프카로 DELETE 이벤트가 전달되지 않거나, PostgreSQL의 CDC 테이블에서 삭제가 반영되지 않는 경우

## 원인 분석

### 1. Debezium Source Connector
- Debezium은 기본적으로 DELETE 이벤트를 캡처합니다
- 하지만 Oracle LogMiner 설정에 따라 DELETE 이벤트가 로그에 기록되지 않을 수 있습니다

### 2. JDBC Sink Connector
- JDBC Sink Connector는 기본적으로 DELETE 이벤트를 처리하지 않을 수 있습니다
- `delete.enabled=true` 설정이 필요합니다

## 해결 방법

### 1. JDBC Sink Connector 설정 확인 및 수정

JDBC Sink Connector 설정에 다음 옵션을 추가해야 합니다:

```json
{
  "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
  "connection.url": "jdbc:postgresql://10.78.30.98:5434/cycy_db",
  "connection.user": "cycy_user",
  "connection.password": "cycy_password",
  "topics": "fcms.FCMS.MA_CYLINDERS",
  "table.name.format": "fcms_cdc.ma_cylinders",
  "insert.mode": "upsert",
  "pk.mode": "record_value",
  "pk.fields": "CYLINDER_NO",
  "delete.enabled": "true",  // ⭐ DELETE 이벤트 처리 활성화
  "delete.mode": "delete",   // DELETE 모드 설정
  "auto.create": "false",
  "auto.evolve": "false"
}
```

### 2. Debezium Source Connector 확인

Debezium Source Connector가 DELETE 이벤트를 캡처하는지 확인:

```bash
# Kafka 토픽에서 DELETE 이벤트 확인
kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic fcms.FCMS.MA_CYLINDERS \
  --from-beginning \
  --property print.key=true \
  --property print.value=true
```

DELETE 이벤트는 다음과 같은 형태로 나타납니다:
```json
{
  "before": {
    "CYLINDER_NO": "ABC123",
    ...
  },
  "after": null,
  "op": "d"  // 'd' = delete
}
```

### 3. JDBC Sink Connector 재시작

설정 변경 후 커넥터를 재시작:

```bash
# 커넥터 설정 업데이트
curl -X PUT http://localhost:8083/connectors/jdbc-sink-fcms-cylinders/config \
  -H "Content-Type: application/json" \
  -d @jdbc-sink-config.json

# 커넥터 재시작
curl -X POST http://localhost:8083/connectors/jdbc-sink-fcms-cylinders/restart

# 상태 확인
curl -s http://localhost:8083/connectors/jdbc-sink-fcms-cylinders/status | jq
```

### 4. PostgreSQL 트리거 확인

PostgreSQL의 `cy_cylinder_current` 테이블에 DELETE 트리거가 설정되어 있는지 확인:

```sql
-- 트리거 확인
SELECT 
    trigger_name, 
    event_manipulation, 
    event_object_table
FROM information_schema.triggers
WHERE event_object_table = 'ma_cylinders'
  AND event_object_schema = 'fcms_cdc';

-- 트리거 재생성 (필요한 경우)
\i sql/create_sync_triggers.sql
```

### 5. 수동 삭제 처리 (임시 해결책)

JDBC Sink Connector가 DELETE를 처리하지 않는 경우, PostgreSQL에서 수동으로 삭제:

```sql
-- fcms_cdc.ma_cylinders에서 삭제된 용기 확인
-- (cy_cylinder_current에는 있지만 fcms_cdc.ma_cylinders에는 없는 용기)
SELECT c.cylinder_no
FROM cy_cylinder_current c
LEFT JOIN "fcms_cdc"."ma_cylinders" mc ON TRIM(c.cylinder_no) = TRIM(mc."CYLINDER_NO")
WHERE mc."CYLINDER_NO" IS NULL;

-- 삭제 실행
DELETE FROM cy_cylinder_current
WHERE cylinder_no IN (
    SELECT c.cylinder_no
    FROM cy_cylinder_current c
    LEFT JOIN "fcms_cdc"."ma_cylinders" mc ON TRIM(c.cylinder_no) = TRIM(mc."CYLINDER_NO")
    WHERE mc."CYLINDER_NO" IS NULL
);
```

## 확인 방법

### 1. Kafka 토픽에서 DELETE 이벤트 확인
```bash
kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic fcms.FCMS.MA_CYLINDERS \
  --from-beginning \
  --max-messages 100 \
  | grep '"op":"d"'
```

### 2. PostgreSQL CDC 테이블 확인
```sql
-- 최근 삭제된 용기 확인 (없어야 함)
SELECT COUNT(*) 
FROM "fcms_cdc"."ma_cylinders" 
WHERE "CYLINDER_NO" = '삭제한_용기번호';

-- cy_cylinder_current에서도 확인
SELECT COUNT(*) 
FROM cy_cylinder_current 
WHERE cylinder_no = '삭제한_용기번호';
```

### 3. 트리거 동작 확인
```sql
-- 트리거 함수 테스트
SELECT delete_cylinder_current('테스트_용기번호');
```

## 예상되는 JDBC Sink Connector 설정 파일

`jdbc-sink-fcms-cylinders-config.json`:
```json
{
  "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
  "connection.url": "jdbc:postgresql://10.78.30.98:5434/cycy_db",
  "connection.user": "cycy_user",
  "connection.password": "cycy_password",
  "topics": "fcms.FCMS.MA_CYLINDERS",
  "table.name.format": "fcms_cdc.ma_cylinders",
  "insert.mode": "upsert",
  "pk.mode": "record_value",
  "pk.fields": "CYLINDER_NO",
  "delete.enabled": "true",
  "delete.mode": "delete",
  "auto.create": "false",
  "auto.evolve": "false",
  "transforms": "unwrap",
  "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
  "transforms.unwrap.drop.tombstones": "false",
  "transforms.unwrap.delete.handling.mode": "rewrite"
}
```

## 참고사항

1. **Debezium Transform**: `ExtractNewRecordState` transform을 사용하는 경우, `delete.handling.mode`를 `rewrite`로 설정해야 DELETE 이벤트가 올바르게 처리됩니다.

2. **Tombstone 메시지**: Debezium은 DELETE 이벤트 후 tombstone 메시지(null value)를 보냅니다. JDBC Sink Connector가 이를 올바르게 처리하도록 설정해야 합니다.

3. **용기번호 공백 처리**: 용기번호에 공백이 있는 경우, TRIM 처리가 필요합니다. 트리거 함수에서 이미 처리하고 있습니다.










