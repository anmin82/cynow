"""CDC 동기화 지연 확인 및 알림"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from datetime import timedelta
import sys


class Command(BaseCommand):
    help = 'CDC 동기화 지연 시간 확인 및 알림'

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=int,
            default=60,
            help='알림 임계값 (분 단위, 기본 60분)'
        )
        parser.add_argument(
            '--schema',
            type=str,
            default='fcms_cdc',
            help='CDC 스키마 이름 (기본: fcms_cdc)'
        )

    def handle(self, *args, **options):
        threshold_minutes = options['threshold']
        cdc_schema = options['schema']
        threshold_time = timezone.now() - timedelta(minutes=threshold_minutes)
        
        self.stdout.write('========================================')
        self.stdout.write('CDC 동기화 상태 확인')
        self.stdout.write(f'스키마: {cdc_schema}')
        self.stdout.write(f'임계값: {threshold_minutes}분 이전')
        self.stdout.write(f'현재 시각: {timezone.now()}')
        self.stdout.write('========================================')
        
        try:
            with connection.cursor() as cursor:
                # PostgreSQL의 CDC 테이블 목록 조회
                cursor.execute(f"""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = %s
                    AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                """, [cdc_schema])
                
                tables = [row[0] for row in cursor.fetchall()]
                
                if not tables:
                    self.stdout.write(
                        self.style.WARNING(
                            f'⚠️ 스키마 {cdc_schema}에 테이블이 없습니다. '
                            f'스키마 이름을 확인하세요.'
                        )
                    )
                    return
                
                self.stdout.write(f'\n확인할 테이블: {len(tables)}개\n')
                
                all_ok = True
                lag_info = []
                
                for table_name in tables:
                    try:
                        # Debezium 메타데이터 컬럼 확인
                        # __source_ts_ms: Debezium이 추가하는 타임스탬프 (밀리초)
                        cursor.execute(f"""
                            SELECT 
                                column_name
                            FROM information_schema.columns
                            WHERE table_schema = %s
                            AND table_name = %s
                            AND column_name IN ('__source_ts_ms', '__ts_ms', 'last_modified_date', 'updated_at')
                            LIMIT 1
                        """, [cdc_schema, table_name])
                        
                        timestamp_col_result = cursor.fetchone()
                        
                        if not timestamp_col_result:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'⚠️ {table_name}: 타임스탬프 컬럼 없음 (스킵)'
                                )
                            )
                            continue
                        
                        timestamp_col = timestamp_col_result[0]
                        
                        # 최근 업데이트 시간 조회
                        cursor.execute(f"""
                            SELECT 
                                MAX({timestamp_col}) as last_update,
                                COUNT(*) as row_count
                            FROM {cdc_schema}.{table_name}
                        """)
                        
                        result = cursor.fetchone()
                        last_update_raw = result[0]
                        row_count = result[1]
                        
                        if last_update_raw is None:
                            self.stdout.write(
                                self.style.WARNING(
                                    f'⚠️ {table_name}: 데이터 없음 (0건)'
                                )
                            )
                            continue
                        
                        # 타임스탬프 변환
                        if isinstance(last_update_raw, int):
                            # 밀리초 타임스탬프 (__source_ts_ms, __ts_ms)
                            last_update = timezone.datetime.fromtimestamp(
                                last_update_raw / 1000,
                                tz=timezone.utc
                            )
                        else:
                            # datetime 객체
                            if timezone.is_naive(last_update_raw):
                                last_update = timezone.make_aware(last_update_raw)
                            else:
                                last_update = last_update_raw
                        
                        lag = timezone.now() - last_update
                        lag_minutes = lag.total_seconds() / 60
                        
                        # 상태 출력
                        status_msg = (
                            f'{table_name:30s} | '
                            f'마지막 업데이트: {last_update.strftime("%Y-%m-%d %H:%M:%S")} | '
                            f'지연: {lag_minutes:6.1f}분 | '
                            f'{row_count:,}건'
                        )
                        
                        if last_update < threshold_time:
                            self.stdout.write(
                                self.style.ERROR(f'❌ {status_msg}')
                            )
                            all_ok = False
                            lag_info.append({
                                'table': table_name,
                                'lag_minutes': lag_minutes,
                                'last_update': last_update,
                            })
                        else:
                            self.stdout.write(
                                self.style.SUCCESS(f'✓ {status_msg}')
                            )
                    
                    except Exception as table_err:
                        self.stdout.write(
                            self.style.ERROR(
                                f'❌ {table_name}: 확인 실패 - {table_err}'
                            )
                        )
                        all_ok = False
                
                self.stdout.write('\n========================================')
                
                if all_ok:
                    self.stdout.write(
                        self.style.SUCCESS('✓ 모든 테이블 동기화 정상')
                    )
                    sys.exit(0)
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f'⚠️ {len(lag_info)}개 테이블에서 동기화 지연 감지'
                        )
                    )
                    
                    if lag_info:
                        self.stdout.write('\n지연된 테이블:')
                        for info in lag_info:
                            self.stdout.write(
                                f"  - {info['table']}: {info['lag_minutes']:.1f}분 지연"
                            )
                    
                    self.stdout.write('\n권장 조치:')
                    self.stdout.write('  1. Debezium Connector 상태 확인')
                    self.stdout.write('     curl http://localhost:8083/connectors/fcms-oracle-connector/status')
                    self.stdout.write('  2. Kafka Connect 로그 확인')
                    self.stdout.write('  3. Oracle 리스너 상태 확인')
                    self.stdout.write('  4. 필요시 Connector 재시작')
                    self.stdout.write('     curl -X POST http://localhost:8083/connectors/fcms-oracle-connector/restart')
                    
                    sys.exit(1)
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'오류 발생: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())
            sys.exit(1)













