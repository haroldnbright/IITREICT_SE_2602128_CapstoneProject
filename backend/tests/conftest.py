import os
import sys
import tempfile
from pathlib import Path

# Use a throwaway database and settings for tests (must be set before the app is imported)
_db_file = Path(tempfile.mkdtemp()) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"
os.environ["JWT_SECRET_KEY"] = "test-secret-that-is-long-enough-for-hs256"
os.environ["OPENAI_API_KEY"] = ""
os.environ["SEED_DEMO_DATA"] = "true"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def login(client, email, password="password123"):
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def customer(client):
    return login(client, "customer@campusbite.com")


@pytest.fixture(scope="session")
def customer2(client):
    return login(client, "customer2@campusbite.com")


@pytest.fixture(scope="session")
def owner(client):
    return login(client, "owner1@campusbite.com")


@pytest.fixture(scope="session")
def owner2(client):
    return login(client, "owner2@campusbite.com")


@pytest.fixture(scope="session")
def delivery(client):
    return login(client, "delivery1@campusbite.com")


@pytest.fixture(scope="session")
def delivery2(client):
    return login(client, "delivery2@campusbite.com")
