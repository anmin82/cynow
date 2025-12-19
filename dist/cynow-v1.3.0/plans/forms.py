from django import forms
from .models import PlanForecastMonthly, PlanScheduledMonthly
from core.repositories.view_repository import ViewRepository
from core.utils.cylinder_type import generate_cylinder_type_key


class PlanForecastForm(forms.ModelForm):
    """출하 계획 입력 폼"""
    
    class Meta:
        model = PlanForecastMonthly
        fields = ['month', 'gas_name', 'capacity', 'valve_spec', 'cylinder_spec', 
                  'usage_place', 'planned_ship_qty', 'note']
        widgets = {
            'month': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'gas_name': forms.TextInput(attrs={'class': 'form-control'}),
            'capacity': forms.TextInput(attrs={'class': 'form-control'}),
            'valve_spec': forms.TextInput(attrs={'class': 'form-control'}),
            'cylinder_spec': forms.TextInput(attrs={'class': 'form-control'}),
            'usage_place': forms.TextInput(attrs={'class': 'form-control'}),
            'planned_ship_qty': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        if user:
            instance.created_by = user
        
        # cylinder_type_key 생성
        instance.cylinder_type_key = generate_cylinder_type_key(
            instance.gas_name,
            instance.capacity,
            instance.valve_spec,
            instance.cylinder_spec,
            instance.usage_place
        )
        
        if commit:
            instance.save()
        return instance


class PlanScheduledForm(forms.ModelForm):
    """투입 계획 입력 폼"""
    
    class Meta:
        model = PlanScheduledMonthly
        fields = ['month', 'gas_name', 'capacity', 'valve_spec', 'cylinder_spec',
                  'usage_place', 'add_purchase_qty', 'add_refurb_qty',
                  'recover_from_defect_qty', 'convert_gas_qty', 'note']
        widgets = {
            'month': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'gas_name': forms.TextInput(attrs={'class': 'form-control'}),
            'capacity': forms.TextInput(attrs={'class': 'form-control'}),
            'valve_spec': forms.TextInput(attrs={'class': 'form-control'}),
            'cylinder_spec': forms.TextInput(attrs={'class': 'form-control'}),
            'usage_place': forms.TextInput(attrs={'class': 'form-control'}),
            'add_purchase_qty': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'add_refurb_qty': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'recover_from_defect_qty': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'convert_gas_qty': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def save(self, commit=True, user=None):
        instance = super().save(commit=False)
        if user:
            instance.created_by = user
        
        # cylinder_type_key 생성
        instance.cylinder_type_key = generate_cylinder_type_key(
            instance.gas_name,
            instance.capacity,
            instance.valve_spec,
            instance.cylinder_spec,
            instance.usage_place
        )
        
        if commit:
            instance.save()
        return instance

