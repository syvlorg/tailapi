from functools import partial
from rich.pretty import pprint

from .group import Group
from .object import Object

capabilities = ("ephemeral", "preauthorized", "reusable", "tags")


class Key(Object):
    __slots__ = ("_" + c for c in capabilities)

    def __init__(
        self,
        key,
        api=None,
        auth=None,
        oapi=None,
        server=None,
        verbose=False,
    ):
        super().__init__(
            api=api,
            auth=auth,
            oapi=oapi,
            obj=key,
            server=server,
            verbose=verbose,
        )

        self._api = not self.capabilities
        self._oauth = not self.expires
        for c in capabilities:
            setattr(self, "_" + c, self.capabilities.devices.create[c])

    def _get(self):
        return self._server.get(
            f'Sorry; something happened when trying to get key of id "{self._id}"!',
            f"https://api.tailscale.com/api/v2/tailnet/-/keys/{self._id}",
        )

    def _delete(self, ignore_error=False):
        if self._api:
            print("Sorry; not deleting an API key!")
            return False
        elif self._oauth:
            print("Sorry; not deleting an OAuth key!")
            return False
        else:
            return self._server.delete(
                f'Sucessfully deleted key of id "{self.id}"!',
                f'Sorry; something happened when trying to delete key of id "{self.id}"!',
                f"https://api.tailscale.com/api/v2/tailnet/-/keys/{self.id}",
                ignore_error=ignore_error,
            )

    def _include(
        self,
        api=True,
        oauth=True,
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
        tags = {tag if tag.startswith("tag:") else ("tag:" + tag) for tag in tags}
        excluded_tags = {
            tag if tag.startswith("tag:") else ("tag:" + tag) for tag in excluded_tags
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
        group_partial = partial(
            Group, verbose=self._verbose, obj=self, is_key=True, **variables
        )
        if any(variables.values()):
            if or_pt:
                group = group_partial(delimiter="or")
                results = any(group.results())
                return self.capabilities and any(
                    (
                        ephemeral and self._ephemeral,
                        not_ephemeral and not self._ephemeral,
                        preauthorized and self._preauthorized,
                        not_preauthorized and not self._preauthorized,
                        reusable and self._reusable,
                        not_reusable and not self._reusable,
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
                if ephemeral:
                    lst.append(ephemeral and self._ephemeral)
                if not_ephemeral:
                    lst.append(not_ephemeral and not self._ephemeral)
                if preauthorized:
                    lst.append(preauthorized and self._preauthorized)
                if not_preauthorized:
                    lst.append(not_preauthorized and not self._preauthorized)
                if reusable:
                    lst.append(reusable and self._reusable)
                if not_reusable:
                    lst.append(not_reusable and not self._reusable)
                if tags:
                    lst.append(all(tag in self._tags for tag in tags))
                if excluded_tags:
                    lst.append(all(tag not in self._tags for tag in excluded_tags))
                return self.capabilities and all(lst)

        # TODO
        # return not ((not api) and self._api) or ((not oauth) and self._oauth)

        # if (not api) and self._api:
        #     return False
        # if (not oauth) and self._oauth:
        #     return False

        if ((not api) and self._api) or ((not oauth) and self._oauth):
            return False
        return True
