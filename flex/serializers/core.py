from __future__ import unicode_literals

import functools
import six

from rest_framework import serializers

from flex.compat.fields import (
    ListField,
    CharField,
    NullBooleanField,
)
from flex.compat.serializers import (
    add_field_to_serializer,
    DRFSerializerShim,
)
from flex.exceptions import (
    ValidationError,
    ErrorDict,
)
from flex.context_managers import ErrorCollection
from flex.serializers.fields import (
    SecurityRequirementReferenceField,
)
from flex.serializers.common import (
    HomogenousDictSerializer,
    BaseResponseSerializer,
    BaseParameterSerializer,
    BaseSchemaSerializer,
    BaseItemsSerializer,
    BaseHeaderSerializer,
)
from flex.serializers.validators import (
    host_validator,
    path_validator,
    scheme_validator,
    mimetype_validator,
    string_type_validator,
)
from flex.constants import (
    PATH,
    REQUEST_METHODS,
)
from flex.validation.common import (
    validate_object,
)
from flex.validation.schema import (
    construct_schema_validators,
)
from flex.paths import (
    get_parameter_names_from_path,
)
from flex.parameters import (
    filter_parameters,
    merge_parameter_lists,
    dereference_parameter_list,
)
from flex.error_messages import MESSAGES


class InfoSerializer(serializers.Serializer):
    """
    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#infoObject
    """
    title = serializers.CharField()
    description = CharField(allow_null=True, required=False)
    termsOfService = CharField(allow_null=True, required=False)
    contact = CharField(allow_null=True, required=False)
    license = CharField(allow_null=True, required=False)
    version = CharField(allow_null=True, required=False)


class ItemsSerializer(BaseItemsSerializer):
    default_error_messages = {
        'unknown_reference': 'Unknown definition reference `{0}`',
    }

    def from_native(self, data, files):
        if isinstance(data, six.string_types):
            definitions = self.context.get('definitions', {})
            if data not in definitions:
                raise ValidationError(
                    self.error_messages['unknown_reference'].format(data),
                )
            return data
        return super(ItemsSerializer, self).from_native(data, files)


class HeaderSerializer(BaseHeaderSerializer):
    items = ItemsSerializer(allow_null=True, required=False, many=True)


class HeadersSerializer(HomogenousDictSerializer):
    """
    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#headersObject
    """
    value_serializer_class = HeaderSerializer


class SchemaSerializer(BaseSchemaSerializer):
    default_error_messages = {
        'unknown_reference': 'Unknown definition reference `{0}`'
    }

    def validate(self, attrs):
        errors = ErrorDict()

        if '$ref' in attrs:
            definitions = self.context.get('definitions', {})
            if attrs['$ref'] not in definitions:
                errors['$ref'].add_error(
                    self.error_messages['unknown_reference'].format(attrs['$ref']),
                )

        if errors:
            raise ValidationError(errors)
        return super(SchemaSerializer, self).validate(attrs)

    def save_object(self, obj, **kwargs):
        validators = construct_schema_validators(obj, self.context)
        self.object = functools.partial(validate_object, validators=validators)


class ResponseSerializer(BaseResponseSerializer):
    """
    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#responseObject
    """
    schema = SchemaSerializer(allow_null=True, required=False)
    headers = HeadersSerializer(allow_null=True, required=False)
    # TODO: how do we do examples
    # examples =


class ResponsesSerializer(HomogenousDictSerializer):
    value_serializer_class = ResponseSerializer


class SecuritySerializer(HomogenousDictSerializer):
    value_serializer_class = SecurityRequirementReferenceField


class ParameterSerializer(BaseParameterSerializer):
    schema = SchemaSerializer(allow_null=True, required=False)
    items = ItemsSerializer(allow_null=True, required=False, many=True)

    @property
    def many(self):
        return True

    @many.setter
    def many(self, value):
        pass

    def to_internal_value(self, data, files=None):
        if isinstance(data, six.string_types):
            try:
                self.validate_reference(data)
            except ValidationError as err:
                assert not getattr(self, '_errors', False)
                self._errors = {}
                self._errors['non_field_errors'] = self._errors.get(
                    'non_field_errors', [],
                ) + (err.messages or getattr(err, 'detail', None))
                return
            else:
                return data
        return super(ParameterSerializer, self).from_native(data, files)

    def validate_reference(self, reference):
        if reference not in self.context.get('parameters', {}):
            raise ValidationError(
                MESSAGES['unknown_reference']['parameter'].format(reference),
            )


class OperationSerializer(DRFSerializerShim, serializers.Serializer):
    """
    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#operationObject
    """
    tags = ListField(
        allow_null=True, required=False,
        child=serializers.CharField(validators=[string_type_validator]),
    )
    summary = CharField(allow_null=True, required=False)
    description = CharField(allow_null=True, required=False)
    externalDocs = CharField(allow_null=True, required=False)
    operationId = CharField(allow_null=True, required=False)
    consumes = ListField(
        allow_null=True, required=False,
        child=serializers.CharField(validators=[mimetype_validator]),
    )
    produces = ListField(
        allow_null=True, required=False,
        child=serializers.CharField(validators=[mimetype_validator]),
    )
    parameters = ParameterSerializer(allow_null=True, required=False, many=True)
    responses = ResponsesSerializer()
    schemes = ListField(
        allow_null=True, required=False,
        child=serializers.CharField(validators=[scheme_validator]),
    )
    deprecated = NullBooleanField(required=False)
    security = SecuritySerializer(allow_null=True, required=False)


