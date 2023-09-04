from pytest import mark, xfail
from rich.pretty import pprint


@mark.create
class TestCreateDelete:
    @mark.delete
    @mark.parametrize("count", range(1, 3))
    def test_create_delete(
        self,
        tailnet,
        tags,
        count,
        options,
    ):
        options |= tags
        with tailnet.test_key(count=count, **options) as k:
            assert all(key.capabilities.devices.create == options for key in k.values())
            assert tailnet.delete(k, do_not_prompt=True)

    def test_no_tags(self, tailnet):
        if tailnet.server.api.oauth:
            xfail("Fails when using an OAuth token.")
        else:
            with tailnet.test_key() as k:
                assert k


@mark.delete
def test_delete_oapi_key(tailnet):
    assert not tailnet.delete(
        tailnet.api.oauth_id or tailnet.api.api_id, do_not_prompt=True
    )
