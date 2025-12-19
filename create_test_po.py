"""
테스트용 수주 데이터 생성 스크립트
서버에서 실행: python manage.py shell < create_test_po.py
"""
from orders.models import PO, POItem
from datetime import date, datetime
from django.contrib.auth.models import User

# 테스트 수주 생성
print("=" * 80)
print("테스트 수주 생성 중...")
print("=" * 80)

# 생성자 (없으면 None으로)
try:
    creator = User.objects.filter(is_staff=True).first()
except:
    creator = None

# 수주 1: 일반 수주
po1 = PO.objects.create(
    po_no="TEST-PO-001",
    supplier_user_code="KDKK",
    supplier_user_name="KDKK",
    customer_order_no="CUST-2024-001",
    received_at=datetime.now(),
    due_date=date(2025, 1, 15),
    status="DRAFT",
    memo="테스트 수주 - COS 가스 50본",
    created_by=creator
)

POItem.objects.create(
    po=po1,
    line_no=1,
    trade_condition_code="9100010103000099",
    trade_condition_name="COS 47L",
    qty=50,
    unit_price=50000.00,
    remarks=""
)

print(f"✅ 수주 1 생성: {po1.po_no} - {po1.supplier_user_name} ({po1.customer_order_no})")

# 수주 2: 긴급 수주
po2 = PO.objects.create(
    po_no="TEST-PO-002",
    supplier_user_code="SAMSUNG",
    supplier_user_name="삼성전자",
    customer_order_no="CUST-2024-002",
    received_at=datetime.now(),
    due_date=date(2024, 12, 25),
    status="RESERVED",
    memo="긴급 수주 - CLF3 가스 100본",
    created_by=creator
)

POItem.objects.create(
    po=po2,
    line_no=1,
    trade_condition_code="9100010301000099",
    trade_condition_name="CLF3 47L",
    qty=100,
    unit_price=120000.00,
    remarks="긴급"
)

print(f"✅ 수주 2 생성: {po2.po_no} - {po2.supplier_user_name} ({po2.customer_order_no})")

# 수주 3: 분할 납품
po3 = PO.objects.create(
    po_no="TEST-PO-003",
    supplier_user_code="HYNIX",
    supplier_user_name="SK하이닉스",
    customer_order_no="CUST-2024-003",
    received_at=datetime.now(),
    due_date=date(2025, 2, 1),
    status="DRAFT",
    memo="분할 납품 수주 - 2회 납품",
    created_by=creator
)

POItem.objects.create(
    po=po3,
    line_no=1,
    trade_condition_code="9100010103000099",
    trade_condition_name="COS 47L",
    qty=200,
    unit_price=48000.00,
    remarks="분할납품: 1차 100본, 2차 100본"
)

print(f"✅ 수주 3 생성: {po3.po_no} - {po3.supplier_user_name} ({po3.customer_order_no})")

print("\n" + "=" * 80)
print("총 3건의 테스트 수주 생성 완료!")
print("=" * 80)
print(f"\n확인: http://10.78.30.98/cynow/orders/")
print(f"관리: http://10.78.30.98/cynow/admin/orders/po/")


