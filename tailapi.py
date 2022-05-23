#!/usr/bin/env python

from addict import Dict
from os import environ
from os.path import exists
from pathlib import Path
from requests.auth import HTTPBasicAuth
from rich import print
from rich.pretty import pprint
from sys import exit
import click
import json
import oreo
import requests

def return_json_addict(action, *args, **kwargs):
    return Dict(json.loads(getattr(requests, action)(*args, **kwargs).text))

class dk:
    def __init__(self, auth, recreate_response, values):
        self.auth = auth
        self.recreate_response = recreate_response
        self.values = values
        self.empty = bool(self.values)

    def get_response(self, url):
        return json.loads(requests.get(url, auth = self.auth).text)

    def _write(self, response_file, response_dict):
        response_path = Path(response_file)
        response_dir = Path(response_path.parent)
        response_dir.mkdir(parents = True, exist_ok = True)
        if not exists(response_file):
            with open(response_file, "w") as f:
                json.dump(response_dict, f)
        return response_dict

    def get(self, response_file):
        if self.recreate_response:
            return self.write()
        elif exists(response_file):
            with open(response_file) as f:
                return json.load(f)
        else:
            return self.write()

    def get_all(self):
        if self.all:
            return self.get(self.default_response_file)
        else:
            all_responses = Dict(dict())
            for file in self.response_files:
                all_responses.update(self.get(file))
            return all_responses

    def print(self):
        pprint(self.get_all())

    def create_response_file_path(self, dk, value):
        return f"{environ['HOME']}/.local/share/tailapi/{dk}/{value}.json"

class device_class(dk):
    def __init__(self, recreate_response, response_files, auth, values, domain):
        super().__init__(values = values, auth = auth, recreate_response = recreate_response)
        self.all = "all" in values
        self.default_response_file = f"{environ['HOME']}/.local/share/tailapi/devices.json"
        self.domain = domain
        self.response_files = response_files or [ self.create_response_file_path("devices", device) for device in self.values ]
        self.zipped = zip(self.values, self.response_files, strict = True)

    def write(self):
        if self.all:
            all_responses = Dict({
                device["name"].split(".")[0] : device for device in self.get_response(f"https://api.tailscale.com/api/v2/tailnet/{self.domain}/devices")["devices"]
            })
            self._write(self.default_response_file, all_responses)
        else:
            all_responses = Dict(dict())
            for device, file in self.zipped:
                response = self.get_response(f"https://api.tailscale.com/api/v2/device/{device}?fields=all")
                all_responses.update(self._write(file, { response["name"].split(".")[0] : response }))
        return all_responses

class key_class(dk):
    def __init__(self, values, response_files, auth, recreate_response, domain):
        super().__init__(values = values, auth = auth, recreate_response = recreate_response)
        self.all = "all" in values
        self.default_response_file = f"{environ['HOME']}/.local/share/tailapi/keys.json"
        self.domain = domain
        self.response_files = response_files or [ self.create_response_file_path("keys", key) for key in self.values ]
        self.zipped = zip(self.values, self.response_files, strict = True)

    def create_url(self, key):
        return f"https://api.tailscale.com/api/v2/tailnet/{self.domain}/keys/{key}"

    def write(self):
        all_responses = Dict(dict())
        if self.all:
            for key in self.get_response(f"https://api.tailscale.com/api/v2/tailnet/{self.domain}/keys")["keys"]:
                all_responses[key["id"]] = json.loads(requests.get(self.create_url(key["id"]), auth = self.auth).text)
            self._write(self.default_response_file, all_responses)
        else:
            for key, file in self.zipped:
                response = self.get_response(self.create_url(key))
                all_responses.update(self._write(file, { response["id"] : response }))
        return all_responses

@click.group(no_args_is_help = True)
@click.option("-a", '--api-key', default = environ["TAILSCALE_APIKEY"])
@click.option(
    "-d",
    '--devices',
    cls = oreo.Option,
    help = "The device name or id; input `all' to show all devices, or specify multiple times for multiple devices. Every index here matches to the same index in `--device-response-files', while a value of `all' uses a single file. If no device response files are given, the device names are used for all specified devices.",
    multiple = True,
    xor = [ "keys" ],
)
@click.option("-D", '--domain', required = True)
@click.option(
    "-k",
    "--keys",
    cls = oreo.Option,
    help = "The key id; input `all' to show all keys, or specify multiple times for multiple keys. Every index here matches to the same index in `--key-response-files', while a value of `all' uses a single file. If no key response files are given, the key ids' are used for all specified keys.",
    multiple = True,
    xor = [ "devices" ],
)
@click.option(
    "-f",
    '--device-response-files',
    help = "Where the device information should be stored; every index here matches to the same index in `--devices', while a value of `all' in `--devices' uses a single file.",
    multiple = True,
)
@click.option(
    "-F",
    '--key-response-files',
    help = "Where the device information should be stored; every index here matches to the same index in `--keys', while a value of `all' in `--keys' uses a single file.",
    multiple = True,
)
@click.option("-r", '--recreate-response', is_flag = True)
@click.pass_context
def tailapi(ctx, api_key, domain, devices, device_response_files, key_response_files, recreate_response, keys):
    ctx.ensure_object(dict)
    auth = HTTPBasicAuth(api_key, "")
    if devices:
        ctx.obj.type = "devices"
        ctx.obj.cls = device_class(
            auth = auth,
            values = devices,
            domain = domain,
            recreate_response = recreate_response,
            response_files = device_response_files,
        )
    elif keys:
        ctx.obj.type = "keys"
        ctx.obj.cls = key_class(
            auth = auth,
            domain = domain,
            values = keys,
            recreate_response = recreate_response,
            response_files = key_response_files,
        )

