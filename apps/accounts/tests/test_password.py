from apps.accounts.domain.password import generate_activation_code, hash_code, verify_code


def test_generate_activation_code():
    code = generate_activation_code()
    assert len(code) == 8
    assert code.isalnum()
    assert code.isupper()


def test_hash_code():
    code = "ABCD1234"
    hashed = hash_code(code)
    assert hashed != code
    assert len(hashed) > 20


def test_verify_code_correct():
    code = "ABCD1234"
    hashed = hash_code(code)
    assert verify_code(code, hashed) is True


def test_verify_code_incorrect():
    code = "ABCD1234"
    hashed = hash_code(code)
    assert verify_code("WRONG123", hashed) is False
