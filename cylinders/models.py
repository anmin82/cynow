from django.db import models
from django.utils import timezone


class CylinderMemo(models.Model):
    """용기별 메모/댓글"""
    
    cylinder_no = models.CharField(
        max_length=20, 
        db_index=True,
        verbose_name='용기번호'
    )
    
    # 답글인 경우 부모 메모 참조
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='replies',
        verbose_name='상위 메모'
    )
    
    # 작성자 정보 (비로그인)
    author_name = models.CharField(
        max_length=50,
        verbose_name='작성자명'
    )
    
    # 4자리 숫자 암호 (수정/삭제용)
    password = models.CharField(
        max_length=4,
        default='0000',
        verbose_name='암호',
        help_text='4자리 숫자'
    )
    
    # 내용
    content = models.TextField(
        verbose_name='내용'
    )
    
    # 메타데이터
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='작성일시'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )
    
    # 관리용
    is_active = models.BooleanField(
        default=True,
        verbose_name='활성화'
    )
    
    class Meta:
        db_table = 'cylinder_memo'
        verbose_name = '용기 메모'
        verbose_name_plural = '용기 메모'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cylinder_no', '-created_at']),
        ]
    
    def __str__(self):
        return f"[{self.cylinder_no}] {self.author_name}: {self.content[:30]}"
    
    @property
    def is_reply(self):
        """답글 여부"""
        return self.parent is not None
    
    @property
    def reply_count(self):
        """답글 수"""
        return self.replies.filter(is_active=True).count()
