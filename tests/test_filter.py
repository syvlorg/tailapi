from addict import Dict
from collections import namedtuple
from pytest import mark, fixture
from rich.pretty import pprint

KeyOps = namedtuple("KeyOps", "key options")


@mark.filter
class TestFilter:
    @fixture
    def key(self, tailnet, tags, options):
        with tailnet.test_key(**(options := options | tags)) as key:
            key = next(iter(key.values()))
            for attr in tailnet.sensitive_attrs:
                key.pop(attr, None)
            yield KeyOps(key, options)

    def test_keys(self, tailnet, key):
        assert key.key == tailnet.filter(obj="keys", **key.options)[key.key.id]

    def test_attrs(self, tailnet, key):
        options = Dict()
        options.capabilities.devices.create = key.options
        assert (
            options
            == tailnet.filterattrs(
                obj="keys",
                options="capabilities.devices.create",
                **key.options,
            )[key.key.id]
        )
