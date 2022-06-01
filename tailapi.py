#!/usr/bin/env python

from addict import Dict
from ipaddress import ip_address
from more_itertools import intersperse
from os import environ
from os.path import exists
from pathlib import Path
from requests.auth import HTTPBasicAuth
from rich import print
from rich.pretty import pprint
from sys import exit
import ast
import click
import json
import oreo
import requests

def raise_response_error(error_message, response):
    raise ValueError(error_message + " Response reason: " + response.reason)

def return_json_addict(action, error_message, *args, **kwargs):
    if (response := getattr(requests, action)(*args, **kwargs)).status_code == 200:
        return Dict(json.loads(response.text))
    else:
        raise_response_error(error_message, response)

class dk:
    def __init__(self, auth, recreate_response, values, excluded):
        self.auth = auth
        self.recreate_response = recreate_response
        self.values = list(values) or [ "all" ]
        self.all_responses = dict()
        self.empty = bool(self.values)
        self.excluded = excluded

    def get_response(self, url, error_message):
        return return_json_addict("get", error_message, url, auth = self.auth)

    def _write(self, response_file, response_dict):
        response_path = Path(response_file)
        response_dir = Path(response_path.parent)
        response_dir.mkdir(parents = True, exist_ok = True)
        with open(response_file, "w") as f:
            json.dump(response_dict, f)
        return response_dict

    def get(self, response_file, all_override = False, recreate_override = False):
        if self.recreate_response or recreate_override:
            responses = self.write(all_override = all_override)
        elif exists(response_file):
            with open(response_file) as f:
                responses = Dict(json.load(f))
        else:
            responses = self.write(all_override = all_override)
        for dk in self.excluded:
            if dk.isnumeric():
                for k, v in responses.items():
                    if dk == v.id:
                        del responses[k]
            else:
                del responses[dk]
        return responses

    def get_all(self, all_override = False, recreate_override = False):
        if self.all or all_override:
            return self.get(self.default_response_file, all_override = all_override, recreate_override = recreate_override)
        else:
            all_responses = Dict(dict())
            for file in self.response_files:
                all_responses.update(self.get(file))
            return all_responses

    def print(self):
        pprint(self.get_all())

    def create_response_file_path(self, dk, value):
        return f"{environ['HOME']}/.local/share/tailapi/{dk}/{value}.json"

    def create_response_file_paths(self, dk, values):
        return [ self.create_response_file_path(dk, _) for _ in values ]

    def _delete(self, url, success_message, error_message):
        if (response := requests.delete(url, auth = self.auth)).status_code == 200:
            print(success_message)
        else:
            raise_response_error(error_message, response)

    def delete_all(self, values = None):
        try:
            for dk in (values or self.get_all()):
                if self.delete(dk):
                    self.values.remove(dk)
                    self.response_files.remove(self.mapped.pop(dk))
        finally:
            self.write()
            if not self.all:
                self.write(all_override = True)

class device_class(dk):
    def __init__(self, recreate_response, response_files, auth, values, domain, excluded):
        super().__init__(values = values, auth = auth, recreate_response = recreate_response, excluded = excluded)
        self.all = (not values) or ("all" in values)
        self.default_response_file = f"{environ['HOME']}/.local/share/tailapi/devices.json"
        self.domain = domain
        self.response_files = response_files or self.create_response_file_paths("devices", self.values)
        self.mapped = Dict(dict(zip(self.values, self.response_files, strict = True)))

    def write(self, all_override = False):
        if self.all or all_override:
            all_responses = Dict({
                device["name"].split(".")[0] : device for device in self.get_response(
                    f"https://api.tailscale.com/api/v2/tailnet/{self.domain}/devices?fields=all",
                    f'Sorry; something happened when trying to get all devices!',
                )["devices"]
            })
            self._write(self.default_response_file, all_responses)
        else:
            all_responses = Dict(dict())
            for device, file in self.mapped.items():
                if device.isnumeric():
                    response = self.get_response(
                        f"https://api.tailscale.com/api/v2/device/{device}?fields=all",
                        f'Sorry; something happened when trying to get device of id "{device}"!',
                    )
                    all_responses.update(self._write(file, { response["name"].split(".")[0] : response }))
                else:
                    self.all_responses = self.all_responses or self.get_all(all_override = True)
                    all_responses.update(self._write(file, { device : self.all_responses[device] }))
        return all_responses

    def delete(self, device):
        if device.isnumeric():
            id = device
            of_id = "of id "
        else:
            self.all_responses = self.all_responses or self.get_all(all_override = True, recreate_override = True)
            id = self.all_responses[device].id
            of_id = ""
        self._delete(
            f"https://api.tailscale.com/api/v2/device/{id}",
            f'Sucessfully deleted device {of_id}"{device}"!',
            f'Sorry; something happened when trying to delete device {of_id}"{device}"!',
        )
        return True

