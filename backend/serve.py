"""Production WSGI entrypoint, shared by Windows and Linux."""
import os
from app import create_app


def main():
    from waitress import serve
    app = create_app(os.getenv('FLASK_CONFIG', 'production'))
    with app.test_client() as client:
        if client.get('/health/ready').status_code != 200:
            raise SystemExit('服务未就绪，请检查生产配置与数据库迁移')
    if app.config.get('AI_WORKER_ENABLED'):
        raise SystemExit('WSGI 服务禁止内嵌 Worker，请单独启动 worker.py')
    serve(app, host=os.getenv('BIND_HOST', '127.0.0.1'), port=int(os.getenv('PORT', '8000')),
          threads=int(os.getenv('WSGI_THREADS', '8')), max_request_body_size=app.config['MAX_CONTENT_LENGTH'])


if __name__ == '__main__':
    main()
