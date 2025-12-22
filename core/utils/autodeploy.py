"""
운영 배포 편의 기능

- 목적: 서버에서 `git pull` 후 `systemctl restart cynow`만으로도
        마이그레이션/정적파일 수집이 자동으로 반영되도록 지원한다.
- 주의: 운영 환경(DEBUG=False) + systemd 실행 환경에서만 동작하도록 제한한다.
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import contextmanager


def _log(msg: str) -> None:
    sys.stderr.write(f"[cynow-autodeploy] {msg}\n")
    sys.stderr.flush()


@contextmanager
def _file_lock(lock_path: str, timeout_sec: int = 180):
    """
    단순 파일 락 (Linux에서만 동작: fcntl 기반)
    - gunicorn multi-worker에서 중복 실행을 방지한다.
    """
    try:
        import fcntl  # type: ignore
    except Exception:
        # Windows/환경 미지원 시 락 없이 진행 (개발 환경에서는 기본적으로 호출되지 않음)
        yield
        return

    os.makedirs(os.path.dirname(lock_path), exist_ok=True)
    with open(lock_path, "w", encoding="utf-8") as f:
        start = time.time()
        while True:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.time() - start > timeout_sec:
                    _log(f"lock timeout: {lock_path} (skip)")
                    yield
                    return
                time.sleep(0.2)
        try:
            yield
        finally:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass


def run_autodeploy_if_needed(*, base_dir: str, debug: bool) -> None:
    """
    운영 환경에서만 자동 배포 작업 수행
    - migrate: 적용할 마이그레이션이 있을 때만 실행
    - collectstatic: 운영에서는 항상 실행(안전)하되, 락으로 1회만 수행
    """
    if debug:
        return

    # systemd 서비스에서만 동작 (local/dev 서버 부작용 방지)
    if not os.environ.get("INVOCATION_ID"):
        return

    # 긴급 비활성화 스위치
    if os.environ.get("CYNOW_DISABLE_AUTODEPLOY") == "1":
        return

    lock_path = os.path.join(base_dir, ".run", "autodeploy.lock")

    with _file_lock(lock_path):
        try:
            from django.core.management import call_command
            from django.db import connections
            from django.db.migrations.executor import MigrationExecutor
        except Exception as e:
            _log(f"import error: {e}")
            return

        # 1) migrate (필요할 때만)
        try:
            connection = connections["default"]
            executor = MigrationExecutor(connection)
            targets = executor.loader.graph.leaf_nodes()
            plan = executor.migration_plan(targets)
            if plan:
                _log(f"apply migrations: {len(plan)}")
                call_command("migrate", interactive=False, verbosity=1)
            else:
                _log("no pending migrations")
        except Exception as e:
            _log(f"migrate failed: {e}")
            # migrate 실패 시에는 서비스가 뜨더라도 상태가 꼬일 수 있으니 여기서 중단
            return

        # 2) collectstatic (운영에서 정적 파일 누락 방지)
        try:
            _log("collectstatic")
            call_command("collectstatic", interactive=False, verbosity=0, clear=False, noinput=True)
        except TypeError:
            # Django 버전/옵션 호환성 fallback
            try:
                call_command("collectstatic", interactive=False, verbosity=0, clear=False)
            except Exception as e:
                _log(f"collectstatic failed: {e}")
        except Exception as e:
            _log(f"collectstatic failed: {e}")


