from django.db import models
from django.utils import timezone


class Translation(models.Model):
    """다국어 번역 매핑 (FCMS 원본 → 표시명)"""
    
    FIELD_TYPE_CHOICES = [
        ('gas_name', '가스명'),
        ('valve_spec', '밸브 스펙'),
        ('cylinder_spec', '용기 스펙'),
        ('usage_place', '사용처'),
        ('location', '위치'),
    ]
    
    field_type = models.CharField(
        max_length=50,
        choices=FIELD_TYPE_CHOICES,
        verbose_name='필드 타입',
        help_text='번역할 필드의 타입'
    )
    source_text = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name='원본값',
        help_text='FCMS 원본 데이터 값 (대소문자 구분 없음)',
        db_index=True
    )
    display_ko = models.CharField(
        max_length=500,
        blank=True,
        default='',
        verbose_name='한국어 표시명',
        help_text='한국어로 표시할 이름 (기본 언어)'
    )
    display_ja = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='일본어 표시명',
        help_text='일본어로 표시할 이름 (선택)'
    )
    display_en = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='영어 표시명',
        help_text='영어로 표시할 이름 (선택)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성화',
        help_text='이 번역을 사용할지 여부'
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='메모',
        help_text='번역 관련 메모나 참고사항'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )
    
    class Meta:
        verbose_name = '번역'
        verbose_name_plural = '번역'
        unique_together = [['field_type', 'source_text']]
        indexes = [
            models.Index(fields=['field_type', 'source_text']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"[{self.get_field_type_display()}] {self.source_text} → {self.display_ko}"
    
    def get_display(self, lang='ko'):
        """언어별 표시명 반환"""
        if lang == 'ja' and self.display_ja:
            return self.display_ja
        elif lang == 'en' and self.display_en:
            return self.display_en
        return self.display_ko  # 기본값: 한국어


class EndUserMaster(models.Model):
    """EndUser 마스터"""
    enduser_code = models.CharField(max_length=50, unique=True, verbose_name='EndUser 코드')
    enduser_name = models.CharField(max_length=200, verbose_name='EndUser 이름')
    description = models.TextField(blank=True, null=True, verbose_name='설명')
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        db_table = 'cy_enduser_master'
        verbose_name = 'EndUser 마스터'
        verbose_name_plural = 'EndUser 마스터'
        indexes = [
            models.Index(fields=['enduser_code']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.enduser_code} - {self.enduser_name}"


class EndUserDefault(models.Model):
    """EndUser 기본값 설정"""
    gas_name = models.CharField(max_length=100, verbose_name='가스명')
    capacity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='용량')
    valve_spec_code = models.CharField(max_length=50, null=True, blank=True, verbose_name='밸브 스펙 코드')
    cylinder_spec_code = models.CharField(max_length=50, null=True, blank=True, verbose_name='용기 스펙 코드')
    default_enduser = models.CharField(max_length=50, default='SDC', verbose_name='기본 EndUser')
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        db_table = 'cy_enduser_default'
        verbose_name = 'EndUser 기본값'
        verbose_name_plural = 'EndUser 기본값'
        unique_together = [['gas_name', 'capacity', 'valve_spec_code', 'cylinder_spec_code']]
        indexes = [
            models.Index(fields=['gas_name', 'capacity', 'valve_spec_code', 'cylinder_spec_code']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.gas_name} {self.capacity or '전체'} → {self.default_enduser}"


class EndUserException(models.Model):
    """EndUser 예외 지정 (기본값과 다른 경우)"""
    cylinder_no = models.CharField(max_length=20, unique=True, verbose_name='용기번호')
    enduser = models.CharField(max_length=50, verbose_name='EndUser')
    reason = models.TextField(blank=True, null=True, verbose_name='사유')
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        db_table = 'cy_enduser_exception'
        verbose_name = 'EndUser 예외'
        verbose_name_plural = 'EndUser 예외'
        indexes = [
            models.Index(fields=['cylinder_no']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.cylinder_no} → {self.enduser}"


class ValveGroup(models.Model):
    """밸브 그룹 정의"""
    group_name = models.CharField(max_length=100, unique=True, verbose_name='그룹명')
    description = models.TextField(blank=True, null=True, verbose_name='설명')
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        db_table = 'cy_valve_group'
        verbose_name = '밸브 그룹'
        verbose_name_plural = '밸브 그룹'
    
    def __str__(self):
        return self.group_name


class ValveGroupMapping(models.Model):
    """밸브 → 그룹 매핑"""
    valve_spec_code = models.CharField(max_length=50, verbose_name='밸브 스펙 코드')
    valve_spec_name = models.CharField(max_length=200, verbose_name='밸브 스펙명')
    group = models.ForeignKey(ValveGroup, on_delete=models.CASCADE, related_name='mappings', verbose_name='그룹', db_column='group_id')
    is_primary = models.BooleanField(default=False, verbose_name='대표 밸브')
    is_active = models.BooleanField(default=True, verbose_name='활성화')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')
    
    class Meta:
        db_table = 'cy_valve_group_mapping'
        verbose_name = '밸브 그룹 매핑'
        verbose_name_plural = '밸브 그룹 매핑'
        unique_together = [['valve_spec_code', 'valve_spec_name']]
        indexes = [
            models.Index(fields=['valve_spec_code', 'valve_spec_name']),
            models.Index(fields=['group', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.valve_spec_name} → {self.group.group_name}"


class HiddenCylinderType(models.Model):
    """대시보드에서 숨긴 용기종류"""
    cylinder_type_key = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='용기종류 키',
        help_text='gas_name|capacity|valve_type|cylinder_spec|enduser 형식의 키'
    )
    gas_name = models.CharField(max_length=100, verbose_name='가스명')
    capacity = models.CharField(max_length=50, blank=True, default='', verbose_name='용량')
    valve_type = models.CharField(max_length=100, blank=True, default='', verbose_name='밸브타입')
    cylinder_spec = models.CharField(max_length=200, blank=True, default='', verbose_name='용기스펙')
    enduser = models.CharField(max_length=100, blank=True, default='', verbose_name='EndUser')
    hidden_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='숨김 처리자'
    )
    reason = models.TextField(blank=True, default='', verbose_name='숨김 사유')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='숨김일시')
    
    class Meta:
        db_table = 'cy_hidden_cylinder_type'
        verbose_name = '숨김 용기종류'
        verbose_name_plural = '숨김 용기종류'
        indexes = [
            models.Index(fields=['cylinder_type_key']),
            models.Index(fields=['gas_name']),
        ]
    
    def __str__(self):
        return f"[숨김] {self.gas_name} {self.capacity or ''} {self.enduser or ''}"
