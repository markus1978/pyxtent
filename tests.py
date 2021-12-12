import pytest

from xtend import Scanner, parse


@pytest.mark.parametrize('input, output', [
    pytest.param('class', 'string', id='string'),
    pytest.param('s {c}:', 'string, code, string', id='expr'),
    pytest.param(
        'class name{IF base}(base){END}:',
        'string, keyword, code, string, keyword, string', id='if'),
    pytest.param(
        '    {FOR item IN list}\n',
        'indent, keyword, code, keyword, code, nl',
        id='with-white-space'
    ),
    pytest.param('1{{2}}3', 'string', id='escape')
])
def test_scanner(input: str, output: str):
    result_output = [token for token, _ in Scanner(input).scan()]
    expected_output = [token.strip() for token in output.split(',')]
    assert result_output == expected_output


@pytest.mark.parametrize('input, output', [
    pytest.param('class', 'string', id='string'),
    pytest.param('class {name}:', 'string, expr, string', id='expr'),
    pytest.param('class name{IF base}(base){END}:', 'string, if, string', id='if'),
    pytest.param('{IF c}s{ELIF c}s{END}', 'if', id='if-elif'),
    pytest.param('{IF c}s{ELSE}s{END}', 'if', id='if-else'),
    pytest.param('{IF c}s{ELSE}s{ELSE}s{END}', None, id='if-double-else'),
    pytest.param('{IF c}s{ELSE}s', None, id='if-no-end'),
    pytest.param('{IF c}{END}', None, id='if-no-stmt'),
    pytest.param('{IF }s{END}', None, id='if-no-code'),
    pytest.param('{IF c}s{ELIF c}{END}', None, id='elif-no-stmt'),
    pytest.param('{IF c}s{ELSE}{END}', None, id='else-no-stmt'),
    pytest.param('{FOR item IN list}{item}{END}', 'for', id='for'),
])
def test_parser(input: str, output: str):
    if output is None:
        with pytest.raises(Exception):
            list(parse(input))
        return

    result_output = [token for token, _ in parse(input)]
    expected_output = [token.strip() for token in output.split(',')]
    assert result_output == expected_output
