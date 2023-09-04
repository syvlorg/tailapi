import requests

from autoslot import Slots

from .api import API
from .miscellaneous import (
    construct_error_message,
    raise_response_error,
    return_json_addict,
)


class Server(Slots):
    def __init__(self, api=None, auth=None, oapi=None):
        if any((api, auth, oapi)):
            self.api = api or API(auth or oapi)
            self.auth = auth or self.api.get()
        else:
            raise ValueError(
                "Sorry; an api key / oauth token, `API' instance, or `HTTPBasicAuth' / `BearerAuth' instance must be provided!"
            )

    def __getattr__(self, attr):
        def wrapper(error_message, *args, **kwargs):
            return return_json_addict(
                attr, error_message, *args, auth=kwargs.pop("auth", self.auth), **kwargs
            )

        return wrapper

    def delete(
        self, success_message, error_message, *args, ignore_error=False, **kwargs
    ):
        response = requests.delete(*args, auth=kwargs.pop("auth", self.auth), **kwargs)
        if response.status_code == 200:
            print(success_message)
            return True
        elif ignore_error:
            print(construct_error_message(error_message, response))
            return False
        else:
            raise_response_error(error_message, response)
