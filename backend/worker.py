"""Standalone worker protected by a process lock on this host."""
import os
from pathlib import Path
from app import create_app
from app.workers.ai_task_worker import start


def acquire_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open('a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            if path.stat().st_size == 0:
                handle.write(b'0'); handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        raise RuntimeError('本机已有 Worker 持有锁，拒绝重复启动')
    return handle


def main():
    app = create_app(os.getenv('FLASK_CONFIG', 'production'))
    lock_path = Path(os.getenv('AI_WORKER_LOCK_FILE', str(Path(__file__).parent / '.runtime/worker.lock')))
    with acquire_lock(lock_path):
        start(app.config['AI_WORKER_INTERVAL_SECONDS'], app)


if __name__ == '__main__':
    main()
