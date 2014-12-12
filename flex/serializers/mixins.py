import six

from flex.compat.fields import empty
from flex.exceptions import ValidationError
from flex.utils import is_value_of_type
from flex.decorators import (
    translate_validation_error,
)


class TypedDefaultMixin(object):
    default_error_messages = {
        'default_is_incorrect_type': (
            "The value supplied for 'default' must match the specified type."
        ),
    }

    def validate_default_type(self, attrs, errors):
        if 'default' in attrs and 'type' in attrs:
            if not is_value_of_type(attrs['default'], attrs['type']):
                errors['default'].add_error(
                    self.error_messages['default_is_incorrect_type'],
                )


class TranslateValidationErrorMixin(object):
    @translate_validation_error
    def field_from_native(self, *args, **kwargs):
        return super(TranslateValidationErrorMixin, self).field_from_native(
            *args, **kwargs
        )

    @translate_validation_error
    def validate(self, *args, **kwargs):
        return super(TranslateValidationErrorMixin, self).validate(
            *args, **kwargs
        )


class AllowStringReferenceMixin(object):
    def run_validation(self, data=empty):
        if isinstance(data, six.string_types):
            value = self.to_internal_value(data)
            if getattr(self, '_errors', False):
                raise ValidationError(self._errors)
            return value
        return super(AllowStringReferenceMixin, self).run_validation(data)
