"""EndUser 예외 입력"""
from django.core.management.base import BaseCommand
from django.db import connection
import csv
import os


class Command(BaseCommand):
    help = 'EndUser 예외 입력 (용기번호별로 기본값과 다른 EndUser 지정)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='CSV 파일 경로 (컬럼: cylinder_no, enduser, reason)'
        )
        parser.add_argument(
            '--cylinder-no',
            type=str,
            help='용기번호'
        )
        parser.add_argument(
            '--enduser',
            type=str,
            help='EndUser (예: LGD, SDC)'
        )
        parser.add_argument(
            '--reason',
            type=str,
            default='',
            help='사유 (선택사항)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='실제 저장하지 않고 미리보기만'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        file_path = options.get('file')
        cylinder_no = options.get('cylinder_no')
        enduser = options.get('enduser')
        reason = options.get('reason', '')
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN 모드: 실제 저장하지 않습니다."))
        
        with connection.cursor() as cursor:
            # CSV 파일로 일괄 입력
            if file_path:
                if not os.path.exists(file_path):
                    self.stdout.write(self.style.ERROR(f"CSV 파일을 찾을 수 없습니다: {file_path}"))
                    return
                
                self.stdout.write(f"CSV 파일 읽는 중: {file_path}")
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    count = 0
                    for row in reader:
                        cyl_no = row.get('cylinder_no', '').strip()
                        end_user = row.get('enduser', '').strip()
                        reason_text = row.get('reason', '').strip()
                        
                        if not cyl_no or not end_user:
                            self.stdout.write(self.style.WARNING(f"건너뜀: cylinder_no={cyl_no}, enduser={end_user}"))
                            continue
                        
                        if dry_run:
                            self.stdout.write(f"  - {cyl_no} → {end_user} ({reason_text})")
                        else:
                            cursor.execute("""
                                INSERT INTO cy_enduser_exception 
                                (cylinder_no, enduser, reason, is_active)
                                VALUES (%s, %s, %s, TRUE)
                                ON CONFLICT (cylinder_no) 
                                DO UPDATE SET 
                                    enduser = EXCLUDED.enduser,
                                    reason = EXCLUDED.reason,
                                    is_active = TRUE,
                                    updated_at = NOW()
                            """, [cyl_no, end_user, reason_text])
                            count += 1
                    
                    if not dry_run:
                        self.stdout.write(self.style.SUCCESS(f"{count}개 예외 입력 완료"))
            
            # 단일 입력
            elif cylinder_no and enduser:
                if dry_run:
                    self.stdout.write(f"다음 예외가 입력됩니다:")
                    self.stdout.write(f"  용기번호: {cylinder_no}")
                    self.stdout.write(f"  EndUser: {enduser}")
                    self.stdout.write(f"  사유: {reason}")
                else:
                    cursor.execute("""
                        INSERT INTO cy_enduser_exception 
                        (cylinder_no, enduser, reason, is_active)
                        VALUES (%s, %s, %s, TRUE)
                        ON CONFLICT (cylinder_no) 
                        DO UPDATE SET 
                            enduser = EXCLUDED.enduser,
                            reason = EXCLUDED.reason,
                            is_active = TRUE,
                            updated_at = NOW()
                    """, [cylinder_no, enduser, reason])
                    self.stdout.write(self.style.SUCCESS(f"예외 입력 완료: {cylinder_no} → {enduser}"))
            
            else:
                self.stdout.write(self.style.ERROR("사용법:"))
                self.stdout.write("  CSV 파일 입력: python manage.py load_enduser_exceptions --file exceptions.csv")
                self.stdout.write("  단일 입력: python manage.py load_enduser_exceptions --cylinder-no 22DH0001 --enduser LGD --reason 'LGD 납품 전용'")
                self.stdout.write("\nCSV 파일 형식:")
                self.stdout.write("  cylinder_no,enduser,reason")
                self.stdout.write("  22DH0001,LGD,LGD 납품 전용")
                self.stdout.write("  22DH0002,LGD,LGD 납품 전용")

