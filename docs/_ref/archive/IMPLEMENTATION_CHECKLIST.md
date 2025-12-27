# CYNOW 데이터 아키텍처 재설계 구현 체크리스트

## 완료된 작업 ✅

1. ✅ DDL 설계 완료 (`sql/create_cynow_tables.sql`)
2. ✅ Django 모델 생성 (`core/models.py`)
3. ✅ Admin 페이지 등록 (`core/admin.py`)
4. ✅ 스냅샷 갱신 명령어 (`core/management/commands/sync_cylinder_snapshot.py`)
5. ✅ Repository 레이어 (`core/repositories/cylinder_repository.py`)
6. ✅ 문서화 완료

## 다음 단계

### 1. 마이그레이션 실행
```bash
python manage.py makemigrations core
python manage.py migrate core
```

### 2. 정책 데이터 입력
```sql
-- 기본 EndUser 정책
INSERT INTO cy_enduser_policy (default_enduser_code, default_enduser_name, is_active, notes)
VALUES ('SDC', 'SDC', TRUE, '기본 EndUser');

-- CF4 YC 440L LGD 전용 예외 규칙 (실제 키 값으로 수정 필요)
-- 먼저 실제 cylinder_type_key를 확인한 후 입력
```

### 3. 초기 스냅샷 생성
```bash
python manage.py sync_cylinder_snapshot --full
```

### 4. 점진적 전환
- `settings.py`에 `USE_SNAPSHOT_TABLE` 플래그 추가
- `ViewRepository`에서 조건부 분기
- 테스트 후 전환

### 5. 정기 갱신 설정
```bash
# Cron 설정 (5분마다)
*/5 * * * * cd /path/to/cynow && python manage.py sync_cylinder_snapshot
```

## 검증 항목

- [ ] 스냅샷 테이블 데이터 개수 = VIEW 데이터 개수
- [ ] EndUser 정책 적용 확인 (CF4 LGD 29병 분리)
- [ ] 밸브 표준화 확인 (NERIKI/HAMAI 통합)
- [ ] 성능 비교 (VIEW vs 스냅샷)
- [ ] 정책 변경 후 재계산 확인

