from oreo import mark_apod
from os import environ
from pytest import fixture
from tailapi import Tailnet
from valiant import SH

oapi = environ.get(
    "TEST_TAILSCALE_ATK", SH._run(environ.get("TEST_TAILSCALE_ATK_COMMAND"))
)


@fixture
def tailnet(scope="session"):
    return Tailnet(oapi=oapi)


@fixture
def tags(scope="session"):
    return dict(tags=[environ.get("TEST_TAILSCALE_TAG", "tag:example")])


@fixture(params=mark_apod(("ephemeral", "preauthorized", "reusable"), (True, False)))
def options(request):
    return request.param


def pytest_ignore_collect(collection_path, config):
    if not oapi:
        return True
