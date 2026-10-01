from src.security import RateLimiter, UserStore, hash_key, new_api_key


def test_keys_are_unique_and_hash_is_stable():
    a, b = new_api_key(), new_api_key()
    assert a != b and a.startswith("pk_")
    assert hash_key(a) == hash_key(a) != hash_key(b)


def test_userstore_authenticates_by_hash_only():
    key = new_api_key()
    store = UserStore({"u": {"key_hash": hash_key(key), "sources": ["x.pdf"]}})
    user = store.authenticate(key)
    assert user.name == "u" and user.allowed == frozenset({"x.pdf"})
    assert store.authenticate("wrong") is None
    assert store.authenticate(hash_key(key)) is None  # the hash is not a valid key


def test_wildcard_means_all_documents():
    store = UserStore({"a": {"key_hash": hash_key("k"), "sources": ["*"]}})
    assert store.authenticate("k").allowed is None


def test_sliding_window_expires():
    rl = RateLimiter(window_seconds=60)
    assert rl.check("u", 2, now=0)[0]
    assert rl.check("u", 2, now=1)[0]
    assert not rl.check("u", 2, now=2)[0]
    assert rl.check("u", 2, now=61)[0]  # first hit left the window