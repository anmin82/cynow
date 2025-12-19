"""
PO 폼
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import PO, POItem


class POForm(forms.ModelForm):
    """PO 생성/수정 폼"""
    
    class Meta:
        model = PO
        fields = [
            'supplier_user_code',
            'supplier_user_name',
            'customer_order_no',
            'received_at',
            'due_date',
            'status',
            'memo',
        ]
        widgets = {
            'supplier_user_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '예: KDKK'
            }),
            'supplier_user_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '예: KDKK'
            }),
            'customer_order_no': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '예: CUST-2024-001'
            }),
            'received_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'memo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '메모 (선택사항)'
            }),
        }
        labels = {
            'supplier_user_code': '고객 코드',
            'supplier_user_name': '고객명',
            'customer_order_no': 'PO번호(고객발주번호)',  # ✅ PO번호는 이것 하나뿐
            'received_at': '수주 접수일시',
            'due_date': '납기일',
            'status': '상태',
            'memo': '메모',
        }
    
    def clean_customer_order_no(self):
        """고객 발주번호 중복 체크 (PO 번호는 유일해야 함)"""
        customer_order_no = self.cleaned_data.get('customer_order_no')
        
        # 수정 시 자기 자신은 제외
        qs = PO.objects.filter(customer_order_no=customer_order_no)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise ValidationError(
                f'이미 존재하는 PO번호(고객발주번호)입니다.'
            )
        
        return customer_order_no


class POItemForm(forms.ModelForm):
    """PO 라인 아이템 폼"""
    
    class Meta:
        model = POItem
        fields = [
            'line_no',
            'trade_condition_code',
            'trade_condition_name',
            'qty',
            'unit_price',
            'remarks',
        ]
        widgets = {
            'line_no': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'min': 1
            }),
            'trade_condition_code': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': '품목코드'
            }),
            'trade_condition_name': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': '품목명'
            }),
            'qty': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'min': 1,
                'placeholder': '수량'
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'step': '0.01',
                'placeholder': '단가 (선택)'
            }),
            'remarks': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': '비고 (선택)'
            }),
        }
        labels = {
            'line_no': '라인',
            'trade_condition_code': '품목코드',
            'trade_condition_name': '품목명',
            'qty': '수량',
            'unit_price': '단가',
            'remarks': '비고',
        }


# Django Formset으로 여러 POItem을 한번에 처리
POItemFormSet = forms.inlineformset_factory(
    PO,
    POItem,
    form=POItemForm,
    extra=1,  # 빈 폼 1개
    can_delete=True,
    min_num=1,  # 최소 1개 라인
    validate_min=True,
)

