"""Kafka PostgreSQL Sink Connector 상태 확인 및 문제 진단"""
import json
import requests
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Kafka PostgreSQL Sink Connector 상태 확인 및 문제 진단'

    def add_arguments(self, parser):
        parser.add_argument(
            '--connector-name',
            type=str,
            default='postgresql-sink-fcms',
            help='Sink Connector 이름 (기본값: postgresql-sink-fcms)'
        )
        parser.add_argument(
            '--connect-url',
            type=str,
            default='http://localhost:8083',
            help='Kafka Connect REST API URL (기본값: http://localhost:8083)'
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='자동으로 문제를 수정 시도'
        )

    def handle(self, *args, **options):
        connector_name = options['connector_name']
        connect_url = options['connect_url']
        auto_fix = options['fix']

        self.stdout.write(f"\n=== Kafka Sink Connector 진단 ===\n")
        self.stdout.write(f"Connector: {connector_name}")
        self.stdout.write(f"Connect URL: {connect_url}\n")

        try:
            # 1. 커넥터 목록 확인
            self.stdout.write("1. 커넥터 목록 확인 중...")
            try:
                response = requests.get(f"{connect_url}/connectors", timeout=5)
                if response.status_code == 200:
                    connectors = response.json()
                    self.stdout.write(self.style.SUCCESS(f"   ✓ 연결 성공 (총 {len(connectors)}개 커넥터)"))
                    if connector_name not in connectors:
                        self.stdout.write(self.style.WARNING(f"   ⚠ '{connector_name}' 커넥터를 찾을 수 없습니다."))
                        self.stdout.write(f"   사용 가능한 커넥터: {', '.join(connectors)}")
                        return
                else:
                    self.stdout.write(self.style.ERROR(f"   ✗ HTTP {response.status_code}: {response.text}"))
                    return
            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f"   ✗ Kafka Connect에 연결할 수 없습니다: {e}"))
                self.stdout.write(f"   Connect URL을 확인하세요: {connect_url}")
                return

            # 2. 커넥터 상태 확인
            self.stdout.write(f"\n2. '{connector_name}' 커넥터 상태 확인 중...")
            try:
                response = requests.get(f"{connect_url}/connectors/{connector_name}/status", timeout=5)
                if response.status_code != 200:
                    self.stdout.write(self.style.ERROR(f"   ✗ 커넥터를 찾을 수 없습니다 (HTTP {response.status_code})"))
                    return

                status = response.json()
                connector_state = status.get('connector', {}).get('state', 'UNKNOWN')
                worker_id = status.get('connector', {}).get('worker_id', 'N/A')

                self.stdout.write(f"   상태: {connector_state}")
                self.stdout.write(f"   Worker: {worker_id}")

                if connector_state == 'RUNNING':
                    self.stdout.write(self.style.SUCCESS("   ✓ 커넥터가 정상 실행 중입니다"))
                elif connector_state == 'FAILED':
                    self.stdout.write(self.style.ERROR("   ✗ 커넥터가 실패했습니다"))
                    error = status.get('connector', {}).get('trace', 'N/A')
                    if error and error != 'N/A':
                        self.stdout.write(f"   오류 메시지:\n{error}")
                elif connector_state == 'PAUSED':
                    self.stdout.write(self.style.WARNING("   ⚠ 커넥터가 일시 정지되었습니다"))
                else:
                    self.stdout.write(self.style.WARNING(f"   ⚠ 알 수 없는 상태: {connector_state}"))

                # 3. Task 상태 확인
                self.stdout.write(f"\n3. Task 상태 확인 중...")
                tasks = status.get('tasks', [])
                if not tasks:
                    self.stdout.write(self.style.WARNING("   ⚠ Task가 없습니다"))
                else:
                    failed_tasks = []
                    for i, task in enumerate(tasks):
                        task_id = task.get('id', i)
                        task_state = task.get('state', 'UNKNOWN')
                        worker_id = task.get('worker_id', 'N/A')
                        
                        self.stdout.write(f"   Task {task_id}: {task_state} (Worker: {worker_id})")
                        
                        if task_state == 'FAILED':
                            failed_tasks.append(task)
                            trace = task.get('trace', '')
                            if trace:
                                self.stdout.write(self.style.ERROR(f"      오류:\n{trace[:500]}"))
                                if len(trace) > 500:
                                    self.stdout.write(f"      ... (전체 오류 메시지는 로그에서 확인)")

                    if failed_tasks:
                        self.stdout.write(self.style.ERROR(f"\n   ✗ {len(failed_tasks)}개의 Task가 실패했습니다"))
                    else:
                        self.stdout.write(self.style.SUCCESS(f"   ✓ 모든 Task가 정상 실행 중입니다 ({len(tasks)}개)"))

                # 4. 커넥터 설정 확인
                self.stdout.write(f"\n4. 커넥터 설정 확인 중...")
                try:
                    response = requests.get(f"{connect_url}/connectors/{connector_name}/config", timeout=5)
                    if response.status_code == 200:
                        config = response.json()
                        self.stdout.write(f"   Connection URL: {config.get('connection.url', 'N/A')}")
                        self.stdout.write(f"   Topics: {config.get('topics', 'N/A')}")
                        self.stdout.write(f"   Tasks Max: {config.get('tasks.max', 'N/A')}")
                        self.stdout.write(f"   Auto Create: {config.get('auto.create', 'N/A')}")
                        self.stdout.write(f"   Insert Mode: {config.get('insert.mode', 'N/A')}")
                        self.stdout.write(f"   Delete Enabled: {config.get('delete.enabled', 'N/A')}")  # DELETE 이벤트 처리 여부
                        self.stdout.write(f"   Delete Mode: {config.get('delete.mode', 'N/A')}")
                        self.stdout.write(f"   Batch Size: {config.get('batch.size', 'N/A')}")
                        self.stdout.write(f"   Max Retries: {config.get('max.retries', 'N/A')}")
                        self.stdout.write(f"   Errors Tolerance: {config.get('errors.tolerance', 'N/A')}")
                    else:
                        self.stdout.write(self.style.WARNING(f"   ⚠ 설정을 가져올 수 없습니다 (HTTP {response.status_code})"))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"   ⚠ 설정 확인 중 오류: {e}"))

                # 5. DELETE 이벤트 처리 확인
                delete_enabled = config.get('delete.enabled', 'false').lower() == 'true'
                if not delete_enabled:
                    if 'issues' not in locals():
                        issues = []
                    if 'suggestions' not in locals():
                        suggestions = []
                    issues.append("DELETE 이벤트 처리가 비활성화되어 있습니다")
                    suggestions.append("⚠️ DELETE 이벤트를 처리하려면 'delete.enabled=true' 설정을 추가하세요")
                    suggestions.append(f"설정 업데이트: curl -X PUT {connect_url}/connectors/{connector_name}/config -H 'Content-Type: application/json' -d '{{\"delete.enabled\": \"true\", \"delete.mode\": \"delete\"}}'")

                # 6. 문제 진단 및 해결 제안
                self.stdout.write(f"\n6. 문제 진단 및 해결 제안...")
                if 'issues' not in locals():
                    issues = []
                if 'suggestions' not in locals():
                    suggestions = []

                if connector_state == 'FAILED':
                    issues.append("커넥터가 실패 상태입니다")
                    suggestions.append("커넥터를 재시작하세요: curl -X POST {}/connectors/{}/restart".format(connect_url, connector_name))

                if failed_tasks:
                    issues.append(f"{len(failed_tasks)}개의 Task가 실패했습니다")
                    for task in failed_tasks:
                        trace = task.get('trace', '').lower()
                        trace_original = task.get('trace', '')
                        
                        # 스키마 진화 실패 감지 (가장 흔한 문제)
                        if 'cannot alter table' in trace and ('not optional but has no default value' in trace or 'is not optional but has no default value' in trace):
                            suggestions.append("⚠️ 스키마 진화 실패: NOT NULL이고 기본값이 없는 필드 추가 시도. auto.evolve=false로 설정하거나 PostgreSQL에서 해당 필드를 NULL 허용/기본값 설정하세요.")
                            suggestions.append(f"빠른 해결: curl -X PUT {connect_url}/connectors/{connector_name}/config -H 'Content-Type: application/json' -d '{{\"auto.evolve\": \"false\"}}' && curl -X POST {connect_url}/connectors/{connector_name}/tasks/{task.get('id', 0)}/restart")
                        elif 'connection' in trace or 'timeout' in trace:
                            suggestions.append("PostgreSQL 연결 문제가 있습니다. 연결 정보와 네트워크를 확인하세요.")
                        elif 'schema' in trace or 'column' in trace:
                            suggestions.append("스키마 불일치 문제가 있습니다. auto.create=true 또는 auto.evolve=true 설정을 확인하세요.")
                        elif 'memory' in trace or 'oom' in trace:
                            suggestions.append("메모리 부족 문제가 있습니다. batch.size를 줄이거나 JVM 메모리를 늘리세요.")
                        elif 'deadlock' in trace or 'lock' in trace:
                            suggestions.append("데드락 문제가 있습니다. max.retries와 retry.backoff.ms를 조정하세요.")
                        else:
                            suggestions.append("Task를 재시작하세요: curl -X POST {}/connectors/{}/tasks/{}/restart".format(
                                connect_url, connector_name, task.get('id', 0)))

                if not issues:
                    self.stdout.write(self.style.SUCCESS("   ✓ 문제가 발견되지 않았습니다"))
                else:
                    self.stdout.write(self.style.WARNING(f"   발견된 문제: {len(issues)}개"))
                    for issue in issues:
                        self.stdout.write(f"   - {issue}")
                    
                    if suggestions:
                        self.stdout.write(f"\n   해결 제안:")
                        for i, suggestion in enumerate(set(suggestions), 1):
                            self.stdout.write(f"   {i}. {suggestion}")

                # 7. 자동 수정 시도
                if auto_fix and (connector_state == 'FAILED' or failed_tasks):
                    self.stdout.write(f"\n6. 자동 수정 시도 중...")
                    if connector_state == 'FAILED':
                        try:
                            response = requests.post(f"{connect_url}/connectors/{connector_name}/restart", timeout=10)
                            if response.status_code == 204:
                                self.stdout.write(self.style.SUCCESS("   ✓ 커넥터 재시작 성공"))
                            else:
                                self.stdout.write(self.style.WARNING(f"   ⚠ 재시작 실패 (HTTP {response.status_code})"))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"   ✗ 재시작 중 오류: {e}"))
                    
                    for task in failed_tasks:
                        task_id = task.get('id', 0)
                        try:
                            response = requests.post(f"{connect_url}/connectors/{connector_name}/tasks/{task_id}/restart", timeout=10)
                            if response.status_code == 204:
                                self.stdout.write(self.style.SUCCESS(f"   ✓ Task {task_id} 재시작 성공"))
                            else:
                                self.stdout.write(self.style.WARNING(f"   ⚠ Task {task_id} 재시작 실패 (HTTP {response.status_code})"))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"   ✗ Task {task_id} 재시작 중 오류: {e}"))

            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f"   ✗ 상태 확인 중 오류: {e}"))

            self.stdout.write(f"\n=== 진단 완료 ===\n")
            self.stdout.write("자세한 해결 방법은 docs/postgresql_sink_troubleshooting.md를 참조하세요.\n")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n오류 발생: {str(e)}"))
            import traceback
            self.stdout.write(traceback.format_exc())
            raise












