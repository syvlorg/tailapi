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

def write_response_base(response_file, url, auth):
    response_path = Path(response_file)
    response_dir = Path(response_path.parent)
    response_dir.mkdir(parents = True, exist_ok = True)
    with open(response_file, "w") as f:
        response = requests.get(url, auth = auth).text
        f.write(response)
        return json.loads(response)

def write_response_device(response_file, auth, id):
    return write_response_base(response_file, f"https://api.tailscale.com/api/v2/device/{id}?fields=all", auth)

def write_response_devices(response_file, auth, domain):
    return write_response_base(response_file, f"https://api.tailscale.com/api/v2/tailnet/{domain}/devices", auth)

def get_base(func, recreate_response, response_file, auth, *args):
    if recreate_response:
        return func(response_file, auth, *args)
    elif exists(response_file):
        with open(response_file) as f:
            return json.load(f)
    else:
        return func(response_file, auth, *args)

def get_device(recreate_response, response_file, auth, id):
    response = get_base(write_response_device, recreate_response, response_file, auth, id)
    return Dict({ response["name"].split(".")[0] : response })

def get_devices(recreate_response, response_file, auth, domain):
    return Dict({ device["name"].split(".")[0] : device for device in get_base(write_response_devices, recreate_response, response_file, auth, domain)["devices"] })

one_req = [ "device", "key", "create" ]

@click.group(no_args_is_help = True)
@click.option("-a", '--api-key', default=environ["TAILSCALE_APIKEY"])
@click.option("-d", '--device', req_one_of = [ "domain" ], one_req = one_req, help = "The device name or id.")
@click.option("-D", '--domain', req_one_of = [ "device" ])
@click.option("-k", "--key", cls = oreo.Option, one_req = one_req, help = "The key id.")
@click.option("-c", "--create", cls = oreo.Option, one_req = one_req)
@click.option("-f", '--response-file')
@click.option("-r", '--recreate-response', is_flag = True)
@click.pass_context
def tailapi(ctx, api_key, domain, device, response_file, recreate_response, id, key):
    ctx.ensure_object(dict)
    ctx.obj.api_key = api_key
    ctx.obj.auth = HTTPBasicAuth(ctx.obj.api_key, "")
    ctx.obj.domain = domain
    ctx.obj.id = device if device.isnumeric() else None
    ctx.obj.device = device if ctx.obj.id is None else None
    ctx.obj.key = key
    ctx.obj.response_file = response_file or (f"{environ['HOME']}/.local/share/tailapi/{id}.json" if ctx.obj.id else f"{environ['HOME']}/.local/share/tailapi/devices.json")
    ctx.obj.recreate_response = recreate_response
    ctx.obj.devices = None if ctx.obj.domain is None else get_devices(ctx.obj.recreate_response, ctx.obj.response_file, ctx.obj.auth, ctx.obj.domain)

def return_json_reponse(action, *args, **kwargs):
    return Dict(json.loads(getattr(requests, action)(*args, **kwargs).text))

@tailapi.command(no_args_is_help = True)
@click.argument("options", nargs = -1, required = False)
@click.pass_context
def show(ctx, options):
    if ctx.obj.key:
        pprint(return_json_reponse("get", f"https://api.tailscale.com/api/v2/tailnet/example.com/keys/{ctx.obj.key}", auth = ctx.obj.auth))
    else:
        if ctx.obj.id:
            pprint(get_device(ctx.obj.recreate_response, ctx.obj.response_file, ctx.obj.auth, ctx.obj.id))
        elif ctx.obj.device:
            if not ctx.obj.devices[ctx.obj.device]:
                print(f'Sorry; no such device "{ctx.obj.device}" exists!')
                exit(1)
            elif options:
                pprint({ opt : ctx.obj.devices[ctx.obj.device][opt] for opt in options })
            else:
                pprint(ctx.obj.devices[ctx.obj.device])
        else:
            pprint(ctx.obj.devices)

@tailapi.command(no_args_is_help = True)
@click.argument("option")
@click.pass_context
def get(ctx, option):
    print(ctx.obj.devices[ctx.obj.device][option])

@tailapi.command(no_args_is_help = True)
@click.option("-d", "--no-recreate", is_flag = True, help = "Don't recreate the list of devices.")
@click.option("--do-not-prompt", is_flag = True)
@click.pass_context
def delete(ctx, no_recreate, do_not_prompt):
    if ctx.obj.key:
        if do_not_prompt or input(f'THIS WILL DELETE YOUR KEY FROM YOUR TAILNET! TO CONTINUE, PLEASE TYPE IN "DELETE KEY" WITHOUT THE QUOTES:\n\t') == f"DELETE KEY":
            if (response := requests.delete(f"https://api.tailscale.com/api/v2/tailnet/example.com/keys/{ctx.obj.key}", auth = ctx.obj.auth)).status_code == 200:
                print(f'Sucessfully deleted key of id "{ctx.obj.key}"!')
            else:
                print(f"Sorry; something happened! Response reason: {response.reason}")
                exit(1)
    else:
        if not no_recreate:
            ctx.obj.devices = get_device(True, ctx.obj.response_file, ctx.obj.auth, ctx.obj.id) if ctx.obj.id else get_devices(True, ctx.obj.response_file, ctx.obj.auth, ctx.obj.domain)
        if ctx.obj.id:
            ctx.obj.device = next(iter(ctx.obj.devices))
        if not ctx.obj.devices[ctx.obj.device]:
            print(f'Sorry; no such device "{ctx.obj.device}" exists!')
            exit(1)
        elif do_not_prompt or input(f'THIS WILL DELETE YOUR DEVICE FROM YOUR TAILNET! TO CONTINUE, PLEASE TYPE IN "DELETE {ctx.obj.device.upper()}" WITHOUT THE QUOTES:\n\t') == f"DELETE {ctx.obj.device.upper()}":
            if (response := requests.delete(f"https://api.tailscale.com/api/v2/device/{ctx.obj.id or ctx.obj.devices[ctx.obj.device].id}", auth = ctx.obj.auth)).status_code == 200:
                print(f'Sucessfully deleted "{ctx.obj.device}"!')
                write_response_devices(ctx.obj.response_file, ctx.obj.auth, ctx.obj.domain)
            else:
                print(f"Sorry; something happened! Response reason: {response.reason}")
                exit(1)

if __name__ == '__main__':
    tailapi(obj=Dict(dict()))

@tailapi.command(no_args_is_help = True)
@click.argument("tags", nargs = -1, required = False)
@click.option("-e", "--ephemeral", is_flag = True)
@click.option("-p", "--preauthorized", is_flag = True)
@click.option("-r", "--reusable", is_flag = True)
@click.option("-j", "--just-key", help = "Just print the key.")
def create(ctx, tags, ephemeral, preauthorized, reusable, just_key):
    data = Dict(dict())
    data.capabilities.devices.create = {
        "ephemeral" : ephemeral,
        "preauthorized" : preauthorized,
        "reusable" : reusable,
        "tags" : [ f"tag:{tag}" for tag in tags ],
    }
    response = return_json_reponse("post", "https://api.tailscale.com/api/v2/tailnet/example.com/keys", json = data, auth = ctx.obj.auth)
    if just_key:
        print(response.key)
    else:
        pprint(response)