import magicattr
import re

from addict import Dict
from autoslot import Slots
from operator import attrgetter
from oreo import Counter
from rich.pretty import pretty_repr

from .server import Server


class Object(Slots):
    __slots__ = ("_server", "_verbose", "_id")

    def __init__(
        self,
        api=None,
        auth=None,
        oapi=None,
        obj=None,
        server=None,
        verbose=False,
    ):
        self._kwargs = dict(
            server=server or Server(api=api, auth=auth, oapi=oapi),
            verbose=verbose,
        )
        for k, v in self._kwargs.items():
            setattr(self, "_" + k, v)
        self._id = self._kwargs["obj"] = obj

        if isinstance(obj, Dict):
            self._obj = obj
        elif isinstance(obj, dict):
            self._obj = Dict(obj)
        else:
            count = Counter(2)
            while count:
                try:
                    self._obj = self._get()
                except ValueError:
                    pass
                else:
                    break
            else:
                self._obj = self._get()

    def _deepcopy(self, func=None, options=tuple(), **kwargs):
        obj = kwargs.pop("obj", self._obj)
        kwargs = Dict(kwargs or self._kwargs)
        del kwargs["obj"]
        return self.__class__(
            {
                k: v
                for k, v in (self._filterattrs(options) if options else obj).items()
                if func(k, v)
            }
            if func
            else obj,
            **kwargs,
        )

    def __delete__(self, attr):
        del self._obj[attr]

    __delitem__ = __delete__

    def __setattr__(self, name, value):
        if name.startswith("_"):
            # Adapted From:
            # Answer: https://stackoverflow.com/a/16171796/10827766
            # User: https://stackoverflow.com/users/1196900/dhara
            object.__setattr__(self, name, value)
        else:
            self._obj[name] = value

    def __getattr__(self, attr):
        # The regex is necessary for `__rich_repr__' to work,
        # because when it uses `__getattr__' it trips up on alphanumeric hashes,
        # such as "awehoi234_wdfjwljet234_234wdfoijsdfmmnxpi492", for some reason.
        # Adapted From:
        # Answer: https://stackoverflow.com/a/19859308/10827766
        # User: https://stackoverflow.com/users/1903116/thefourtheye
        if attr.startswith("_") or re.search(r"\d", attr):
            raise AttributeError
        return getattr(self._obj, attr)

    def __setitem__(self, name, value):
        self._obj[name] = value

    def __getitem__(self, name):
        return self._obj[name]

    def __eq__(self, other):
        return self.id == (other.id if isinstance(other, Object) else other)

    # Adapted From:
    # Answer: https://stackoverflow.com/a/65355793/10827766
    # User: https://stackoverflow.com/users/442852/milo-wielondek
    def _getattr(self, *options):
        return attrgetter(options[0] if ("." in options[0]) else ".".join(options))(
            self._obj
        )

    # Adapted From:
    # Comment: https://stackoverflow.com/questions/31174295/getattr-and-setattr-on-nested-subobjects-chained-properties#comment123601436_65355793
    # User: https://stackoverflow.com/users/7938503/plagon
    def _filterattrs(self, *options):
        if options:
            new = Dict()
            for attrs in options:
                magicattr.set(
                    new,
                    attrs,
                    self._getattr(attrs),
                )
            return new
        return self._obj

    def _values(self):
        return self._obj.values()

    def _keys(self):
        return self._obj.keys()

    def __repr__(self):
        return pretty_repr(self._obj)

    def __rich_repr__(self):
        for k, v in self._obj.items():
            yield k, v
