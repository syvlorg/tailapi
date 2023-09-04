import json

from contextlib import contextmanager
from rich import print_json

from .object import Object


class Policy(Object):
    __slots__ = ("_headers",)

    def __init__(
        self, api=None, auth=None, oapi=None, policy=None, server=None, verbose=False
    ):
        super().__init__(
            api=api,
            auth=auth,
            oapi=oapi,
            obj=policy,
            server=server,
            verbose=verbose,
        )
        self._policy_file = self._server.api.path.dir / "policy.json"

    def __eq__(self, other):
        return self._obj == other

    def _get(self):
        response = self._server.get(
            "Sorry; something happened when trying to get the policy file!",
            "https://api.tailscale.com/api/v2/tailnet/-/acl",
            include_headers=True,
            headers=dict(Accept="application/json"),
        )
        self._headers = response.headers
        return response.data

    def _update(self):
        return self._server.post(
            "Sorry; something happened when trying to update the policy file!",
            "https://api.tailscale.com/api/v2/tailnet/-/acl",
            headers=dict(Accept="application/json") | {"If-Match": self._headers.Etag},
            json=self._obj.to_dict(),
        )

    def _preview(self, user=None, ipport=None):
        return self._server.post(
            "Sorry; something happened when trying to preview the policy file!",
            f'https://api.tailscale.com/api/v2/tailnet/example.com/acl/preview?previewFor={user or ipport}&type={"user" if user else "ipport"}',
            headers=dict(Accept="application/json"),
            json=self._obj.to_dict(),
        )

    def _test(self, current=False, validate=False):
        if not current:
            self._update()
        return self._server.post(
            f'Sorry; something happened when trying to test the{" current" if current else ""} policy file!',
            "https://api.tailscale.com/api/v2/tailnet/example.com/acl/validate",
            headers=dict(Accept="application/json"),
            json=dict(acls=self.acls, tests=self.tests) if validate else self.tests,
        )

    def _write(self):
        with self._policy_file.open("w") as f:
            json.dump(self._obj, f, indent=2)

    def _read(self):
        if self._policy_file.exists():
            with self._policy_file.open() as f:
                self._obj = json.load(f)

    @contextmanager
    def _edit(self):
        self._write()
        yield self._policy_file
        self._read()
