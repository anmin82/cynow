"""데이터베이스에서 일본어 데이터를 추출하여 번역 테이블에 로드"""
from django.core.management.base import BaseCommand
from django.db import connection
from core.models import Translation
from core.utils.translation import get_or_create_translation


class Command(BaseCommand):
    help = '데이터베이스에서 일본어 데이터를 추출하여 번역 테이블에 로드'

    def add_arguments(self, parser):
        parser.add_argument(
            '--field-type',
            type=str,
            choices=['gas_name', 'valve_spec', 'cylinder_spec', 'usage_place', 'location', 'all'],
            default='all',
            help='로드할 필드 타입 (기본값: all)'
        )
        parser.add_argument(
            '--auto-translate',
            action='store_true',
            help='자동 번역 시도 (Google Translate API 등 사용)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제로 저장하지 않고 미리보기만'
        )

    def handle(self, *args, **options):
        field_type = options['field_type']
        auto_translate = options['auto_translate']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN 모드: 실제로 저장하지 않습니다."))
        
        field_types_to_load = []
        if field_type == 'all':
            field_types_to_load = ['gas_name', 'valve_spec', 'cylinder_spec', 'usage_place', 'location']
        else:
            field_types_to_load = [field_type]
        
        try:
            with connection.cursor() as cursor:
                total_loaded = 0
                
                for ft in field_types_to_load:
                    self.stdout.write(f"\n=== {ft} 필드 로드 중 ===")
                    
                    # VIEW에서 고유한 값 추출
                    column_name = ft
                    
                    # vw_cynow_inventory와 vw_cynow_cylinder_list에서 모두 추출
                    # 스키마 지정 (public 스키마에 VIEW가 생성됨)
                    queries = [
                        f'SELECT DISTINCT "{column_name}" FROM vw_cynow_inventory WHERE "{column_name}" IS NOT NULL AND "{column_name}" != \'\'',
                        f'SELECT DISTINCT "{column_name}" FROM vw_cynow_cylinder_list WHERE "{column_name}" IS NOT NULL AND "{column_name}" != \'\'',
                    ]
                    
                    unique_values = set()
                    for query in queries:
                        try:
                            cursor.execute(query)
                            rows = cursor.fetchall()
                            for row in rows:
                                if row[0]:
                                    unique_values.add(str(row[0]).strip())
                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"  쿼리 실행 오류: {e}"))
                            continue
                    
                    self.stdout.write(f"  발견된 고유 값: {len(unique_values)}개")
                    
                    # 각 값에 대해 번역 엔트리 생성
                    created_count = 0
                    existing_count = 0
                    
                    for value in sorted(unique_values):
                        if not value:
                            continue
                        
                        # 이미 번역이 있는지 확인
                        existing = Translation.objects.filter(
                            field_type=ft,
                            japanese_text__iexact=value
                        ).first()
                        
                        if existing:
                            existing_count += 1
                            if not dry_run:
                                self.stdout.write(f"  [기존] {value}")
                            continue
                        
                        # 새 번역 생성
                        korean_text = value  # 기본값은 원문
                        
                        if auto_translate:
                            # TODO: 자동 번역 API 연동 (Google Translate, DeepL 등)
                            # korean_text = auto_translate_japanese_to_korean(value)
                            pass
                        
                        if not dry_run:
                            translation, created = get_or_create_translation(
                                field_type=ft,
                                japanese_text=value,
                                korean_text=korean_text
                            )
                            if created:
                                created_count += 1
                                self.stdout.write(self.style.SUCCESS(f"  [생성] {value} → {korean_text}"))
                            else:
                                existing_count += 1
                        else:
                            created_count += 1
                            self.stdout.write(f"  [생성 예정] {value} → {korean_text}")
                    
                    self.stdout.write(f"  생성: {created_count}개, 기존: {existing_count}개")
                    total_loaded += created_count
                
                self.stdout.write(self.style.SUCCESS(f"\n총 {total_loaded}개의 번역이 로드되었습니다."))
                self.stdout.write("\n다음 단계:")
                self.stdout.write("  1. Django 관리자 페이지(/admin/core/translation/)에서 번역을 확인하세요")
                self.stdout.write("  2. 번역이 이상한 곳은 직접 수정하세요")
                self.stdout.write("  3. is_active를 True로 설정하면 자동으로 적용됩니다")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"오류 발생: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())
            raise
