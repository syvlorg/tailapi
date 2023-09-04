from autoslot import Slots
from functools import partial
from ipaddress import ip_address

from .group import Group
from .object import Object


class IPPort(Slots):
    def __init__(self, ipport=None, ip=None, port=None):
        if ipport:
            ip_port = ipport.rsplit(":", 1)
            self.ip = ip_address(ip_port[0].strip("[").strip("]"))
            self.port = ip_port[1]
        else:
            self.ip = ip
            self.port = port

    def __rich_repr__(self):
        yield "ip", self.ip
        yield "port", self.port


class Device(Object):
    def __init__(
        self, device, api=None, auth=None, oapi=None, server=None, verbose=False
    ):
        super().__init__(
            api=api,
            auth=auth,
            oapi=oapi,
            obj=device,
            server=server,
            verbose=verbose,
        )

        self.addresses = [ip_address(ip) for ip in self.addresses]
        self.clientConnectivity.endpoints = [
            IPPort(ipport=ipport) for ipport in self.clientConnectivity.endpoints
        ]
        self._tags = self.tags

    def _get(self):
        return self._server.get(
            f'Sorry; something happened when trying to get device of id "{self._id}"!',
            f"https://api.tailscale.com/api/v2/device/{self._id}?fields=all",
        )

    def _ips(self, ipv4=False, ipv6=False, first=False):
        ips = dict()

        def inner(version):
            for ip in self.addresses:
                if ip.version == version:
                    if ips[version]:
                        ips[version].append(ip)
                    else:
                        ips[version] = [ip]

        if ipv4:
            inner(4)
        if ipv6:
            inner(6)
        if not (ipv4 or ipv6):
            for version in (4, 6):
                inner(version)
        return next(iter(ips.values()))[0] if first else {self.id: ips}

    def _delete(self, ignore_error=False):
        return self._server.delete(
            f'Sucessfully deleted device "{self.hostname}"!',
            f'Sorry; something happened when trying to delete device "{self.hostname}"!',
            f"https://api.tailscale.com/api/v2/device/{self.id}",
            ignore_error=ignore_error,
        )

    def _included(
        self,
        tags=tuple(),
        excluded_tags=tuple(),
        groups=tuple(),
        or_pt=False,
        ephemeral=False,
        not_ephemeral=False,
        reusable=False,
        not_reusable=False,
        preauthorized=False,
        not_preauthorized=False,
        **kwargs,
    ):
        tags = {("tag:" + tag) for tag in tags if not tag.startswith("tag:")}
        excluded_tags = {
            ("tag:" + tag) for tag in excluded_tags if not tag.startswith("tag:")
        }
        variables = dict(
            tags=tags,
            excluded_tags=excluded_tags,
            ephemeral=ephemeral,
            not_ephemeral=not_ephemeral,
            reusable=reusable,
            not_reusable=not_reusable,
            preauthorized=preauthorized,
            not_preauthorized=not_preauthorized,
            groups=groups,
        )
        group_partial = partial(Group, verbose=self._verbose, obj=self, **variables)
        if any(variables.values()):
            if or_pt:
                group = group_partial(delimiter="or")
                results = any(group.results())
                return any(
                    (
                        results,
                        any(tag in self._tags for tag in tags),
                        any(tag not in self._tags for tag in excluded_tags),
                    )
                )
            else:
                lst = []
                group = group_partial(delimiter="and")
                if groups:
                    lst.append(all(group.results()))
                if tags:
                    lst.append(all(tag in self._tags for tag in tags))
                if excluded_tags:
                    lst.append(all(tag not in self._tags for tag in excluded_tags))
                return all(lst)
        return True
