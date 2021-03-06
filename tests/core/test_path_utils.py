from flex.serializers.core import ParameterSerializer
from flex.paths import (
    get_parameter_names_from_path,
    path_to_pattern,
)
from flex.constants import (
    INTEGER,
    STRING,
    PATH,
)


ID_IN_PATH = {
    'name': 'id', 'in': PATH, 'description': 'id', 'type': INTEGER, 'required': True,
}
USERNAME_IN_PATH = {
    'name': 'username', 'in': PATH, 'description': 'username', 'type': STRING, 'required': True
}


#
# get_parameter_names_from_path tests
#
def test_non_parametrized_path_returns_empty():
    path = "/get/with/no-parameters"
    names = get_parameter_names_from_path(path)
    assert len(names) == 0


def test_getting_names_from_parametrized_path():
    path = "/get/{username}/also/{with_underscores}/and/{id}"
    names = get_parameter_names_from_path(path)
    assert len(names) == 3
    assert ("username", "with_underscores", "id") == names


#
# path_to_pattern tests
#
def test_undeclared_api_path_parameters_are_skipped():
    """
    Test that parameters that are declared in the path string but do not appear
    in the parameter definitions are ignored.
    """
    path = '/get/{username}/posts/{id}/'
    serializer = ParameterSerializer(many=True, data=[
        ID_IN_PATH,
    ])
    assert serializer.is_valid(), serializer.errors
    parameters = serializer.object
    pattern = path_to_pattern(path, parameters)
    assert pattern == '^/get/\{username\}/posts/(?P<id>.+)/$'
