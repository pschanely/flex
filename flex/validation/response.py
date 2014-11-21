import functools
import operator

from django.core.exceptions import ValidationError

from flex.utils import chain_reduce_partial
from flex.context_managers import ErrorCollection
from flex.validation.common import validate_object
from flex.validation.schema import construct_schema_validators
from flex.error_messages import MESSAGES
from flex.paths import (
    match_path_to_api_path,
)
from flex.constants import (
    EMPTY,
)
from flex.validation.header import (
    construct_header_validators,
)
from flex.http import Response


def validate_response_to_path(response, paths, base_path, context):
    """
    Given a response, check whether the path of the response matches any if the
    api paths.  Note that this does not do deep validation on the path
    parameters themselves, but only matches whether the response path *looks*
    like an api path.

    If so, return the api path and the path definitions.
    """
    try:
        api_path = match_path_to_api_path(
            path_definitions=paths,
            path=request.path,
            base_path=base_path,
        )
    except LookupError:
        raise ValidationError(MESSAGES['path']['unknown_path'])

    path_definition = paths[api_path] or {}
    return api_path, path_definition


def validate_status_code_to_response_definition(response, operation_definition):
    """
    Given a response, validate that the response status code is in the accepted
    status codes defined by this endpoint.

    If so, return the response definition that corresponds to the status code.
    """
    status_code = response.status_code
    operation_responses = operation_definition['responses']
    try:
        response_definition = operation_responses[status_code]
    except KeyError:
        raise ValidationError(
            MESSAGES['response']['invalid_status_code'].format(
                status_code, operation_responses.keys(),
            ),
        )
    return response_definition


def generate_response_body_validator(schema, context, **kwargs):
    validators = construct_schema_validators(schema, context=context)
    return chain_reduce_partial(
        operator.attrgetter('data'),
        functools.partial(
            validate_object,
            validators=validators,
            inner=True,
        ),
    )


def generate_response_header_validator(headers, context, **kwargs):
    validators = {}
    for key, header_definition in headers.items():
        header_validator = functools.partial(
            validate_object,
            validators=construct_header_validators(header_definition, context=context),
            inner=True,
        )
        # Chain the individual header validation function with a methodcaller
        # that will fetch the header with
        # `response.headers.get(header_name, EMPTY)`
        # and then feed that into the validation function.
        validators[key] = chain_reduce_partial(
            operator.methodcaller('get', key, EMPTY),
            header_validator,
        )
    return chain_reduce_partial(
        operator.attrgetter('headers'),
        functools.partial(validate_object, validators=validators, inner=True),
    )


def validate_response_content_type(response, content_types):
    assert isinstance(response, Response)  # TODO: remove this sanity check
    if response.content_type not in content_types:
        raise ValidationError(
            'Invalid content type `{0}`.  Must be one of `{1}`.'.format(
                response.content_type, content_types,
            ),
        )


def generate_response_content_type_validator(produces, **kwargs):
    return functools.partial(
        validate_response_content_type,
        content_types=produces,
    )


validator_mapping = {
    'produces': generate_response_content_type_validator,
    'schema': generate_response_body_validator,
    'headers': generate_response_header_validator,
}


def generate_response_validator(operation_definition, response_definition, context):
    validators = {}
    for key in validator_mapping:
        if key in response_definition:
            validators[key] = validator_mapping[key](context=context, **response_definition)
        elif key in operation_definition:
            validators[key] = validator_mapping[key](context=context, **operation_definition)

    if 'produces' in context and 'produces' not in validators:
        validators['produces'] = generate_response_content_type_validator(**context)

    return functools.partial(
        validate_object,
        validators=validators,
        inner=True,
    )


def validate_response(response, operation_definition, context, inner=False):
    """
    Response validation involves the following steps.
       4. validate that the response status_code is in the allowed responses for
          the request method.
       5. validate that the response content validates against any provided
          schemas for the responses.
       6. headers, content-types, etc..., ???
    """
    with ErrorCollection(inner=inner) as errors:
        # 1
        try:
            api_path, path_definition = validate_response_to_path(
                response=response,
                paths=context['paths'],
                base_path=context.get('basePath', ''),
                context=context,
            )
        except ValidationError as err:
            errors['path'].extend(list(err.messages))
            return  # this causes an exception to be raised since errors is no longer falsy.

        # 4
        try:
            response_definition = validate_status_code_to_response_definition(
                response=response,
                operation_definition=operation_definition,
            )
        except ValidationError as err:
            errors['status_code'].append(err.message)
        else:
            # 5
            response_validator = generate_response_validator(
                operation_definition=operation_definition,
                response_definition=response_definition,
                context=context,
            )
            try:
                response_validator(response)
            except ValidationError as err:
                errors['body'].extend(err.messages)

        # 6
        # TODO
