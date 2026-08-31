# ============================================================
# 智绘锡承 - User 数据模型测试
# ============================================================
import pytest


@pytest.fixture
def app():
    """创建测试应用（SQLite 内存库，无需 MySQL）"""
    from app import create_app

    app = create_app('testing')
    return app


@pytest.fixture
def db(app):
    """初始化数据库表"""
    from app.extensions import db

    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()


class TestUserModel:
    """User 模型测试（规范 5.1）"""

    def test_create_user(self, app, db):
        """创建用户 + 密码哈希"""
        from app.models.user import User

        with app.app_context():
            user = User(username='testuser', email='test@example.com', password='password123')
            db.session.add(user)
            db.session.commit()

            assert user.id is not None
            assert user.username == 'testuser'
            assert user.email == 'test@example.com'
            # 密码必须存储为哈希，绝不存明文
            assert user.password_hash != 'password123'
            assert user.password_hash.startswith(('scrypt:', 'pbkdf2:'))

    def test_password_verify(self, app, db):
        """密码验证方法"""
        from app.models.user import User

        with app.app_context():
            user = User(username='pwuser', email='pw@example.com', password='secret123')
            db.session.add(user)
            db.session.commit()

            assert user.check_password('secret123') is True
            assert user.check_password('wrongpass') is False

    def test_to_dict_no_password_hash(self, app, db):
        """序列化绝不返回 password_hash"""
        from app.models.user import User

        with app.app_context():
            user = User(username='dictuser', email='dict@example.com', password='secret123')
            db.session.add(user)
            db.session.commit()

            data = user.to_dict(include_sensitive=True)
            assert 'password_hash' not in data
            assert data['username'] == 'dictuser'
            assert data['email'] == 'dict@example.com'
            assert 'created_at' in data

    def test_username_unique(self, app, db):
        """username 唯一约束"""
        from app.models.user import User
        from sqlalchemy.exc import IntegrityError

        with app.app_context():
            db.session.add(User(username='same', email='a@example.com', password='pass123'))
            db.session.commit()
            db.session.add(User(username='same', email='b@example.com', password='pass123'))
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_email_unique(self, app, db):
        """email 唯一约束"""
        from app.models.user import User
        from sqlalchemy.exc import IntegrityError

        with app.app_context():
            db.session.add(User(username='u1', email='dup@example.com', password='pass123'))
            db.session.commit()
            db.session.add(User(username='u2', email='dup@example.com', password='pass123'))
            with pytest.raises(IntegrityError):
                db.session.commit()
            db.session.rollback()

    def test_user_profile_relation(self, app, db):
        """UserProfile 与 User 一对一关系"""
        from app.models.user import User, UserProfile

        with app.app_context():
            user = User(username='profileuser', email='profile@example.com', password='pass123')
            user.profile = UserProfile(github_url='https://github.com/testuser', theme='dark')
            db.session.add(user)
            db.session.commit()

            assert user.profile.github_url == 'https://github.com/testuser'
            assert user.profile.theme == 'dark'
            assert UserProfile.query.filter_by(user_id=user.id).one().user.username == 'profileuser'
