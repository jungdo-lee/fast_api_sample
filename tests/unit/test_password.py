from app.core.security import hash_password, verify_password


def test_hash_password_returns_hash():
    hashed = hash_password("TestPass123!")
    assert hashed != "TestPass123!"
    assert hashed.startswith("$2b$")


def test_verify_password_correct():
    hashed = hash_password("TestPass123!")
    assert verify_password("TestPass123!", hashed) is True


def test_verify_password_incorrect():
    hashed = hash_password("TestPass123!")
    assert verify_password("WrongPass456!", hashed) is False
