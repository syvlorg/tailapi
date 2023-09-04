import json
import requests
from addict import Dict
from rich.pretty import pprint
from valiant import dirs


def construct_error_message(error_message, response):
    data = json.dumps(json.loads(response.text), indent=4)
    return f"{error_message}\nResponse reason: {response.reason}\nResponse data: {data}"


def raise_response_error(error_message, response):
    raise ValueError(construct_error_message(error_message, response))


def return_json_addict(action, error_message, *args, include_headers=False, **kwargs):
    response = getattr(requests, action)(*args, **kwargs)
    if response.status_code == 200:
        data = Dict(json.loads(response.text))
        if include_headers:
            return Dict(data=data, headers=dict(response.headers))
        else:
            return data
    else:
        raise_response_error(error_message, response)
