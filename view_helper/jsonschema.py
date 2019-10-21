import json
from functools import wraps
from . import logger
from .errors import InvalidParams, DataInvalidToSchema


VALIDATE_RESPONSE = True


def wrap_with_validator(pre_validator=None, post_validator=None):
    """
    :param pre_validator: fn(data: request json data, request: django request) -> None:
        raise InvalidParams
    :param post_validator: fn(data: response json data) -> None:
        raise InvalidParams
    """

    def decorator(fn):
        @wraps(fn)
        def _fn(self, request):
            # must inherit JSONView
            if pre_validator:
                try:
                    data = self.json
                    pre_validator(data, request=request)
                except InvalidParams as e:
                    raise
                except Exception as e:
                    raise InvalidParams(str(e))
            rv = fn(self, request)
            if rv.status_code == 200 and post_validator:
                try:
                    data = json.loads(rv.content)
                    post_validator(data)
                except InvalidParams as e:
                    # exception is a bug
                    logger.warn("post_validator error: %s", e)
                    if VALIDATE_RESPONSE:
                        raise DataInvalidToSchema(
                            'service under maintenance: invalid data to schema'
                        )
            return rv

        return _fn

    return decorator
