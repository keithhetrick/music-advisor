from advisor_host.auth.auth import AuthError
from advisor_host.auth.providers import NoAuthProvider, StaticBearerAuthProvider


def test_static_bearer_provider():
    provider = StaticBearerAuthProvider("secret")
    ctx = provider.verify({"Authorization": "Bearer secret"})
    assert ctx.user_id == "static_token_user"
    try:
        provider.verify({"Authorization": "Bearer wrong"})
        raise AssertionError("expected auth error")
    except AuthError:
        pass


def test_no_auth_provider():
    provider = NoAuthProvider()
    ctx = provider.verify({})
    assert ctx.user_id is None
