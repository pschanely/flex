import functools

from django.core.exceptions import ValidationError

from flex.utils import chain_reduce_partial
from flex.context_managers import ErrorCollection
from flex.validation.operation import (
    construct_operation_validators,
    validate_operation,
)
from flex.validation.common import (
    validate_request_method_to_operation,
    validate_path_to_api_path,
)
from flex.http import normalize_request


def validate_request(request, paths, base_path, context, inner=False):
    """
    Request validation does the following steps.

       1. validate that the path matches one of the defined paths in the schema.
       2. validate that the request method conforms to a supported methods for the given path.
       3. validate that the request parameters conform to the parameter
          definitions for the operation definition.
    """
    with ErrorCollection(inner=inner) as errors:
        # 1
        try:
            api_path = validate_path_to_api_path(
                request=request,
                paths=paths,
                base_path=base_path,
                context=context,
            )
        except ValidationError as err:
            errors['path'].extend(list(err.messages))
            return  # this causes an exception to be raised since errors is no longer falsy.

        path_definition = paths[api_path] or {}

        if not path_definition:
            # TODO: is it valid to not have a definition for a path?
            return

        # 2
        try:
            operation_definition = validate_request_method_to_operation(
                request_method=request.method,
                path_definition=path_definition,
            )
        except ValidationError as err:
            errors['method'].append(err.message)
            return

        if operation_definition is None:
            # TODO: is this compliant with swagger, can path operations have a null
            # definition?
            return

        # 3
        operation_validators = construct_operation_validators(
            api_path=api_path,
            path_definition=path_definition,
            operation_definition=operation_definition,
            context=context,
        )
        try:
            validate_operation(request, operation_validators, inner=True)
        except ValidationError as err:
            errors['method'].append(err.messages)

    return operation_definition


def generate_request_validator(schema, **kwargs):
    request_validator = functools.partial(
        validate_request,
        paths=schema['paths'],
        base_path=schema.get('basePath', ''),
        context=schema,
        **kwargs
    )
    return chain_reduce_partial(
        normalize_request,
        request_validator,
    )
