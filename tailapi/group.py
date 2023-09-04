import ast

from more_itertools import collapse, intersperse
from oreo import Multi
from rich import print
from rich.pretty import pprint

from .transformer import Transformer


class Group:
    def __init__(
        self,
        delimiter="",
        dk=None,
        ephemeral=False,
        excluded_tags=tuple(),
        groups=None,
        not_ephemeral=False,
        not_preauthorized=False,
        not_reusable=False,
        preauthorized=False,
        reusable=False,
        tags=tuple(),
        is_key=False,
        obj=None,
        verbose=False,
    ):
        self.delimiter = delimiter
        self.dk = dk
        self.ephemeral = ephemeral
        self.excluded_tags = excluded_tags
        self.original_groups = groups
        self.groups = self.replace_all(self.original_groups)
        self.not_ephemeral = not_ephemeral
        self.not_preauthorized = not_preauthorized
        self.not_reusable = not_reusable
        self.preauthorized = preauthorized
        self.reusable = reusable
        self.tags = tags
        self.obj = obj
        self.is_key = is_key
        self.verbose = verbose
        self.properties = ("ephemeral", "preauthorized", "reusable")
        self.not_properties = tuple(("not_" + p) for p in self.properties)

    def _replace(self, pt):
        if pt.startswith("tag:"):
            spt = pt in self.obj._tags
        elif pt.startswith("!tag:"):
            spt = pt not in self.obj._tags
        else:
            if self.is_key:
                match pt:
                    case "ephemeral":
                        spt = self.obj._ephemeral
                    case "reusable":
                        spt = self.obj._reusable
                    case "preauthorized":
                        spt = self.obj._preauthorized
                    case "!ephemeral":
                        spt = not self.obj._ephemeral
                    case "!reusable":
                        spt = not self.obj._reusable
                    case "!preauthorized":
                        spt = not self.obj._preauthorized
                    case _:
                        spt = pt
            else:
                match pt:
                    case "!":
                        spt = "not"
                    case "&" | "&&":
                        spt = "and"
                    case "|" | "||":
                        spt = "or"
                    case _:
                        spt = pt
        return str(spt)

    # Adapted From:
    # Answer: https://stackoverflow.com/a/18178379/10827766
    # User: https://stackoverflow.com/users/918959/antti-haapala-%d0%a1%d0%bb%d0%b0%d0%b2%d0%b0-%d0%a3%d0%ba%d1%80%d0%b0%d1%97%d0%bd%d1%96

    def eval(self, group):
        source = (
            group if isinstance(group, (str, bytes, bytearray)) else " ".join(group)
        )
        tree = ast.parse(source, mode="eval")
        transformer = Transformer()
        transformer.visit(tree)
        clause = compile(tree, "<AST>", "eval")
        return eval(clause)

    def replace(self, group):
        def i1():
            properties = (
                str(self.obj.capabilities.devices.create.get(p))
                for p in self.properties
                if getattr(self, p)
            )
            not_properties = (
                str(not self.obj.capabilities.devices.create.get(p))
                for p in self.not_properties
                if getattr(self, p)
            )
            tags = []
            if self.tags:
                tags.append(str(all(tag in self.obj._tags for tag in self.tags)))
            if self.excluded_tags:
                tags.append(
                    str(all(tag not in self.obj._tags) for tag in self.excluded_tags)
                )
            return collapse(properties, not_properties, tags)

        def i2():
            tags = []
            if self.tags:
                tags.append(str(all(tag in self.obj._tags for tag in self.tags)))
            if self.excluded_tags:
                tags.append(
                    str(all(tag not in self.obj._tags for tag in self.excluded_tags))
                )
            return tags

        pts = list(intersperse(self.delimiter, i1() if self.is_key else i2()))
        return collapse(
            (
                pts,
                (self.delimiter,) if pts else tuple(),
                map(self._replace, Multi(group).partition("(", ")")),
            )
        )

    def replace_all(self, groups):
        return [self.replace(group) for group in groups]

    def _results(self):
        results = []
        if self.verbose:
            dks = "key" if self.is_key else "device"
            of_id = "of id " if self.dk.isnumeric() else ""
            print(
                f'Group String{"" if len(self.groups) == 1 else "s"} for {dks} {of_id}"{self.dk}":'
            )
        for ogroup, group in zip(self.original_groups, self.groups):
            if self.verbose:
                group = list(group)
                togroup = ""
                for p in self.properties:
                    if getattr(self, p):
                        togroup += f"{p} {self.delimiter} "
                for tag in self.tags:
                    togroup += f"{tag} {self.delimiter} "
                for p in self.not_properties:
                    if getattr(self, p):
                        togroup += f"{p} {self.delimiter} "
                for tag in self.excluded_tags:
                    togroup += f"!{tag} {self.delimiter} "
                togroup += ogroup
                togroup = togroup.replace("not_", "!")
                print(togroup)
                results.append(self.eval(group))
        return results

    def results(self):
        if self.is_key:
            if self.values.capabilities:
                yield from self._results()
        else:
            yield from self._results()