@tailapi.command()
@click.argument("options", nargs = -1, required = False)
@click.pass_context
def show(ctx, options):
    if options:
        _ = {}
        responses = ctx.obj.cls.get_all()
        for dk in responses:
            for option in options:
                _[dk][option] = responses[dk][option]
        pprint(_)
    else:
        ctx.obj.cls.print()

@tailapi.command(no_args_is_help = True)
@click.argument("option")
@click.pass_context
def get(ctx, option):
    for dk in ctx.obj.values:
        print(ctx.obj.values[dk][option])

# @tailapi.command(no_args_is_help = True)
# @click.option("-d", "--no-recreate", is_flag = True, help = "Don't recreate the list of devices.")
# @click.option("--do-not-prompt", is_flag = True)
# @click.pass_context
# def delete(ctx, no_recreate, do_not_prompt):
#     if ctx.obj.key:
#         if "all" in ctx.obj.key:
#             if do_not_prompt or input(f'THIS WILL DELETE ALL YOUR AUTHKEYS FROM YOUR TAILNET! TO CONTINUE, PLEASE TYPE IN "DELETE AUTHKEYS" WITHOUT THE QUOTES:\n\t') == f"DELETE AUTHKEYS":
#                 for key in get_keys(ctx.obj.domain, ctx.obj.key, ctx.obj.auth).keys:
#                     id = key["id"]
#                     if (response := requests.delete(f"https://api.tailscale.com/api/v2/tailnet/example.com/keys/{id}", auth = ctx.obj.auth)).status_code == 200:
#                         print(f'Sucessfully deleted key of id "{id}"!')
#                     else:
#                         print(f"Sorry; something happened! Response reason: {response.reason}")
#                         exit(1)
#         else:
#             if do_not_prompt or input(f'THIS WILL DELETE THE SPECIFIED AUTHKEYS FROM YOUR TAILNET! TO CONTINUE, PLEASE TYPE IN "DELETE AUTHKEYS" WITHOUT THE QUOTES:\n\t') == f"DELETE AUTHKEYS":
#                 for key in ctx.obj.key:
#                     if (response := requests.delete(f"https://api.tailscale.com/api/v2/tailnet/example.com/keys/{key}", auth = ctx.obj.auth)).status_code == 200:
#                         print(f'Sucessfully deleted key of id "{key}"!')
#                     else:
#                         print(f"Sorry; something happened! Response reason: {response.reason}")
#                         exit(1)
#     else:
#         if not no_recreate:
#             ctx.obj.devices = get_device(True, ctx.obj.response_file, ctx.obj.auth, ctx.obj.id) if ctx.obj.id else get_devices(True, ctx.obj.response_file, ctx.obj.auth, ctx.obj.domain)
#         if ctx.obj.id:
#             ctx.obj.device = next(iter(ctx.obj.devices))
#         if not ctx.obj.devices[ctx.obj.device]:
#             print(f'Sorry; no such device "{ctx.obj.device}" exists!')
#             exit(1)
#         elif do_not_prompt or input(f'THIS WILL DELETE YOUR DEVICE FROM YOUR TAILNET! TO CONTINUE, PLEASE TYPE IN "DELETE {ctx.obj.device.upper()}" WITHOUT THE QUOTES:\n\t') == f"DELETE {ctx.obj.device.upper()}":
#             if (response := requests.delete(f"https://api.tailscale.com/api/v2/device/{ctx.obj.id or ctx.obj.devices[ctx.obj.device].id}", auth = ctx.obj.auth)).status_code == 200:
#                 print(f'Sucessfully deleted "{ctx.obj.device}"!')
#                 write_response_devices(ctx.obj.response_file, ctx.obj.auth, ctx.obj.domain)
#             else:
#                 print(f"Sorry; something happened! Response reason: {response.reason}")
#                 exit(1)

# @tailapi.command(no_args_is_help = True)
# @click.argument("tags", nargs = -1, required = False)
# @click.option("-e", "--ephemeral", is_flag = True)
# @click.option("-p", "--preauthorized", is_flag = True)
# @click.option("-r", "--reusable", is_flag = True)
# @click.option("-j", "--just-key", help = "Just print the key.")
# @click.pass_context
# def create(ctx, tags, ephemeral, preauthorized, reusable, just_key):
#     data = Dict(dict())
#     data.capabilities.devices.create = {
#         "ephemeral" : ephemeral,
#         "preauthorized" : preauthorized,
#         "reusable" : reusable,
#         "tags" : [ f"tag:{tag}" for tag in tags ],
#     }
#     response = return_json_addict("post", f"https://api.tailscale.com/api/v2/tailnet/{ctx.obj.domain}/keys", json = data, auth = ctx.obj.auth)
#     if just_key:
#         print(response.key)
#     else:
#         pprint(response)

if __name__ == '__main__':
    tailapi(obj=Dict(dict()))