import copy

import rest_framework

from flex.compat.fields import DRFFieldShim

if rest_framework.__version__ >= '3.0.0':
    from rest_framework.utils import representation
    from rest_framework import serializers

    def add_field_to_serializer(class_, field_name, field):
        class_._declared_fields[field_name] = field

    def make_serializer_repr_safe(serializer):
        """
        Since some of the serializers have recursive fields on them
        (`SchemaSerializer`), we need to avoid infinite recursion while
        trying to repr them.
        """
        serializer_copy = copy.deepcopy(serializer)

        for field_name in serializer_copy.fields.keys():
            field = serializer_copy.fields[field_name]
            if hasattr(field, 'child'):
                field = field.child
            if getattr(field, '_unsafe_to_repr', False):
                serializer_copy.fields.pop(field_name)

        return serializer_copy

    class ReprSafeListSerializer(serializers.ListSerializer):
        def __repr__(self):
            """
            Since some of the serializers have recursive fields on them
            (`SchemaSerializer`), we need to avoid infinite recursion while
            trying to repr them.
            """
            return representation.serializer_repr(
                make_serializer_repr_safe(self.child),
                indent=1,
            )


    class DRFSerializerShim(DRFFieldShim):
        def __repr__(self):
            """
            Since some of the serializers have recursive fields on them
            (`SchemaSerializer`), we need to avoid infinite recursion while
            trying to repr them.
            """
            return representation.serializer_repr(
                make_serializer_repr_safe(self),
                indent=1,
            )

        class Meta:
            list_serializer_class = ReprSafeListSerializer

    def bind_field(field, field_name, parent):
        """
        This is a noop since the `BindingDict` class in DRF-3 does the binding.
        """
        return
else:
    def add_field_to_serializer(class_, field_name, field):
        class_.base_fields[field_name] = field

    class DRFSerializerShim(DRFFieldShim):
        @property
        def validated_data(self):
            return self.object

    def bind_field(field, field_name, parent):
        field.initialize(parent, field_name)
