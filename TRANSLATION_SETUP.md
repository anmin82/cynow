# 일본어 → 한국어 번역 시스템 설정 가이드

## 빠른 시작

### 1. 마이그레이션 실행

```bash
python manage.py migrate core
```

### 2. 초기 번역 데이터 로드

데이터베이스에서 일본어 데이터를 추출하여 번역 테이블에 로드:

```bash
python manage.py load_translations
```

이 명령어는 다음을 수행합니다:
- `vw_cynow_inventory`와 `vw_cynow_cylinder_list` VIEW에서 고유한 일본어 값 추출
- 각 필드 타입별로 번역 엔트리 생성 (기본값은 원문)
- 이미 존재하는 번역은 건너뜀

### 3. 번역 수정

Django 관리자 페이지에서 번역을 수정:

1. `/admin/` 접속
2. `Core` → `번역` 메뉴
3. 목록에서 일본어 원문을 찾아 한국어 번역 입력
4. `활성화` 체크박스가 체크되어 있는지 확인
5. 저장

### 4. 확인

웹 페이지를 새로고침하면 번역이 적용된 것을 확인할 수 있습니다.

## 번역이 적용되는 곳

다음 화면에서 자동으로 번역이 적용됩니다:

- **대시보드** (`/`): 가스명, 밸브 스펙, 용기 스펙, 사용처
- **현황 상세** (`/detail/`): 모든 필드
- **용기 리스트** (`/cylinders/`): 모든 필드
- **알림** (`/alerts/`): 가스명, 밸브 스펙, 용기 스펙
- **보고서** (`/reports/`): 모든 필드

## 번역 관리 팁

### 일괄 수정

1. 관리자 페이지에서 여러 번역 선택
2. "선택한 번역 활성화" 또는 "선택한 번역 비활성화" 실행

### 특정 필드만 로드

```bash
# 가스명만 로드
python manage.py load_translations --field-type gas_name

# 위치만 로드
python manage.py load_translations --field-type location
```

### 미리보기

실제로 저장하지 않고 어떤 번역이 생성될지 확인:

```bash
python manage.py load_translations --dry-run
```

## 문제 해결

### 번역이 표시되지 않는 경우

1. 마이그레이션이 실행되었는지 확인: `python manage.py migrate`
2. 번역 데이터가 로드되었는지 확인: `python manage.py load_translations`
3. 관리자 페이지에서 해당 번역의 `활성화`가 체크되어 있는지 확인
4. 일본어 텍스트가 정확히 일치하는지 확인 (공백, 특수문자 포함)

### 새로운 데이터가 추가된 경우

새로운 일본어 데이터가 데이터베이스에 추가되면:

```bash
python manage.py load_translations
```

이 명령어를 다시 실행하면 새로운 일본어 텍스트만 추가되고, 기존 번역은 유지됩니다.

## 상세 가이드

더 자세한 내용은 [docs/TRANSLATION_GUIDE.md](docs/TRANSLATION_GUIDE.md)를 참고하세요.
