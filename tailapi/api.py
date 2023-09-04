from autoslot import Slots
from collections import namedtuple
from cryptography.exceptions import InvalidSignature
from cryptography.fernet import InvalidToken
from oreo import BearerAuth, password_decrypt, password_encrypt, password_encrypt_parts
from os import environ
from pathlib import Path
from requests.auth import HTTPBasicAuth


from .miscellaneous import return_json_addict

APIPath = namedtuple("APIPath", "dir key")


class API(Slots):
    def __init__(
        self,
        auth=environ.get("TAILSCALE_ATK", environ.get("DEFAULT_TAILSCALE_ATK", None)),
    ):
        if isinstance(auth, (str, bytes, bytearray)):
            self.key = auth
            if "-client-" in self.key:
                self.auth = BearerAuth(self.key)
                self.oauth = True
            else:
                self.auth = HTTPBasicAuth(self.key, "")
        else:
            self.auth = auth
            if isinstance(auth, HTTPBasicAuth):
                self.key = self.auth.username.decode()
            elif isinstance(auth, BearerAuth):
                self.key = self.auth.token.decode()
                self.oauth = True
        if self.key:
            key_id = self.key.split("-")[2]
            if self.oauth:
                self.oauth_id = key_id
                self.api_id = None
            else:
                self.api_id = key_id
            self.salt = self.key.split("-")[-1][:16].encode()
            self.encrypted = password_encrypt_parts(
                self.key,
                self.key,
                salt=self.salt,
                iv=self.salt,
            ).decode()
            self.path = APIPath(
                path := Path.home()
                / ".local"
                / "share"
                / "tailapi"
                / self.encrypted[int(len(self.encrypted) / 2) :],
                key=path / "key",
            )

    def __getattr__(self, attr):
        return None

    def __bool__(self):
        return bool(self.key)

    def create(self):
        return return_json_addict(
            "post",
            "Sorry; something happened when trying to create a temporary api key!",
            "https://api.tailscale.com/api/v2/oauth/token",
            data=dict(
                client_id=self.oauth_id,
                client_secret=self.key,
            ),
        ).access_token

    def write(self):
        api_key = self.create()
        self.path.dir.mkdir(parents=True, exist_ok=True)
        self.path.key.touch(exist_ok=True)
        self.path.key.write_bytes(password_encrypt(api_key, self.key))
        return api_key

    def decrypt(self):
        return password_decrypt(self.path.key.read_bytes(), self.key)

    def wrap(self, write=None, decrypt=False):
        return HTTPBasicAuth(
            self.decrypt() if decrypt else self.write() if write else self.create(), ""
        )

    def get(self):
        if self.oauth:
            if self.path.key.exists() and (self.path.key.stat().st_size != 0):
                try:
                    api_key = self.wrap(decrypt=True)
                    return_json_addict(
                        "get",
                        "",
                        f"https://api.tailscale.com/api/v2/tailnet/-/devices",
                        auth=api_key,
                    )
                except (ValueError, InvalidSignature, InvalidToken):
                    api_key = self.wrap(write=True)
            else:
                api_key = self.wrap(write=True)
            self.api_id = api_key.username.split("-")[2]
            return api_key
        else:
            return self.auth
