import rest_framework

if rest_framework.__version__ >= '3.0.0':
    from rest_framework import fields
    ListField = fields.ListField
    WritableField = rest_framework.fields.Field

else:
    from drf_compound_fields.fields import ListField as BaseListField
    from rest_framework.fields import WritableField  # NOQA

    class ListField(BaseListField):
        def __init__(self, *args, **kwargs):
            kwargs['item_field'] = kwargs.pop('child', None)
            super(ListField, self).__init__(*args, **kwargs)
