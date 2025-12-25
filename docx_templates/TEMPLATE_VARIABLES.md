# DOCX 템플릿 변수 목록

이 문서는 `offer_template.docx` 템플릿에서 사용하는 변수를 정리합니다.
템플릿 파일에서 `{{ 변수명 }}` 형태로 사용합니다.

---

## 1. 공급처 정보 (Supplier)

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `{{ supplier_name }}` | 공급처명 | CYNOW Co., Ltd. |
| `{{ supplier_address }}` | 주소 | 서울시 강남구... |
| `{{ supplier_ceo }}` | 대표자 | 홍길동 |
| `{{ supplier_tel }}` | TEL | 02-1234-5678 |
| `{{ supplier_fax }}` | FAX | 02-1234-5679 |
| `{{ supplier_manager }}` | 담당자명 | 김담당 |
| `{{ supplier_manager_tel }}` | 담당자 연락처 | 010-1234-5678 |
| `{{ supplier_manager_email }}` | 담당자 이메일 | manager@cynow.com |

---

## 2. 수신처 정보 (Customer)

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `{{ customer_name }}` | 수신처명 | KDKK |
| `{{ customer_address }}` | 주소 | 일본 도쿄... |
| `{{ customer_ceo }}` | 대표자 | 田中太郎 |
| `{{ customer_tel }}` | 연락처 | +81-3-1234-5678 |
| `{{ customer_manager }}` | 담당자명 | 山田花子 |
| `{{ customer_manager_tel }}` | 담당자 연락처 | +81-90-1234-5678 |
| `{{ customer_manager_email }}` | 담당자 이메일 | yamada@kdkk.jp |

---

## 3. 견적 기본 정보

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `{{ quote_date }}` | 견적일자 | 2025-12-25 |
| `{{ quote_no }}` | 견적번호 | QT-2026-0001 |
| `{{ quote_title }}` | 견적건명 | 2026년 특수가스 납품 단가 |

---

## 4. 상세 품목 테이블 (반복)

테이블에서 행을 반복하려면 다음과 같이 작성합니다:

```
{% for item in items %}
{{ item.no }} | {{ item.category }} | {{ item.gas_name }} | ...
{% endfor %}
```

### 품목별 변수

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `{{ item.no }}` | 순번 | 1 |
| `{{ item.category }}` | 구분 | 특수가스 |
| `{{ item.gas_name }}` | 가스명 | COS 5N |
| `{{ item.product_name }}` | 품명 | COS 5N 25kg CGA330 |
| `{{ item.material_code }}` | 자재코드 | KF013 |
| `{{ item.end_user }}` | End User | SDC |
| `{{ item.packing }}` | 포장 | 47L |
| `{{ item.filling_weight }}` | 충전중량 | 25kg |
| `{{ item.currency }}` | 통화 코드 | KRW |
| `{{ item.currency_symbol }}` | 통화 기호 | ₩ |
| `{{ item.price_per_kg }}` | 단가(1kg) | 328,350.00 |
| `{{ item.packing_price }}` | 포장단가 | 8,208,750 |

### 품목 수

| 변수명 | 설명 |
|--------|------|
| `{{ item_count }}` | 전체 품목 수 |

---

## 5. 하단 공통 문구

| 변수명 | 설명 | 예시 |
|--------|------|------|
| `{{ valid_period }}` | 적용기간 | 2026.01.01 ~ 2026.12.31 |
| `{{ trade_terms }}` | 거래조건 | FOB 인천 |
| `{{ bank_account }}` | 결제계좌 | 국민은행 123-456-789 |
| `{{ document_date }}` | 문서 작성일자 | 2025-12-25 |

---

## 6. 템플릿 제작 방법

### Step 1: Word에서 기존 문서 열기
기존 `2025년단가적용견적서.docx` 파일을 엽니다.

### Step 2: 변수로 치환
변경될 텍스트를 위 변수명으로 교체합니다.

예시:
- `CYNOW Co., Ltd.` → `{{ supplier_name }}`
- `2025-01-01` → `{{ quote_date }}`

### Step 3: 테이블 행 반복 설정
품목 테이블의 데이터 행(첫 번째 데이터 행)에서:

1. 행의 첫 번째 셀 앞에 `{%tr for item in items %}` 추가
2. 행의 마지막 셀 뒤에 `{%tr endfor %}` 추가
3. 각 셀의 값을 `{{ item.xxx }}` 변수로 교체

**주의:** `{%tr` 은 테이블 행(row) 단위 반복을 의미합니다.

### Step 4: 저장
`docx_templates/offer_template.docx`로 저장합니다.

---

## 7. 사용 예시 코드

```python
from voucher.services import QuoteDocxGenerator

# 생성기 초기화
generator = QuoteDocxGenerator('offer_template.docx')

# 데이터 준비
quote_info = {
    'date': '2025-12-25',
    'no': 'QT-2026-0001',
    'title': '2026년 특수가스 납품 단가',
}

supplier_info = {
    'name': 'CYNOW Co., Ltd.',
    'address': '서울시 강남구...',
    # ...
}

customer_info = {
    'name': 'KDKK',
    'address': '일본 도쿄...',
    # ...
}

items = [
    {
        'category': '특수가스',
        'gas_name': 'COS 5N',
        'material_code': 'KF013',
        'filling_weight': '25kg',
        'currency': 'KRW',
        'price_per_kg': 328350,
        'packing_price': 8208750,
    },
    # ... 더 많은 품목
]

footer_info = {
    'valid_period': '2026.01.01 ~ 2026.12.31',
    'trade_terms': 'FOB 인천',
    'bank_account': '국민은행 123-456-789',
}

# DOCX 생성
output_path = generator.generate_quote(
    quote_info=quote_info,
    supplier_info=supplier_info,
    customer_info=customer_info,
    items=items,
    footer_info=footer_info,
)

print(f"생성 완료: {output_path}")
```

---

## 8. 주의사항

1. **변수명 정확히 입력**: 오타 있으면 치환되지 않음
2. **중괄호 형식**: `{{ }}` (공백 포함)
3. **테이블 반복**: `{%tr %}` 형식 사용 (행 단위)
4. **이미지**: 로고 등은 템플릿에 미리 삽입
5. **인코딩**: UTF-8 유지