class key_class(dk):
    def __init__(self, values, response_files, auth, recreate_response, domain, excluded):
        super().__init__(values = values, auth = auth, recreate_response = recreate_response, excluded = excluded)
        self.all = "all" in values
        self.default_response_file = f"{environ['HOME']}/.local/share/tailapi/keys.json"
        self.domain = domain
        self.response_files = response_files or self.create_response_file_paths("keys", self.values)
        self.mapped = Dict(dict(zip(self.values, self.response_files, strict = True)))

    def create_url(self, key):
        return f"https://api.tailscale.com/api/v2/tailnet/{self.domain}/keys/{key}"

    def write(self, all_override = False):
        all_responses = Dict(dict())
        if self.all or all_override:
            for key in self.get_response(
                f"https://api.tailscale.com/api/v2/tailnet/{self.domain}/keys",
                f'Sorry; something happened when trying to get all keys!'
            )["keys"]:
                all_responses[key["id"]] = self.get_response(
                    self.create_url(key["id"]),
                    f'Sorry; something happened when trying to get key of id "{key}"!',
                )
            self._write(self.default_response_file, all_responses)
        else:
            for key, file in self.mapped.items():
                response = self.get_response(
                    self.create_url(key),
                    f'Sorry; something happened when trying to get key of id "{key}"!',
                )
                all_responses.update(self._write(file, { response["id"] : response }))
        return all_responses

    def delete(self, key):
        if key in self.get_api_keys():
            print("Sorry; not deleting an API key!")
            return False
        else:
            self._delete(
                f"https://api.tailscale.com/api/v2/tailnet/{self.domain}/keys/{key}",
                f'Sucessfully deleted key of id "{key}"!',
                f'Sorry; something happened when trying to delete key of id "{key}"!',
            )
            return True

    def create_key(self, data, just_key):
        response = return_json_addict(
            "post",
            f'Sorry; something happened when trying to create a key with the following properties: "{data}"!',
            f"https://api.tailscale.com/api/v2/tailnet/{self.domain}/keys",
            json = data,
            auth = self.auth,
        )
        if just_key:
            print(response.key)
        else:
            pprint(response)

    def get_api_keys(self, verbose = False):
        if verbose:
            return { k : v for k, v in self.get_all(all_override = True).items() if not v.capabilities }
        else:
            return [ k for k, v in self.get_all(all_override = True).items() if not v.capabilities ]

