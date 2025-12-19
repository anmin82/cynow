# 스냅샷 테이블 구조 빠른 시작 가이드

## 1. 테이블 생성

```bash
# 정책 테이블 생성
psql -h 10.78.30.98 -p 5434 -U postgres -d cycy_db -f sql/create_cynow_policy_tables.sql

# 스냅샷 테이블 생성
psql -h 10.78.30.98 -p 5434 -U postgres -d cycy_db -f sql/create_cy_cylinder_current.sql
```

## 2. 초기 데이터 입력

```bash
# EndUser 기본값 설정
python manage.py load_enduser_defaults

# 밸브 그룹 설정
python manage.py load_valve_groups
```

## 3. 초기 스냅샷 생성

```bash
# 전체 용기 스냅샷 생성
python manage.py sync_cylinder_current
```

## 4. 자동 동기화 설정 (선택)

```bash
# Trigger 설정 (CDC 이벤트 기반 자동 갱신)
psql -h 10.78.30.98 -p 5434 -U postgres -d cycy_db -f sql/create_sync_triggers.sql
```

## 5. 검증

```bash
# 스냅샷 검증
python manage.py verify_cylinder_current
```

## 6. Repository 전환

```python
# dashboard/views.py
# 기존: ViewRepository.get_inventory_view()
# 변경: CylinderRepository.get_inventory_summary()

# cylinders/views.py  
# 기존: ViewRepository.get_cylinder_list_view()
# 변경: CylinderRepository.get_cylinder_list()
```

## 주요 차이점

### 기존 (VIEW 기반)
- 매번 조인 쿼리 실행
- 정책 적용을 Python에서 처리
- 성능 저하

### 신규 (스냅샷 테이블)
- 인덱스 최적화된 테이블 직접 조회
- 정책이 이미 적용된 값 사용
- 빠른 조회 성능

