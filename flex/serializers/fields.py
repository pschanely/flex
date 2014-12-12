from rest_framework import serializers

from flex.compat.fields import (
    WritableField,
    CharField,
)
from flex.exceptions import ValidationError
from flex.utils import is_non_string_iterable
from flex.serializers.mixins import TranslateValidationErrorMixin


class MaybeListCharField(TranslateValidationErrorMixin, CharField):
    def to_internal_value(self, value):
        if is_non_string_iterable(value):
            return value
        return super(MaybeListCharField, self).to_internal_value(value)


class DefaultValueField(WritableField):
    def to_internal_value(self, value):
        return value


class SecurityRequirementReferenceField(serializers.CharField):
    """
    Field that references a defined security scheme declared in the Security
    Definitions.
    """
    default_error_messages = {
        'unknown_reference': "Unknown Security Scheme reference `{0}`",
    }

    def validate(self, value):
        if value not in self.context.get('securityDefinitions', {}):
            raise ValidationError(
                self.error_messages['unknown_reference'].format(value)
            )