@click.group(no_args_is_help = True)
@click.option("-a", '--api-key', default = environ.get("TAILSCALE_APIKEY", default = None))
@click.option(
    "-d",
    '--devices',
    cls = oreo.Option,
    help = """The device name or id; input `all' to show all devices, or specify multiple times for multiple devices.
Every index here matches to the same index in `--device-response-files', while a value of `all' uses a single file.
If no device response files are given, the device names are used for all specified devices.""",
    multiple = True,
    xor = [ "keys" ],
)
@click.option("-D", '--domain', required = True)
@click.option(
    "-k",
    "--keys",
    cls = oreo.Option,
    help = """The key id; input `all' to show all keys, or specify multiple times for multiple keys.
Every index here matches to the same index in `--key-response-files', while a value of `all' uses a single file.
If no key response files are given, the key ids' are used for all specified keys.""",
    multiple = True,
    xor = [ "devices" ],
)
@click.option(
    "-f",
    '--device-response-files',
    help = """Where the device information should be stored;
every index here matches to the same index in `--devices', while a value of `all' in `--devices' uses a single file.""",
    multiple = True,
)
@click.option(
    "-F",
    '--key-response-files',
    help = """Where the device information should be stored;
every index here matches to the same index in `--keys', while a value of `all' in `--keys' uses a single file.""",
    multiple = True,
)
@click.option("-e", "--excluded", multiple = True)
@click.option("-r", '--recreate-response', is_flag = True)
@click.option("-n", "--dry-run", is_flag = True)
@click.option("-v", "--verbose", is_flag = True)
@click.pass_context
def tailapi(ctx, api_key, domain, devices, device_response_files, key_response_files, recreate_response, keys, dry_run, verbose, excluded):
    if not api_key:
        raise click.UsageError("Sorry; you need to pass in an api key either via the `--api-key' option, or by setting the environment variable `TAILSCALE_APIKEY'!")
    ctx.ensure_object(dict)
    auth = HTTPBasicAuth(api_key, "")
    argument_dict = dict(
        auth = auth,
        domain = domain,
        recreate_response = recreate_response,
        excluded = excluded,
    )
    ctx.obj.type = "key" if keys or (ctx.invoked_subcommand == "create") else "device"
    ctx.obj.cls = eval(ctx.obj.type + "_class")(
        values = keys if ctx.obj.type == "key" else devices,
        response_files = key_response_files if ctx.obj.type == "key" else device_response_files,
        **argument_dict
    )
    ctx.obj.dry_run = dry_run
    ctx.obj.verbose = verbose

@tailapi.command()
@click.argument("options", nargs = -1, required = False)
@click.pass_context
def show(ctx, options):
    if options:
        _ = Dict(dict())
        for dk in (responses := ctx.obj.cls.get_all()):
            for option in options:
                if option in responses[dk]:
                    _[dk][option] = responses[dk][option]
        pprint(_)
    else:
        ctx.obj.cls.print()

@tailapi.command(no_args_is_help = True)
@click.argument("option")
@click.pass_context
def get(ctx, option):
    for dk in (responses := ctx.obj.cls.get_all()):
        print(responses[dk][option])

@tailapi.command()
@click.option("-4", "--ipv4", is_flag = True)
@click.option("-6", "--ipv6", is_flag = True)
@click.option("-f", "--first", is_flag = True)
@click.pass_context
def ip(ctx, ipv4, ipv6, first):
    both = (ipv4 and ipv6) or ((not ipv4) and (not ipv6))
    responses = ctx.obj.cls.get_all()
    ips = Dict(dict())
    for dk, v in responses.items():
        ipvs = [ ip_address(i) for i in v.addresses ]
        for i in ipvs:
            if ips[dk][i.version]:
                ips[dk][i.version].append(i)
            else:
                ips[dk][i.version] = [ i ]
    if ipv4:
        if len(ips) == 0:
            pass
        if len(ips) == 1:
            dk = next(iter(ips))
            if first or (len(ips[dk][4]) <= 1):
                print(ips[dk][4][0])
            else:
                for i in ips[dk][4]:
                    print(i)
        else:
            pprint({ dk : { 4 : v[4] } for dk, v in ips.items() if v[4] })
    if ipv6:
        if len(ips) == 0:
            pass
        if len(ips) == 1:
            dk = next(iter(ips))
            if first or (len(ips[dk][6]) <= 1):
                print(ips[dk][6][0])
            else:
                for i in ips[dk][6]:
                    print(i)
        else:
            pprint({ dk : { 6 : v[6] } for dk, v in ips.items() if v[6] })
    if both:
        pprint(ips)