class PathItemSerializer(DRFSerializerShim, serializers.Serializer):
    """
    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#pathsObject
    """
    # TODO. reference path item objects from definitions.
    # TODO. how is this supposted to work.  The swagger spec doesn't account
    # for a definitions location for PathItem definitions?
    # _ref = serializers.CharField(source='$ref')
    get = OperationSerializer(allow_null=True, required=False)
    put = OperationSerializer(allow_null=True, required=False)
    post = OperationSerializer(allow_null=True, required=False)
    delete = OperationSerializer(allow_null=True, required=False)
    options = OperationSerializer(allow_null=True, required=False)
    head = OperationSerializer(allow_null=True, required=False)
    patch = OperationSerializer(allow_null=True, required=False)
    # TODO: these can be a parameters reference object.
    parameters = ParameterSerializer(allow_null=True, required=False, many=True)


class TagSerializer(DRFSerializerShim, serializers.Serializer):
    """
    https://github.com/wordnik/swagger-spec/blob/master/versions/2.0.md#tagObject
    """
    name = serializers.CharField()
    description = CharField(allow_null=True, required=False)
    externalDocs = CharField(allow_null=True, required=False)


class PropertiesSerializer(HomogenousDictSerializer):
    value_serializer_class = SchemaSerializer


# These fields include recursive use of the `SchemaSerializer` so they have to
# be attached after the `SchemaSerializer` class has been created.
add_field_to_serializer(
    SchemaSerializer,
    'properties',
    PropertiesSerializer(allow_null=True, required=False),
)
add_field_to_serializer(
    SchemaSerializer,
    'items',
    ItemsSerializer(allow_null=True, required=False, many=True),
)
add_field_to_serializer(
    SchemaSerializer,
    'allOf',
    SchemaSerializer(allow_null=True, required=False, many=True),
)


class PathsSerializer(HomogenousDictSerializer):
    value_serializer_class = PathItemSerializer
    value_serializer_kwargs = {'allow_null': True}
    allow_empty = True

    def validate(self, attrs):
        with ErrorCollection(inner=True) as errors:
            for api_path, path_definition in attrs.items():
                path_parameter_names = set(get_parameter_names_from_path(api_path))

                if path_definition is None:
                    continue

                api_path_level_parameters = dereference_parameter_list(
                    path_definition.get('parameters', []),
                    parameter_definitions=self.context.get('parameters', {}),
                )

                path_request_methods = set(REQUEST_METHODS).intersection(
                    path_definition.keys(),
                )

                if not path_request_methods:
                    for parameter in api_path_level_parameters:
                        if parameter['name'] not in path_parameter_names:
                            errors[api_path].add_error(
                                MESSAGES["path"]["missing_parameter"].format(
                                    parameter['name'], api_path,
                                ),
                            )

                for method, operation_definition in path_definition.items():
                    if method not in REQUEST_METHODS:
                        continue
                    if operation_definition is None:
                        operation_definition = {}
                    operation_level_parameters = dereference_parameter_list(
                        operation_definition.get('parameters', []),
                        parameter_definitions=self.context.get('parameters', {}),
                    )
                    parameters_in_path = filter_parameters(
                        merge_parameter_lists(
                            api_path_level_parameters,
                            operation_level_parameters,
                        ),
                        in_=PATH,
                    )

                    for parameter in parameters_in_path:
                        if parameter['name'] not in path_parameter_names:
                            key = "{method}:{api_path}".format(
                                method=method.upper(),
                                api_path=api_path,
                            )
                            errors[key].add_error(
                                MESSAGES["path"]["missing_parameter"].format(
                                    parameter['name'], api_path,
                                ),
                            )

        return super(PathsSerializer, self).validate(attrs)


class SwaggerSerializer(DRFSerializerShim, serializers.Serializer):
    """
    Primary Serializer for swagger schema
    """
    swagger = serializers.ChoiceField(
        choices=[
            ('2.0', '2.0'),
        ],
    )
    info = InfoSerializer()
    host = CharField(
        allow_null=True, required=False,
        validators=[host_validator],
    )
    basePath = CharField(
        allow_null=True, required=False,
        validators=[path_validator],
    )
    schemes = ListField(
        allow_null=True, required=False,
        child=serializers.CharField(validators=[scheme_validator]),
    )
    consumes = ListField(
        allow_null=True, required=False,
        child=serializers.CharField(validators=[mimetype_validator]),
    )
    produces = ListField(
        allow_null=True, required=False,
        child=serializers.CharField(validators=[mimetype_validator]),
    )

    paths = PathsSerializer()

    security = SecuritySerializer(allow_null=True, required=False)

    tags = TagSerializer(allow_null=True, required=False, many=True)
    externalDocs = CharField(allow_null=True, required=False)
