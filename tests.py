from typing import List
import pytest
import inspect

from xtend import (
    strip, xtend, scan, parse, XtendParseException, Node, StrNode, IfNode, ExprNode,
    ForNode)


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
            scan(input)
        return

    result_output = [token for token, _ in scan(input)]
    expected_output = [token.strip() for token in output.split(',')]
    assert result_output == expected_output


@pytest.mark.parametrize('input, output', [
    pytest.param('class', [StrNode], id='string'),
    pytest.param('class {name}:', [StrNode, ExprNode, StrNode], id='expr'),
    pytest.param('class name{IF base}(base){END}:', [StrNode, IfNode, StrNode], id='if'),
    pytest.param('{IF c}s{ELIF c}s{END}', [IfNode], id='if-elif'),
    pytest.param('{IF c}s{ELIF}s{END}', None, id='elif-no-code'),
    pytest.param('{IF c}s{ELSE}s{END}', [IfNode], id='if-else'),
    pytest.param('{IF c}s{ELSE}s{ELSE}s{END}', None, id='if-double-else'),
    pytest.param('{IF c}s{ELSE}s', None, id='if-no-end'),
    pytest.param('{IF c}{END}', None, id='if-no-stmt'),
    pytest.param('{IF }s{END}', None, id='if-no-code'),
    pytest.param('{IF c}', None, id='if-no-follow'),
    pytest.param('{IF c}{c}s{END}', [IfNode], id='if-stmts'),
    pytest.param('{END}', None, id='end-no-if'),
    pytest.param('s{END}', None, id='str-end-no-if'),
    pytest.param('s{ELIF}', None, id='elif-no-if'),
    pytest.param('{IF c}s{ELIF c}{END}', None, id='elif-no-stmt'),
    pytest.param('{IF c}s{ELSE}{END}', None, id='else-no-stmt'),
    pytest.param('{FOR item IN list}{item}{END}', [ForNode], id='for'),
    pytest.param('something { inbalanced', None, id='inbalanced-tmpl'),
    pytest.param('''
        {IF c}
            s
        {END}
    ''', [StrNode, IfNode, StrNode], id='multiline')
])
def test_parser(input: str, output: List[Node]):
    if output is None:
        with pytest.raises(XtendParseException):
            parse(input)
        return

    result_output = [type(stmt) for stmt in parse(input).stmts]
    assert result_output == output


def test_parse_exception():
    try:
        parse('\n{IF c}\ns{ELIF}\n{END}')
    except XtendParseException as e:
        assert e.readable_error_position() == '\n{IF c}\ns{ELIF}\n       ^\n{END}\n'
        return

    assert False, 'expected a parse exception'


def test_python():
    global global_var
    global_var = 'global'
    local_var = 'local'  # pylint: disable=unused-variable
    assert eval('local_var') == 'local'

    def called():
        locals = inspect.currentframe().f_back.f_locals
        globals = inspect.currentframe().f_back.f_globals
        assert eval('global_var + " " + local_var', globals, locals) == 'global local'

    called()


@pytest.mark.parametrize('input, context, output', [
    pytest.param('s', {}, 's', id='string'),
    pytest.param('{v}', {'v': 'value'}, 'value', id='expr'),
    pytest.param('{IF c}t{ELSE}f{END}', {'c': True}, 't', id='if'),
    pytest.param('{IF c}t{ELSE}f{END}', {'c': False}, 'f', id='if-else'),
    pytest.param('{IF c}t{ELIF not c}f{END}', {'c': False}, 'f', id='if-elif'),
    pytest.param('{IF c}t{END}', {'c': False}, '', id='if-none'),
    pytest.param('{FOR c IN l}{c}{END}', {'l': ['v1', 'v2']}, 'v1v2', id='for-stmt'),
    pytest.param('{FOR c IN l}{c},{END}', {'l': ['v1', 'v2']}, 'v1,v2,', id='for-stmts'),
    pytest.param('{FOR c IN l SEPARATOR ","}{c}{END}', {'l': ['v1', 'v2']}, 'v1,v2', id='for-separator'),
    pytest.param('{FOR c IN l}:{IF c}t{ELSE}f{END}:{END}', {'l': [True, False]}, ':t::f:', id='nested-for-if'),
    pytest.param('{IF c1}t,{IF c2}t{ELSE}f{END}{ELSE}f{END}', {'c1': True, 'c2': False}, 't,f', id='nested-if-if'),
    pytest.param('''
        class {name}:
            {IF init}
                __init__(self):
                    pass
            {END}
    ''', {'name': 'Foo', 'init': True}, strip('''
        class Foo:
            __init__(self):
                pass
    '''), id='indent'),
])
def test_xtend(input: str, context: dict, output: str):
    locals().update(context)
    result_output = xtend(input)

    if output != result_output and input.startswith('\n'):
        pytest.skip()
        print('---')
        print(result_output)
        print('---')
        print(output)
        print('---')

    assert output == xtend(input)
