"""
수주 입력 폼

개선:
- 고객 선택 드롭다운 (CompanyInfo 연동)
- ProductCode 자동완성/검색
- 단가 자동 로딩
- 납기 선택 (분납/지정일)
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import PO, POItem
from voucher.models import CompanyInfo


class POForm(forms.ModelForm):
    """PO 생성/수정 폼"""
    
    # 고객 선택 드롭다운
    customer = forms.ModelChoiceField(
        queryset=CompanyInfo.objects.filter(is_customer=True, is_active=True).order_by('name'),
        required=False,
        empty_label='-- 고객사 선택 --',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'customer-select'
        }),
        label='고객사'
    )
    
    class Meta:
        model = PO
        fields = [
            'customer',
            'customer_order_no',
            'supplier_user_code',
            'supplier_user_name',
            'received_at',
            'status',
            'memo',
        ]
        widgets = {
            'customer_order_no': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '고객 PO번호 입력'
            }),
            'supplier_user_code': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': '고객 선택 시 자동입력'
            }),
            'supplier_user_name': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly',
                'placeholder': '고객 선택 시 자동입력'
            }),
            'received_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'memo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': '메모 (선택사항)'
            }),
        }
        labels = {
            'customer_order_no': 'PO번호',
            'supplier_user_code': '고객코드',
            'supplier_user_name': '고객명',
            'received_at': '수주일시',
            'status': '상태',
            'memo': '메모',
        }
    
    def clean_customer_order_no(self):
        """PO번호(고객발주번호) 중복 체크"""
        customer_order_no = self.cleaned_data.get('customer_order_no')
        
        # 수정 시 자기 자신은 제외
        qs = PO.objects.filter(customer_order_no=customer_order_no)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        
        if qs.exists():
            raise ValidationError('이미 존재하는 PO번호입니다.')
        
        return customer_order_no


class POItemForm(forms.ModelForm):
    """수주 품목 폼 (개선됨)"""
    
    # 제품코드 검색용 히든 필드 (product_code FK)
    product_code_pk = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={
            'class': 'product-code-pk'
        })
    )
    
    class Meta:
        model = POItem
        fields = [
            'line_no',
            'trade_condition_code',
            'trade_condition_name',
            'gas_name',
            'cylinder_spec',
            'valve_spec',
            'filling_weight',
            'qty',
            'unit_price',
            'currency',
            'delivery_date',
            'remarks',
        ]
        widgets = {
            'line_no': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm line-no',
                'min': 1,
                'style': 'width: 50px;'
            }),
            'trade_condition_code': forms.Select(attrs={
                'class': 'form-select form-select-sm product-select',
            }),
            'trade_condition_name': forms.HiddenInput(attrs={
                'class': 'product-name'
            }),
            'gas_name': forms.HiddenInput(attrs={
                'class': 'gas-name'
            }),
            'cylinder_spec': forms.HiddenInput(attrs={
                'class': 'cylinder-spec'
            }),
            'valve_spec': forms.HiddenInput(attrs={
                'class': 'valve-spec'
            }),
            'filling_weight': forms.HiddenInput(attrs={
                'class': 'filling-weight'
            }),
            'qty': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm qty-input',
                'min': 1,
                'placeholder': '수량',
                'style': 'width: 80px;'
            }),
            'unit_price': forms.HiddenInput(attrs={
                'class': 'unit-price'
            }),
            'currency': forms.HiddenInput(attrs={
                'class': 'currency-value'
            }),
            'delivery_date': forms.DateInput(attrs={
                'class': 'form-control form-control-sm delivery-date',
                'type': 'date',
                'style': 'width: 130px;'
            }),
            'remarks': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': '비고'
            }),
        }
        labels = {
            'line_no': 'No',
            'trade_condition_code': '제품',
            'qty': '수량',
            'delivery_date': '납기',
            'remarks': '비고',
        }
    
    def save(self, commit=True):
        """저장 시 ProductCode FK 설정"""
        instance = super().save(commit=False)
        
        # product_code_pk가 있으면 FK 설정
        product_code_pk = self.cleaned_data.get('product_code_pk')
        if product_code_pk:
            from products.models import ProductCode
            try:
                instance.product_code = ProductCode.objects.get(pk=product_code_pk)
            except ProductCode.DoesNotExist:
                pass
        
        if commit:
            instance.save()
        return instance


# Django Formset으로 여러 POItem을 한번에 처리
POItemFormSet = forms.inlineformset_factory(
    PO,
    POItem,
    form=POItemForm,
    extra=3,  # 빈 폼 3개
    can_delete=True,
    min_num=1,  # 최소 1개 라인
    validate_min=True,
)
