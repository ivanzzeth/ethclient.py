import logging
import time
import json
from web3 import Web3

from requests.exceptions import (
    ConnectionError,
    HTTPError,
    Timeout,
    TooManyRedirects,
)

from typing import (
    Any,
    Callable,
    Collection,
    Type,
)

from web3.types import (
    RPCEndpoint,
    RPCResponse,
)

# const
RECONNECT_INTERVAL = 1  # second
RECONNECT_MAX_COUNT = 1000
RECONNECT_TIMEOUT = RECONNECT_INTERVAL * RECONNECT_MAX_COUNT


def check_if_retry_on_failure(method: RPCEndpoint) -> bool:
    """
    always return True for now
    :param method:
    :return:
    """
    return True


def exception_retry_middleware(
    make_request: Callable[[RPCEndpoint, Any], RPCResponse],
    web3: "Web3",
    errors: Collection[Type[BaseException]],
    retries: int = 5,
) -> Callable[[RPCEndpoint, Any], RPCResponse]:
    """
    Creates middleware that retries failed HTTP requests. Is a default
    middleware for HTTPProvider.
    """
    def middleware(method: RPCEndpoint, params: Any) -> RPCResponse:
        if check_if_retry_on_failure(method):
            for i in range(retries):
                try:
                    return make_request(method, params)
                # https://github.com/python/mypy/issues/5349
                except errors:  # type: ignore
                    if i < retries - 1:
                        continue
                    else:
                        raise
            return None
        else:
            return make_request(method, params)
    return middleware


def http_retry_request_middleware(
    make_request: Callable[[RPCEndpoint, Any], Any], web3: "Web3"
) -> Callable[[RPCEndpoint, Any], Any]:
    """
    Usage:
    web3.middleware_onion.add(http_retry_request_middleware, 'http_retry_request_middleware')

    :param make_request:
    :param web3:
    :return:
    """
    return exception_retry_middleware(
        make_request,
        web3,
        (ConnectionError, HTTPError, Timeout, TooManyRedirects),
        RECONNECT_MAX_COUNT
    )


class ReconnectMiddleware:
    """
    Usage:
    web3.middleware_onion.inject(ReconnectMiddleware, 'reconnect_middleware', 0)
    """
    def __init__(self, make_request, w3):
        self.w3 = w3
        self.make_request = make_request

    def __call__(self, method, params):
        logging.debug('ReconnectMiddleware wrap request')
        # perform the RPC request, getting the response
        response = None
        for i in range(RECONNECT_MAX_COUNT):
            try:
                logging.debug('ReconnectMiddleware try method: {}, params: {}, count: {}'.format(method, params, i))
                response = self.make_request(method, params)
            except json.JSONDecodeError as e:
                logging.error('ReconnectMiddleware json decode err: {}'.format(e))
                time.sleep(RECONNECT_INTERVAL)
                continue
            except Exception as e:
                logging.error('ReconnectMiddleware exception: {}'.format(e))
                time.sleep(RECONNECT_INTERVAL)
                continue
            break
        logging.debug('ReconnectMiddleware do post-processing here')
        return response
