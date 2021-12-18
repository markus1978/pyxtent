from _pytest.python_api import raises
import pytest

from xtend import Scanner, parse, XtendParseException


@pytest.mark.parametrize('input, output', [
    pytest.param('class', 'string', id='string'),
    pytest.param('s {c}:', 'string, code, string', id='expr'),
    pytest.param(
        'class name{IF base}(base){END}:',
        'string, keyword, code, string, keyword, string', id='if'),
    pytest.param(
        '    {FOR item IN list}\n',
        'indent, keyword, code, keyword, code, newline',
        id='with-white-space'
    ),
    pytest.param('1{{2}}3', 'string', id='escape'),
    pytest.param('inbalanced { inbalanced', None, id='inbalanced')
])
def test_scanner(input: str, output: str):
    if output is None:
        with pytest.raises(XtendParseException):
            Scanner(input).scan()
        return

    result_output = [token for token, _ in Scanner(input).scan()]
    expected_output = [token.strip() for token in output.split(',')]
    assert result_output == expected_output


@pytest.mark.parametrize('input, output', [
    pytest.param('class', 'string', id='string'),
    pytest.param('class {name}:', 'string, expr, string', id='expr'),
    pytest.param('class name{IF base}(base){END}:', 'string, if, string', id='if'),
    pytest.param('{IF c}s{ELIF c}s{END}', 'if', id='if-elif'),
    pytest.param('{IF c}s{ELIF}s{END}', None, id='elif-no-code'),
    pytest.param('{IF c}s{ELSE}s{END}', 'if', id='if-else'),
    pytest.param('{IF c}s{ELSE}s{ELSE}s{END}', None, id='if-double-else'),
    pytest.param('{IF c}s{ELSE}s', None, id='if-no-end'),
    pytest.param('{IF c}{END}', None, id='if-no-stmt'),
    pytest.param('{IF }s{END}', None, id='if-no-code'),
    pytest.param('{IF c}', None, id='if-no-follow'),
    pytest.param('{END}', None, id='end-no-if'),
    pytest.param('s{END}', None, id='end-no-if'),
    pytest.param('s{ELIF}', None, id='elif-no-if'),
    pytest.param('{IF c}s{ELIF c}{END}', None, id='elif-no-stmt'),
    pytest.param('{IF c}s{ELSE}{END}', None, id='else-no-stmt'),
    pytest.param('{FOR item IN list}{item}{END}', 'for', id='for'),
    pytest.param('something { inbalanced', None, id='inbalanced-tmpl'),
    pytest.param('''
        {IF c}
            s
        {END}
    ''', 'string, if, string', id='multiline')
])
def test_parser(input: str, output: str):
    if output is None:
        with pytest.raises(XtendParseException):
            list(parse(input))
        return

    result_output = [token for token, _ in parse(input)]
    expected_output = [token.strip() for token in output.split(',')]
    assert result_output == expected_output


def test_parse_exception():
    try:
        list(parse('\n{IF c}\ns{ELIF}\n{END}'))
    except XtendParseException as e:
        assert e.readable_error_position() == '\n{IF c}\ns{ELIF}\n       ^\n{END}\n'
        return

    assert False, 'expected a parse exception'
