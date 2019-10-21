class FieldErrorInfo:
    key = None
    message = None

    def __init__(self, key, message):
        self.key = key
        self.message = message

    def __str__(self):
        if self.key:
            return '{}: {}'.format(self.key, self.message)
        else:
            return self.message

    def __repr__(self):
        return 'FieldErrorInfo(key={} message={})'.format(self.key, self.message)


class InvalidParams(Exception):
    def __init__(self, errors):
        """errors is list contains key, value pairs"""
        if isinstance(errors, list):
            for i in errors:
                if not isinstance(i, FieldErrorInfo):
                    raise TypeError(
                        'errors item must be instance of FieldErrorInfo, got {} ({})'.format(
                            type(i), i
                        )
                    )
        elif isinstance(errors, str):
            errors = [FieldErrorInfo(None, errors)]
        else:
            raise TypeError('errors must be list of FieldErrorInfo')
        self.errors = errors

    def __str__(self):
        return '\n'.join(str(e) for e in self.errors)


class DataInvalidToSchema(Exception):
    pass
