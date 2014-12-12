import rest_framework

if rest_framework.__version__ >= '3.0.0':
    from rest_framework import fields

    ListField = fields.ListField
    CharField = fields.CharField
    NullBooleanField = fields.NullBooleanField
    FloatField = fields.FloatField
    IntegerField = fields.IntegerField
    WritableField = fields.Field

    empty = fields.empty

    class DRFFieldShim(object):
        pass
else:
    from drf_compound_fields.fields import ListField as BaseListField
    from rest_framework.fields import (
        WritableField as BaseWritableField,
        CharField as BaseCharField,
        FloatField as BaseFloatField,
        BooleanField as BaseBooleanField,
        IntegerField as BaseIntegerField,
    )

    empty = None

    class DRFFieldShim(object):
        def __init__(self, *args, **kwargs):
            kwargs.pop('allow_null', None)
            super(DRFFieldShim, self).__init__(*args, **kwargs)

        def to_internal_value(self, *args, **kwargs):
            return self.from_native(*args, **kwargs)

        def to_representation(self, *args, **kwargs):
            return self.to_native(*args, **kwargs)

    class WritableField(DRFFieldShim, BaseWritableField):
        pass

    class CharField(DRFFieldShim, BaseCharField):
        pass

    class NullBooleanField(DRFFieldShim, BaseBooleanField):
        pass

    class FloatField(DRFFieldShim, BaseFloatField):
        pass

    class IntegerField(DRFFieldShim, BaseIntegerField):
        pass

    class ListField(DRFFieldShim, BaseListField):
        def __init__(self, *args, **kwargs):
            kwargs['item_field'] = kwargs.pop('child', None)
            super(ListField, self).__init__(*args, **kwargs)
