from sqlalchemy import Engine
from src.models import User, SQLModel
import pytest
from sqlmodel import create_engine, Session


@pytest.fixture(name="engine")
def engine_fixture():
    # Create an in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    return engine


class TestUser:

    def test_user_creation(self, engine: Engine):
        # Create a test user
        user = User(username="testuser")
        with Session(engine) as session:
            session.add(user)
            session.commit()
            session.refresh(user)

        assert user.username == "testuser"
