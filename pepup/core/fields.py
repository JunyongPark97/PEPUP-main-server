import uuid


from django.db import models
from . import S3_HOST


"""
Django model field
"""


def _resolve(key):
    # return '%s/resolve/?key=%s' % (FILESERVER_HOST, key)
    return '%s/%s.jpg' % (S3_HOST, key)


class URLResolvableUUID(uuid.UUID):
    @property
    def url(self):
        return _resolve(self)


class S3ImageKeyField(models.UUIDField):
    description = 'Fileserver image key (UUIDField)'

    # https://github.com/django/django/blob/2a7ce34600d0f879e93c9a5e02215948ed3bb6ac/django/db/models/fields/__init__.py
    """
    def to_python(self, value):
        if value and not isinstance(value, URLResolvableUUID):
            try:
                return URLResolvableUUID(value)
            except ValueError:
                raise exceptions.ValidationError(
                    self.error_messages['invalid'],
                    code='invalid',
                    params={'value': value},
                )
        return value
    """

    def from_db_value(self, value, expression, connection):
        if isinstance(value, uuid.UUID):
            return URLResolvableUUID(value.hex)
        return value
