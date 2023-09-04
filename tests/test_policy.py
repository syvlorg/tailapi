from addict import Dict
from pytest import mark


@mark.policy
class TestPolicy:
    def test_update(self, tailnet):
        policy = Dict(tailnet.policy._obj)
        tailnet.policy.tagOwners["tag:test"] = ["autogroup:admin"]
        tailnet.policy._update()
        assert tailnet.policy._get() == tailnet.policy
        tailnet.policy._obj = policy
        tailnet.policy._update()
        assert tailnet.policy._get() == policy
