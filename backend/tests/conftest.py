import os
import tempfile

import pytest

from app import create_app
from app.extensions import db
from app.models import User

TEST_DB = os.getenv("TEST_DATABASE_URL",
                    "mysql+pymysql://sms_user:sms_password@127.0.0.1:3306/tucode_sms_test?charset=utf8mb4")


@pytest.fixture(scope="session")
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": TEST_DB, "ENABLE_SCHEDULER": False,
                      "UPLOAD_FOLDER": tempfile.mkdtemp(), "FRONTEND_URL": "http://test"})
    with app.app_context():
        db.drop_all()
        db.create_all()
        for email, role in (("admin@test.com", "admin"), ("trainer@test.com", "trainer"), ("trainer2@test.com", "trainer")):
            u = User(name=email.split("@")[0].title(), email=email, role=role)
            u.set_password("Password1!")
            db.session.add(u)
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email):
    r = client.post("/api/auth/login", json={"email": email, "password": "Password1!"})
    assert r.status_code == 200, r.get_json()
    return {"Authorization": "Bearer " + r.get_json()["token"]}


@pytest.fixture(scope="session")
def admin_h(app):
    return login(app.test_client(), "admin@test.com")


@pytest.fixture(scope="session")
def trainer_h(app):
    return login(app.test_client(), "trainer@test.com")


@pytest.fixture(scope="session")
def trainer2_h(app):
    return login(app.test_client(), "trainer2@test.com")