# Adapted From:
# Answer: https://stackoverflow.com/a/18178379/10827766
# User: Antti Haapala -- Слава Україні | https://stackoverflow.com/users/918959/antti-haapala-%d0%a1%d0%bb%d0%b0%d0%b2%d0%b0-%d0%a3%d0%ba%d1%80%d0%b0%d1%97%d0%bd%d1%96
class Transformer(ast.NodeTransformer):
    ALLOWED_NAMES = set([

    ])
    ALLOWED_NODE_TYPES = set([
        "Expression",
        "BoolOp",
        "And",
        "Constant",
        "Or",
    ])

    def visit_Name(self, node):
        if not node.id in self.ALLOWED_NAMES:
            raise RuntimeError("Name access to %s is not allowed" % node.id)
        return self.generic_visit(node)

    def generic_visit(self, node):
        nodetype = type(node).__name__
        if nodetype not in self.ALLOWED_NODE_TYPES:
            raise RuntimeError("Invalid expression: %s not allowed" % nodetype)
        return ast.NodeTransformer.generic_visit(self, node)

class Group:
    def __init__(
        self,
        delimiter = "",
        dk = None,
        ephemeral = False,
        excluded_tags = (),
        groups = None,
        not_ephemeral = False,
        not_preauthorized = False,
        not_reusable = False,
        preauthorized = False,
        reusable = False,
        tags = (),
        using_keys = False,
        value = None,
        verbose = False,
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
        self.using_keys = using_keys
        self.value = value
        self.verbose = verbose
        self.properties = ("ephemeral", "preauthorized", "reusable")
        self.not_properties = tuple("not_" + p for p in self.properties)

    def _replace(self, pt):
        if pt.startswith("tag:"):
            return str(pt in (self.value.capabilities.devices.create.tags if self.using_keys else self.value.tags))
        elif pt.startswith("!tag:"):
            return str(pt not in (self.value.capabilities.devices.create.tags if self.using_keys else self.value.tags))
        else:
            match pt:
                case "!": return "not"
                case "&": return "and"
                case "&&": return "and"
                case "|": return "or"
                case "||": return "or"
                case "ephemeral": return str(self.value.capabilities.devices.create.ephemeral) if self.using_keys else None
                case "reusable": return str(self.value.capabilities.devices.create.reusable) if self.using_keys else None
                case "preauthorized": return str(self.value.capabilities.devices.create.preauthorized) if self.using_keys else None
                case "!ephemeral": return str( not self.value.capabilities.devices.create.ephemeral ) if self.using_keys else None
                case "!reusable": return str( not self.value.capabilities.devices.create.reusable ) if self.using_keys else None
                case "!preauthorized": return str( not self.value.capabilities.devices.create.preauthorized ) if self.using_keys else None
                case _: return pt

    # Adapted From:
    # Answer: https://stackoverflow.com/a/18178379/10827766
    # User: Antti Haapala -- Слава Україні | https://stackoverflow.com/users/918959/antti-haapala-%d0%a1%d0%bb%d0%b0%d0%b2%d0%b0-%d0%a3%d0%ba%d1%80%d0%b0%d1%97%d0%bd%d1%96
    def eval(self, group):
        source = group if isinstance(group, (str, bytes, bytearray)) else " ".join(group)
        tree = ast.parse(source, mode='eval')
        transformer = Transformer()
        transformer.visit(tree)
        clause = compile(tree, '<AST>', 'eval')
        return eval(clause)

    def replace(self, group):
        pts = list(intersperse(self.delimiter, [ pt for pt in oreo.flatten((
                [ str(getattr(self, p) and getattr(self.value.capabilities.devices.create, p)) if getattr(self, p) else None for p in self.properties ],
                [ str(getattr(self, p) and not getattr(self.value.capabilities.devices.create, p)) if getattr(self, p) else None for p in self.not_properties ],
                str(all(tag in self.value.capabilities.devices.create.tags for tag in self.tags)) if self.tags else None,
                str(all(tag not in self.value.capabilities.devices.create.tags for tag in self.excluded_tags)) if self.excluded_tags else None,
            )
        ) if pt is not None ])) if self.using_keys else list(intersperse(self.delimiter, [ pt for pt in (
            str(all(tag in self.value.tags for tag in self.tags)) if self.tags else None,
            str(all(tag not in self.value.tags for tag in self.excluded_tags)) if self.excluded_tags else None,
        ) if pt is not None ]))
        yield from oreo.flatten((
            pts,
            [ self.delimiter ] if pts else [],
            [ self._replace(pt) for pt in filter(None, oreo.flatten(oreo.multipart(pt, ")") for pt in oreo.flatten(oreo.multipart(pt, "(") for pt in group.split()))) ],
        ))

    def replace_all(self, groups):
        return [ self.replace(group) for group in groups ]

    def _results(self):
        results = []
        if self.verbose:
            dks = "key" if self.using_keys else "device"
            of_id = "of id " if self.dk.isnumeric() else ""
            print(f'Group String{"s" if len(self.groups) == 1 else ""} for {dks} {of_id}"{self.dk}":')
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
                print(togroup.replace("not_", "!"), "==>", " ".join(group), "\n")
            results.append(self.eval(group))
        return results

    def results(self):
        if self.using_keys:
            if self.value.capabilities:
                yield from self._results()
        else:
            yield from self._results()

def and_or_values(
    responses,
    tags,
    excluded_tags,
    groups,
    or_pt,
    using_keys,
    ctx,
    ephemeral,
    not_ephemeral,
    reusable,
    not_reusable,
    preauthorized,
    not_preauthorized,
):
    values = []
    tags = { f"tag:{tag}" for tag in tags if not tag.startswith("tag:") }
    excluded_tags = { f"tag:{tag}" for tag in excluded_tags if not tag.startswith("tag:") }
    variables = [ tags, excluded_tags, ephemeral, not_ephemeral, reusable, not_reusable, preauthorized, not_preauthorized ]
    group_opts = dict(
        ephemeral = ephemeral,
        excluded_tags = excluded_tags,
        groups = groups,
        not_ephemeral = not_ephemeral,
        not_preauthorized = not_preauthorized,
        not_reusable = not_reusable,
        preauthorized = preauthorized,
        reusable = reusable,
        tags = tags,
        using_keys = using_keys,
        verbose = ctx.obj.verbose,
    )
    if any([ groups ] + variables):
        if or_pt:
            for dk, v in responses.items():
                group = Group(
                    delimiter = "or",
                    dk = dk,
                    value = v,
                    ** group_opts,
                )
                if using_keys:
                    if any((
                        (ephemeral and v.capabilities.devices.create.ephemeral),
                        (not_ephemeral and not v.capabilities.devices.create.ephemeral),
                        (not_preauthorized and not v.capabilities.devices.create.preauthorized),
                        (not_reusable and not v.capabilities.devices.create.reusable),
                        (preauthorized and v.capabilities.devices.create.preauthorized),
                        (reusable and v.capabilities.devices.create.reusable),
                        any(group.results()),
                        any(tag in v.capabilities.devices.create.tags for tag in tags),
                        any(tag not in v.capabilities.devices.create.tags for tag in excluded_tags),
                    )):
                        values.append(dk)
                else:
                    if any(
                        any(group.results()),
                        any(tag in v.tags for tag in tags),
                        any(tag not in v.tags for tag in excluded_tags),
                    ):
                        values.append(dk)
        else:
            for dk, v in responses.items():
                group = Group(
                    delimiter = "and",
                    dk = dk,
                    value = v,
                    ** group_opts,
                )
                if using_keys:
                    if all(n for n in (
                        (ephemeral and v.capabilities.devices.create.ephemeral) if ephemeral else None,
                        (not_ephemeral and not v.capabilities.devices.create.ephemeral) if not_ephemeral else None,
                        (not_preauthorized and not v.capabilities.devices.create.preauthorized) if not_preauthorized else None,
                        (not_reusable and not v.capabilities.devices.create.reusable) if not_reusable else None,
                        (preauthorized and v.capabilities.devices.create.preauthorized) if preauthorized else None,
                        (reusable and v.capabilities.devices.create.reusable) if reusable else None,
                        all(group.results()) if groups else None,
                        all(tag in v.capabilities.devices.create.tags for tag in tags) if tags else None,
                        all(tag not in v.capabilities.devices.create.tags for tag in excluded_tags) if excluded_tags else None,
                    ) if n is not None):
                        values.append(dk)
                else:
                    if all(n for n in (
                        all(group.results()) if groups else None,
                        all(tag in v.tags for tag in tags) if tags else None,
                        all(tag not in v.tags for tag in excluded_tags) if excluded_tags else None,
                    ) if n is not None):
                        values.append(dk)
    return values

@tailapi.command()
@click.option("-t", "--tags", multiple = True)
@click.option("-T", "--excluded-tags", multiple = True)
@click.option("-e", "--ephemeral", is_flag = True)
@click.option("-p", "--preauthorized", is_flag = True)
@click.option("-r", "--reusable", is_flag = True)
@click.option("-E", "--not-ephemeral", is_flag = True)
@click.option("-P", "--not-preauthorized", is_flag = True)
@click.option("-R", "--not-reusable", is_flag = True)
@click.option("-A", "--api-keys", is_flag = True)
@click.option(
    "-a",
    "--and-pt",
    cls = oreo.Option,
    xor = [ "OR" ],
    is_flag = True,
    help = """If a combination of `ephemeral', `preauthorized', `reusable', and tags are used,
this flag deletes devices or keys with all of the specified tags and properties.
Note that properties don't work with devices. This is the default.""",
)
@click.option(
    "-o",
    "--or-pt",
    cls = oreo.Option,
    xor = [ "AND" ],
    is_flag = True,
    help = """If a combination of `ephemeral', `preauthorized', `reusable', and tags are used,
this flag deletes devices or keys with any of the specified tags and properties. Note that properties don't work with devices.""",
)
@click.option(
    "-g",
    "--groups",
    help = """Strings of properties and tags following boolean logic (`&&', `&', or `and', and `||', `|', and `or'),
such as `(ephemeral or reusable) and (tag:server or tag:relay)' deleting all keys with the ephemeral or reusable properties,
and with the server or relay tags.
Can be specified multiple times, where `--or-pt' and `--and-pt' will be used to dictate the interactions between groups,
and can be used with other property and tag options, such as `--ephemeral', etc.
Negation can be achieved with `!' prefixed to the properties or tags, such as `!ephemeral' or `!tag:server'. Note that properties don't work with devices.""",
    multiple = True,
)
@click.pass_context
def filter(ctx, api_keys, and_pt, or_pt, tags, excluded_tags, ephemeral, not_ephemeral, reusable, not_reusable, preauthorized, not_preauthorized, groups):
    using_keys = isinstance(ctx.obj.cls, key_class)
    if api_keys and using_keys:
        pprint(ctx.obj.cls.get_api_keys(verbose = True))
    else:
        responses = ctx.obj.cls.get_all()
        values = and_or_values(
            responses,
            tags,
            excluded_tags,
            groups,
            or_pt,
            using_keys,
            ctx,
            ephemeral,
            not_ephemeral,
            reusable,
            not_reusable,
            preauthorized,
            not_preauthorized,
        )
        pprint({ value : responses[value] for value in values } if values else responses)

@tailapi.command()
@click.option("-t", "--tags", multiple = True)
@click.option("-T", "--excluded-tags", multiple = True)
@click.option("--do-not-prompt", is_flag = True)
@click.option("-e", "--ephemeral", is_flag = True)
@click.option("-p", "--preauthorized", is_flag = True)
@click.option("-r", "--reusable", is_flag = True)
@click.option("-E", "--not-ephemeral", is_flag = True)
@click.option("-P", "--not-preauthorized", is_flag = True)
@click.option("-R", "--not-reusable", is_flag = True)
@click.option(
    "-a",
    "--and-pt",
    cls = oreo.Option,
    xor = [ "OR" ],
    is_flag = True,
    help = """If a combination of `ephemeral', `preauthorized', `reusable', and tags are used,
this flag deletes devices or keys with all of the specified tags and properties.
Note that properties don't work with devices. This is the default.""",
)
@click.option(
    "-o",
    "--or-pt",
    cls = oreo.Option,
    xor = [ "AND" ],
    is_flag = True,
    help = """If a combination of `ephemeral', `preauthorized', `reusable', and tags are used,
this flag deletes devices or keys with any of the specified tags and properties. Note that properties don't work with devices.""",
)
@click.option(
    "-g",
    "--groups",
    help = """Strings of properties and tags following boolean logic (`&&', `&', or `and', and `||', `|', and `or'),
such as `(ephemeral or reusable) and (tag:server or tag:relay)' deleting all keys with the ephemeral or reusable properties,
and with the server or relay tags.
Can be specified multiple times, where `--or-pt' and `--and-pt' will be used to dictate the interactions between groups,
and can be used with other property and tag options, such as `--ephemeral', etc.
Negation can be achieved with `!' prefixed to the properties or tags, such as `!ephemeral' or `!tag:server'. Note that properties don't work with devices.""",
    multiple = True,
)
@click.pass_context
def delete(ctx, do_not_prompt, and_pt, or_pt, tags, excluded_tags, ephemeral, not_ephemeral, reusable, not_reusable, preauthorized, not_preauthorized, groups):
    using_keys = isinstance(ctx.obj.cls, key_class)
    responses = ctx.obj.cls.get_all()
    values = and_or_values(
        responses,
        tags,
        excluded_tags,
        groups,
        or_pt,
        using_keys,
        ctx,
        ephemeral,
        not_ephemeral,
        reusable,
        not_reusable,
        preauthorized,
        not_preauthorized,
    )
    all_your_specified = "ALL YOUR" if ctx.obj.cls.all else "THE SPECIFIED"
    devices_or_keys = "AUTHKEYS" if using_keys else "DEVICES"
    input_message = f'THIS WILL DELETE {all_your_specified} {devices_or_keys} [ {", ".join(values if values else responses.keys())} ] FROM YOUR TAILNET! TO CONTINUE, PLEASE TYPE IN "DELETE {devices_or_keys}" WITHOUT THE QUOTES:\n\t'
    input_response = f"DELETE {devices_or_keys}"
    if ctx.obj.verbose:
        print("Key Dictionary:")
        pprint(responses)
        print("\nKeys to be deleted:", values)
    if not ctx.obj.dry_run and (do_not_prompt or (input(input_message) == input_response)):
        ctx.obj.cls.delete_all(values = values)

@tailapi.command(no_args_is_help = True)
@click.argument("tags", nargs = -1, required = False)
@click.option("-e", "--ephemeral", is_flag = True)
@click.option("-p", "--preauthorized", is_flag = True)
@click.option("-r", "--reusable", is_flag = True)
@click.option("-j", "--just-key", is_flag = True, help = "Just print the key.")
@click.option(
    "-c",
    "--count",
    cls = oreo.Option,
    xor = [ "groups" ],
    default = 1,
    type = int,
    help = "Number of keys to create.",
)
@click.option(
    "-g",
    "--groups",
    cls = oreo.Option,
    xor = [ "count" ],
    help = """Strings of properties and tags,
such as `ephemeral reusable tag:relay tag:server' creating an ephemeral and reusable key with tags `relay' and `server'.
If used with other property options, such as `--preauthorized', or tag arguments, all keys will have those properties and tags as well.
Note that tags here must be prefixed with `tag:'.""",
    multiple = True,
)
@click.pass_context
def create(ctx, tags, ephemeral, preauthorized, reusable, just_key, count, groups):
    tags = { f"tag:{tag}" for tag in tags if not tag.startswith("tag:") }
    if groups:
        for group in groups:
            split_group = group.split()
            data = Dict(dict())
            data.capabilities.devices.create = {
                "ephemeral" : ("ephemeral" in split_group) or ephemeral,
                "preauthorized" : ("preauthorized" in split_group) or preauthorized,
                "reusable" : ("reusable" in split_group) or reusable,
                "tags" : list({ tag for tag in split_group if tag.startswith("tag:") } | tags),
            }
            ctx.obj.cls.create_key(data, just_key)
    else:
        data = Dict(dict())
        data.capabilities.devices.create = {
            "ephemeral" : ephemeral,
            "preauthorized" : preauthorized,
            "reusable" : reusable,
            "tags" : list(tags),
        }
        for i in range(count):
            ctx.obj.cls.create_key(data, just_key)

if __name__ == '__main__':
    tailapi(obj=Dict(dict()))