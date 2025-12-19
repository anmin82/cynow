"""커스텀 권한 생성"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.apps import apps


class Command(BaseCommand):
    help = 'CYNOW 커스텀 권한 생성'

    def handle(self, *args, **options):
        # ContentType 가져오기 (core 앱 사용)
        try:
            content_type = ContentType.objects.get_for_model(apps.get_model('core', 'CynowConfig'))
        except:
            # core 앱에 모델이 없으면 임의의 ContentType 생성
            from django.contrib.contenttypes.models import ContentType
            content_type, created = ContentType.objects.get_or_create(
                app_label='cynow',
                model='plan'
            )
        
        # 권한 생성
        permission, created = Permission.objects.get_or_create(
            codename='can_edit_plan',
            name='Can edit plan',
            content_type=content_type,
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created permission: {permission.codename}'))
        else:
            self.stdout.write(f'Permission already exists: {permission.codename}')
        
        # 편집자 그룹 생성
        editor_group, created = Group.objects.get_or_create(name='CYNOW Editors')
        if created:
            editor_group.permissions.add(permission)
            self.stdout.write(self.style.SUCCESS('Created group: CYNOW Editors'))
        else:
            self.stdout.write('Group already exists: CYNOW Editors')

