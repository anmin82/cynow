# 일본어 → 한국어 번역 시스템 가이드

## 개요

CYNOW 시스템은 일본어로 저장된 데이터를 한국어로 자동 번역하여 표시하는 기능을 제공합니다.

## 주요 기능

1. **자동 번역**: 데이터베이스에서 조회한 일본어 데이터를 자동으로 한국어로 변환
2. **번역 관리**: Django 관리자 페이지에서 번역을 추가/수정/삭제 가능
3. **필드별 번역**: 가스명, 밸브 스펙, 용기 스펙, 사용처, 위치 등 필드별로 번역 관리

## 사용 방법

### 1. 초기 번역 데이터 로드

데이터베이스에서 일본어 데이터를 추출하여 번역 테이블에 로드합니다:

```bash
# 모든 필드 타입 로드
python manage.py load_translations

# 특정 필드 타입만 로드
python manage.py load_translations --field-type gas_name

# 미리보기만 (실제 저장 안 함)
python manage.py load_translations --dry-run
```

### 2. 번역 관리 (Django 관리자)

1. Django 관리자 페이지 접속: `/admin/`
2. `Core` → `번역` 메뉴로 이동
3. 번역 목록에서:
   - **일본어 원문**: 데이터베이스에 저장된 일본어 텍스트
   - **한국어 번역**: 화면에 표시될 한국어 텍스트
   - **활성화**: 이 번역을 사용할지 여부

4. 번역 추가/수정:
   - 목록에서 직접 수정 가능 (한국어 번역, 활성화 여부)
   - 새 번역 추가: "번역 추가" 버튼 클릭

5. 일괄 작업:
   - 여러 번역 선택 후 "선택한 번역 활성화" 또는 "선택한 번역 비활성화" 실행

### 3. 번역이 적용되는 필드

다음 필드들이 자동으로 번역됩니다:

- **가스명** (`gas_name`): 가스 이름
- **밸브 스펙** (`valve_spec`): 밸브 사양
- **용기 스펙** (`cylinder_spec`): 용기 사양
- **사용처** (`usage_place`): 사용 장소
- **위치** (`location`): 용기 위치

### 4. 템플릿에서 번역 필터 사용 (선택사항)

뷰에서 이미 번역이 적용되지만, 템플릿에서 직접 번역을 적용할 수도 있습니다:

```django
{# 일반 번역 필터 #}
{{ cylinder.gas_name|translate:"gas_name" }}
{{ cylinder.location|translate:"location" }}

{# 특정 필드용 필터 #}
{{ cylinder.gas_name|translate_gas_name }}
{{ cylinder.valve_spec|translate_valve_spec }}
{{ cylinder.cylinder_spec|translate_cylinder_spec }}
{{ cylinder.usage_place|translate_usage_place }}
{{ cylinder.location|translate_location }}
```

## 번역 우선순위

1. **번역 테이블에 등록된 번역** (활성화된 것만)
2. **번역이 없으면 원문 표시**

## 번역 데이터 구조

### Translation 모델

- `field_type`: 필드 타입 (gas_name, valve_spec, cylinder_spec, usage_place, location)
- `japanese_text`: 일본어 원문 (대소문자 구분 없음)
- `korean_text`: 한국어 번역
- `is_active`: 활성화 여부
- `notes`: 메모/참고사항
- `created_at`, `updated_at`: 생성/수정 일시

## 주의사항

1. **대소문자 구분 없음**: 일본어 원문은 대소문자를 구분하지 않고 매칭됩니다.
2. **정확한 매칭**: 공백 포함하여 정확히 일치하는 경우에만 번역이 적용됩니다.
3. **활성화된 번역만 사용**: `is_active=True`인 번역만 사용됩니다.
4. **원문 보존**: 번역은 표시용이며, 데이터베이스의 원본 데이터는 변경되지 않습니다.

## 문제 해결

### 번역이 적용되지 않는 경우

1. 번역 테이블에 해당 일본어 텍스트가 등록되어 있는지 확인
2. 번역의 `is_active`가 `True`인지 확인
3. 일본어 텍스트가 정확히 일치하는지 확인 (공백, 특수문자 등)

### 번역 수정 방법

1. Django 관리자 페이지에서 해당 번역 찾기
2. "한국어 번역" 필드를 수정
3. 저장

### 새로운 일본어 데이터가 추가된 경우

```bash
# 번역 데이터 다시 로드
python manage.py load_translations
```

이 명령어는 기존 번역은 유지하고, 새로운 일본어 텍스트만 추가합니다.

## 예시

### 번역 추가 예시

1. 데이터베이스에 `ガス名` (일본어)가 저장되어 있음
2. `load_translations` 명령어 실행 → 번역 테이블에 `ガス名` 추가됨
3. 관리자 페이지에서 `ガス名` → `가스명`으로 번역 입력
4. 화면에 `가스명`으로 표시됨

### 번역 수정 예시

1. 관리자 페이지에서 `ガス名` → `가스명` 번역 찾기
2. 한국어 번역을 `가스 이름`으로 변경
3. 저장
4. 화면에 `가스 이름`으로 표시됨
