import rest_framework

if rest_framework.__version__ >= '3.0.0':
    def add_field_to_serializer(class_, field_name, field):
        class_._declared_fields[field_name] = field
else:
    def add_field_to_serializer(class_, field_name, field):
        class_.base_fields[field_name] = field
