import black

from addict import Dict
from autoslot import Slots
from contextlib import contextmanager
from oreo import Counter, is_coll
from rich import print
from rich.pretty import pretty_repr, pprint
from rich.prompt import Prompt

from .api import API
from .device import Device
from .key import Key
from .object import Object
from .policy import Policy
from .server import Server


class Tailnet(Slots):
    __slots__ = ("server", "verbose")

    def __init__(
        self,
        no_fields=False,
        all_fields=False,
        api=None,
        auth=None,
        oapi=None,
        devices=None,
        dry_run=False,
        excluded=tuple(),
        keys=None,
        verbose=False,
    ):
        self.oapi = oapi
        self.api = api or API(auth or self.oapi)
        self.auth = auth or self.api.get()
        self.dry_run = dry_run

        self.kwargs = dict(
            server=Server(api=self.api, auth=self.auth, oapi=self.oapi), verbose=verbose
        )
        for k, v in self.kwargs.items():
            setattr(self, k, v)

        self.devices = Dict()
        all_devices = devices or True
        for device in self.objs("devices"):
            if (
                all_devices
                or (device["id"] in devices)
                or (device["name"] in devices)
                or (device["hostname"] in devices)
            ) and not (
                (device["id"] in excluded)
                or (device["name"] in excluded)
                or (device["hostname"] in excluded)
            ):
                device = Device(device["id"] if all_fields else device, **self.kwargs)
                self.devices[device["id"]] = device

        self.sensitive_attrs = ("key", "revoked")
        self.current_keys = (self.server.api.api_id, self.server.api.oauth_id)
        self.keys = Dict()
        for key in keys or self.objs("keys"):
            id = key if isinstance(key, (str, bytes, bytearray)) else key["id"]
            if id not in excluded:
                if no_fields:
                    key = Dict(
                        key
                        | dict(
                            _include=lambda *args, **kwargs: True,
                            # Adapted From:
                            # Answer: https://stackoverflow.com/a/7546307/10827766
                            # User: https://stackoverflow.com/users/951890/vaughn-cato
                            _delete=lambda ignore_error, id=id: self.server.delete(
                                f'Sucessfully deleted key of id "{id}"!',
                                f'Sorry; something happened when trying to delete key of id "{id}"!',
                                f"https://api.tailscale.com/api/v2/tailnet/-/keys/{id}",
                                ignore_error=ignore_error,
                            ),
                        )
                    )
                else:
                    key = Key(id, **self.kwargs)
                self.keys[id] = key

        self.policy = Policy(**self.kwargs)

    @property
    def hosts(self):
        return Dict({v["hostname"]: v for v in self.devices.values()})

    @property
    def names(self):
        return Dict({v["name"]: v for v in self.devices.values()})

    @property
    def api_keys(self):
        return self.filterattrs(api_keys=True)

    @property
    def oauth_keys(self):
        return self.filterattrs(oauth_keys=True)

    @property
    def oapi_keys(self):
        return Dict(self.api_keys | self.oauth_keys)

    @property
    def keys_no_api(self):
        api_keys = self.api_keys
        return Dict({k: v for k, v in self.keys.items() if k not in api_keys})

    @property
    def keys_no_oauth(self):
        oauth_keys = self.oauth_keys
        return Dict({k: v for k, v in self.keys.items() if k not in oauth_keys})

    @property
    def keys_no_oapi(self):
        oapi_keys = self.oapi_keys
        return Dict({k: v for k, v in self.keys.items() if k not in oapi_keys})

    @property
    def all(self):
        return Dict(self.devices | self.keys)

    @property
    def all_no_api(self):
        return Dict(self.devices | self.keys_no_api)

    @property
    def all_no_oauth(self):
        return Dict(self.devices | self.keys_no_oauth)

    @property
    def all_no_oapi(self):
        return Dict(self.devices | self.keys_no_oapi)

    def objs(self, type):
        return self.server.get(
            f"Sorry; something happened when trying to get all {type}!",
            f"https://api.tailscale.com/api/v2/tailnet/-/{type}?fields=all",
        )[type]

    def ips(self, ipv4=False, ipv6=False, first=False):
        _ips = (
            d._ips(ipv4=ipv4, ipv6=ipv6, first=first) for d in self.devices.values()
        )
        if first:
            return tuple(_ips)[0]
        else:
            return {k: v for ip in _ips for k, v in ip.items()}

    # Note that `self.all' cannot be used in `_inner',
    # as it doesn't split back into `self.devices' and `self.keys'
    def delete(
        self,
        id,
        do_not_prompt=False,
        ignore_error=False,
        **kwargs,
    ):
        def _inner(i):
            if isinstance(i, Object):
                if (i in self.all.values()) and i._delete(ignore_error=ignore_error):
                    return self.devices.pop(i.id, self.keys.pop(i.id, False))
            else:
                if isinstance(i, dict):
                    i = i.id
                if (i in self.all) and self.devices.get(i, self.keys.get(i))._delete(
                    ignore_error=ignore_error
                ):
                    return self.devices.pop(i, self.keys.pop(i, False))
            return False

        def inner(ids):
            values = self.filter(
                obj=ids, excluded=self.current_keys, api=False, oauth=False, **kwargs
            )
            print(
                f"[bold red]THIS WILL DELETE THE FOLLOWING DEVICES OR KEYS FROM YOUR TAILNET!\n"
            )
            pprint(values)
            print("\n")
            answer = "DELETE FROM TAILNET"
            answer_all = "DELETE ALL"
            if (
                values
                and (not self.dry_run)
                and (
                    do_not_prompt
                    or (
                        (
                            Prompt.ask(
                                f'[bold red]TO CONTINUE, PLEASE TYPE IN "{answer}" WITHOUT THE QUOTES'
                            )
                            == answer
                        )
                        and (
                            (
                                Prompt.ask(
                                    f'[bold red]ARE YOU SURE YOU WANT TO DELETE {"EVERYTHING" if (values == self.all_no_oapi) else "ALL KEYS" if (values == self.keys_no_oapi) else "ALL DEVICES"}? IF SO, PLEASE TYPE IN "{answer_all}" WITHOUT THE QUOTES'
                                )
                                == answer_all
                            )
                            if (
                                values
                                in (self.devices, self.keys_no_oapi, self.all_no_oapi)
                            )
                            else True
                        )
                    )
                )
            ):
                # NOTE: Don't put this directly in the `all';
                #       it will return the moment it finds a
                #       non-truthy value.
                output = [_inner(i) for i in values.values()]
                return all(output)
            return False

        if isinstance(id, Object):
            return inner({id.id: id})
        elif (id in ("all", "devices", "keys")) or is_coll(id):
            if isinstance(id, dict):
                return inner(id)
            elif is_coll(id):
                ids = dict()
                for i in id:
                    if isinstance(i, Object):
                        ids[i.id] = i
                    else:
                        ids[i] = self.devices.get(i, self.keys.get(i))
                return inner(ids)
            else:
                return inner(getattr(self, id))
        else:
            return inner({id: self.all[id]})

    def create(
        self,
        count=1,
        ephemeral=False,
        preauthorized=False,
        reusable=False,
        tags=tuple(),
    ):
        if self.api.oauth and (not tags):
            raise ValueError(
                "Sorry; at least one tag must be set when using an OAuth access token!"
            )
        data = Dict()
        data.capabilities.devices.create = dict(
            ephemeral=ephemeral,
            preauthorized=preauthorized,
            reusable=reusable,
            tags=list(
                {tag if tag.startswith("tag:") else f"tag:{tag}" for tag in tags}
            ),
        )
        formatted = black.format_file_contents(
            str(data), fast=False, mode=black.FileMode()
        )
        responses = Dict()
        count = Counter(count)
        while count:
            key = Key(
                self.server.post(
                    f'Sorry; something happened when trying to create a key with the following properties: "{formatted}"!',
                    f"https://api.tailscale.com/api/v2/tailnet/-/keys",
                    json=data,
                ),
                **self.kwargs,
            )
            responses[key.id] = key
            self.keys[key.id] = key._deepcopy(
                func=lambda k, v: k not in self.sensitive_attrs
            )
        return responses

    def filter(self, obj="all", excluded=tuple(), **kwargs):
        if isinstance(obj, (str, bytes, bytearray)):
            obj = getattr(self, obj)
        elif isinstance(obj, dict):
            pass
        elif is_coll(obj):
            obj = {id: self.all[id] for id in obj}
        else:
            pass
        return Dict(
            {
                k: v
                for k, v in obj.items()
                if (k not in excluded) and v._include(**kwargs)
            }
        )

    def filterattrs(
        self,
        obj="all",
        options=tuple(),
        api_keys=False,
        oauth_keys=False,
        **kwargs,
    ):
        if api_keys:
            attrs = {k: v for k, v in self.keys.items() if v._api}
        elif oauth_keys:
            attrs = {k: v for k, v in self.keys.items() if v._oauth}
        else:
            attrs = {
                k: v._filterattrs(options)
                for k, v in self.filter(
                    obj,
                    **kwargs,
                ).items()
            }
        return Dict(attrs)

    @contextmanager
    def test_key(self, ignore_error=False, **options):
        try:
            k = self.create(**options)
            yield k
        finally:
            self.delete(k, do_not_prompt=True, ignore_error=ignore_error)

    def __repr__(self):
        return pretty_repr(
            dict(
                devices={k: v._obj for k, v in self.devices.items()},
                keys={k: v._obj for k, v in self.keys.items()},
                policy=self.policy._policy,
            )
        )

    def __rich_repr__(self):
        yield self.policy
        yield "Devices", self.devices
        yield "Keys", self.keys
