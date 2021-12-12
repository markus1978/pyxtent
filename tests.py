import pytest

from xtend import scan


@pytest.mark.parametrize('input, output', [
    pytest.param('class', 'string', id='string'),
    pytest.param('class {name}:', 'string, code, string', id='expr'),
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
    result_output = [token for token, _ in scan(input)]
    expected_output = [token.strip() for token in output.split(',')]
    assert result_output == expected_output
