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

def raise_response_error(error_message, response):
    raise ValueError(error_message + " Response reason: " + response.reason)

def return_json_addict(action, error_message, *args, **kwargs):
    if (response := getattr(requests, action)(*args, **kwargs)).status_code == 200:
        return Dict(json.loads(response.text))
    else:
        raise_response_error(error_message, response)

class dk:
    def __init__(self, auth, recreate_response, values):
        self.auth = auth
        self.recreate_response = recreate_response
        self.values = list(values)
        self.all_responses = dict()
        self.empty = bool(self.values)

    def get_response(self, url, error_message):
        if (response := requests.get(url, auth = self.auth)).status_code == 200:
            return json.loads(response.text)
        else:
            raise_response_error(error_message, response)

    def _write(self, response_file, response_dict):
        response_path = Path(response_file)
        response_dir = Path(response_path.parent)
        response_dir.mkdir(parents = True, exist_ok = True)
        with open(response_file, "w") as f:
            json.dump(response_dict, f)
        return response_dict

    def get(self, response_file, all_override = False, recreate_override = False):
        if self.recreate_response or recreate_override:
            return self.write(all_override = all_override)
        elif exists(response_file):
            with open(response_file) as f:
                return Dict(json.load(f))
        else:
            return self.write(all_override = all_override)

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

    def delete_all(self):
        try:
            for dk in self.get_all():
                if self.delete(dk):
                    self.values.remove(dk)
                    self.response_files.remove(self.mapped.pop(dk))
        finally:
            self.write()
            if not self.all:
                self.write(all_override = True)

class device_class(dk):
    def __init__(self, recreate_response, response_files, auth, values, domain):
        super().__init__(values = values, auth = auth, recreate_response = recreate_response)
        self.all = "all" in values
        self.default_response_file = f"{environ['HOME']}/.local/share/tailapi/devices.json"
        self.domain = domain
        self.response_files = response_files or self.create_response_file_paths("devices", self.values)
        self.mapped = Dict(dict(zip(self.values, self.response_files, strict = True)))

    def write(self, all_override = False):
        if self.all or all_override:
            all_responses = Dict({
                device["name"].split(".")[0] : device for device in self.get_response(
                    f"https://api.tailscale.com/api/v2/tailnet/{self.domain}/devices",
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
    def __init__(self, values, response_files, auth, recreate_response, domain):
        super().__init__(values = values, auth = auth, recreate_response = recreate_response)
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
        if self.get_all(all_override = True)[key].capabilities:
            self._delete(
                f"https://api.tailscale.com/api/v2/tailnet/{self.domain}/keys/{key}",
                f'Sucessfully deleted key of id "{key}"!',
                f'Sorry; something happened when trying to delete key of id "{key}"!',
            )
            return True
        else:
            print("Sorry; not deleting an API key!")
            return False

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
    if keys:
        ctx.obj.cls = key_class(
            auth = auth,
            domain = domain,
            values = keys,
            recreate_response = recreate_response,
            response_files = key_response_files,
        )
    else:
        ctx.obj.cls = device_class(
            auth = auth,
            values = devices or [ "all" ],
            domain = domain,
            recreate_response = recreate_response,
            response_files = device_response_files,
        )

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
@click.option("--do-not-prompt", is_flag = True)
@click.pass_context
def delete(ctx, do_not_prompt):
    all_your_specified = "ALL YOUR" if ctx.obj.cls.all else "THE SPECIFIED"
    devices_or_keys = "AUTHKEYS" if isinstance(ctx.obj.cls, key_class) else "DEVICES"
    input_message = f'THIS WILL DELETE {all_your_specified} {devices_or_keys} FROM YOUR TAILNET! TO CONTINUE, PLEASE TYPE IN "DELETE {devices_or_keys}" WITHOUT THE QUOTES:\n\t'
    input_response = f"DELETE {devices_or_keys}"
    if do_not_prompt or (input(input_message) == input_response):
        ctx.obj.cls.delete_all()

@tailapi.command(no_args_is_help = True)
@click.argument("tags", nargs = -1, required = False)
@click.option("-e", "--ephemeral", is_flag = True)
@click.option("-p", "--preauthorized", is_flag = True)
@click.option("-r", "--reusable", is_flag = True)
@click.option("-j", "--just-key", is_flag = True, help = "Just print the key.")
@click.option("-c", "--count", default = 1, type = int, help = "Number of keys to create.")
@click.pass_context
def create(ctx, tags, ephemeral, preauthorized, reusable, just_key, count):
    data = Dict(dict())
    data.capabilities.devices.create = {
        "ephemeral" : ephemeral,
        "preauthorized" : preauthorized,
        "reusable" : reusable,
        "tags" : [ f"tag:{tag}" for tag in tags ],
    }
    for i in range(count):
        response = return_json_addict(
            "post",
            f'Sorry; something happened when trying to create a key with the following properties: "{data}"!',
            f"https://api.tailscale.com/api/v2/tailnet/{ctx.obj.cls.domain}/keys",
            json = data,
            auth = ctx.obj.cls.auth,
        )
        if just_key:
            print(response.key)
        else:
            pprint(response)

if __name__ == '__main__':
    tailapi(obj=Dict(dict()))