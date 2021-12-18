from typing import Tuple, Union, List, Optional, NoReturn
from dataclasses import dataclass
import re
import inspect


def strip(str) -> str:
    return inspect.cleandoc(str)


class Scanner:
    tokens = {
        'keyword': r'IF|ELSE|ELIF|FOR|IN|END|SEPARATOR',
        'open': r'(?<!{){(?!{)',
        'close': r'(?<!})}(?!})',
        'newline': r'\n',
        'indent': r'    |\t',
        'other': r'.'
    }

    token_pattern = re.compile('|'.join([
        f'(?P<{name}>{expr})' for name, expr in tokens.items()
    ]))

    state_string = 'string'
    state_xtend = 'xtend'

    def __init__(self, input):
        self.input = input
        self.stream = self.token_pattern.finditer(input)
        self._lookahead = None
        self.state = 'string'
        self.position = 0, 0

    def _next(self) -> Tuple[str, str]:
        if self._lookahead:
            next_item = self._lookahead
            self._lookahead = None
            return next_item
        match = next(self.stream, None)
        if match:
            self.position = match.span()
            return match.lastgroup, match.group()
        return None, None

    def _peek(self) -> Tuple[str, str]:
        if not self._lookahead:
            self._lookahead = self._next()
        return self._lookahead

    def next(self) -> Tuple[str, str]:
        token, value = self._next()
        if self.state == self.state_string:
            if token in ['other', 'keyword']:
                values = [value]
                while self._peek()[0] in ['other', 'keyword']:
                    _, value = self._next()
                    values.append(value)
                return 'string', ''.join(values)

            if token in ['newline', 'indent']:
                return (token, value)

            if token == 'open':
                self.state = self.state_xtend
                return self.next()

        if self.state == self.state_xtend:
            if token in ['other', 'newline', 'indent']:
                values = [value]
                while self._peek()[0] in ['other', 'newline', 'indent']:
                    _, value = self._next()
                    values.append(value)
                code_value = (''.join(values)).strip()
                if code_value != '':
                    return 'code', ''.join(values)
                return self.next()

            if token == 'keyword':
                return token, value

            if token == 'close':
                self.state = 'string'
                return self.next()

        if token is None:
            return None, None

        raise NotImplementedError()  # pragma: no cover

    def end(self):
        if self.state == self.state_xtend:
            raise XtendParseException(self, '}')


def scan(input):
    scanner = Scanner(input)
    results = []
    while True:
        token, value = scanner.next()
        if token is None:
            break
        results.append((token, value))
    scanner.end()
    return results


class XtendParseException(Exception):
    def __init__(self, scanner: Scanner, expected: Union[str, List[str]], got: str = None):
        self.scanner = scanner
        self.position = scanner.position
        if got:
            self.msg = f'Expected {expected}, got {got}, '
        else:
            self.msg = f'Expected {expected} '
        self.msg += f'at [{self.position[0]}:{self.position[1]}]'
        super().__init__(self.msg)

    def readable_error_position(self, **kwargs):
        result = ''
        start, stop = self.position
        lines = self.scanner.input.split('\n')
        for line in lines:
            result += line + '\n'
            if start < len(line) + 1 and start >= 0:
                for pos in range(0, stop):
                    result += ' ' if pos < start else '^'
                result += '\n'
            start -= len(line) + 1
            stop -= len(line) + 1
        return result


class Context():
    remove: str = None


@dataclass(frozen=True)
class Node:
    context: Context

    def run(self, globals, locals) -> str:
        raise NotImplementedError()  # pragma: no cover


@dataclass(frozen=True)
class StmtsNode(Node):
    stmts: List[Node]

    def run(self, *args) -> str:
        return ''.join([stmt.run(*args) for stmt in self.stmts])


@dataclass(frozen=True)
class IfNode(Node):
    if_branches: List[Tuple[str, Node]]
    else_branch: Optional[Node] = None

    def run(self, *args) -> str:
        for condition, stmt in self.if_branches:
            if eval(condition, *args):
                return stmt.run(*args)
        if self.else_branch:
            return self.else_branch.run(*args)

        return ''


@dataclass(frozen=True)
class ForNode(Node):
    var: str
    list_expr: str
    body: Node
    separator_expr: Optional[str] = None

    def run(self, globals, locals) -> str:
        new_locals = dict(**locals)
        results = []
        for item in eval(self.list_expr, globals, locals):
            new_locals[self.var] = item
            results.append(self.body.run(globals, new_locals))

        if self.separator_expr:
            separator = eval(self.separator_expr, globals, locals)
        else:
            separator = ''
        return separator.join(results)


@dataclass(frozen=True)
class ExprNode(Node):
    expr: str

    def run(self, *args) -> str:
        return eval(self.expr, *args)


@dataclass(frozen=True)
class StrNode(Node):
    value: str

    def run(self, *args) -> str:
        return self.value.replace(' ', '.').replace('\n', 'R\n')


class Parser():
    def __init__(self, input: str):
        self.scanner = Scanner(input)
        self._lookahead: Tuple[str, str] = None
        self.context = Context()

    def fail(self, expected: Union[str, List[str]], got: str) -> NoReturn:
        raise XtendParseException(self.scanner, expected, got)

    def _next(self) -> Tuple[str, str]:
        if self._lookahead:
            next_item = self._lookahead
            self._lookahead = None
            return next_item
        return self.scanner.next()

    def _peek(self) -> Tuple[str, str]:
        if not self._lookahead:
            self._lookahead = self._next()
        return self._lookahead

    def parse_keyword(self, keyword: str) -> None:
        token, value = self._next()
        if token != 'keyword' or value != keyword:
            self.fail(expected=keyword, got=token)

    def parse_code(self) -> str:
        token, value = self._next()
        if token == 'code':
            return value.strip()
        self.fail(expected='code', got=token)

    def parse_string(self) -> str:
        string_value = []
        while True:
            token, value = self._peek()
            if token in ['string', 'indent', 'newline']:
                self._next()
                string_value.append(value)

            else:
                return ''.join(string_value)

    def parse_xtend(self) -> StmtsNode:
        stmts = self.parse_stmts()
        token, value = self._next()
        if token is not None:
            self.fail('end', value if token == 'keyword' else token)
        self.scanner.end()
        return stmts

    def parse_stmts(self, allow_empty=False) -> StmtsNode:
        stmts: List[Node] = []
        while True:
            token, value = self._peek()
            if token == 'keyword' and value in ['ELIF', 'ELSE', 'END']:
                break
            if token is None:
                break
            stmts.append(self.parse_stmt())

        if not allow_empty:
            if len(stmts) == 0:
                self.fail(expected=['string', 'code'], got=token)
        return StmtsNode(context=self.context, stmts=stmts)

    def parse_stmt(self) -> Node:
        # stmt -> string | if | for | expr
        token, value = self._peek()
        if token == 'keyword':
            if value == 'IF':
                return self.parse_if()

            if value == 'FOR':
                return self.parse_for()

        if token in ['string', 'indent', 'newline']:
            return StrNode(context=self.context, value=self.parse_string())

        if token == 'code':
            return self.parse_expr()

        raise NotImplementedError()  # pragma: no cover

    def parse_expr(self) -> ExprNode:
        return ExprNode(context=self.context, expr=self.parse_code())

    def parse_if(self) -> IfNode:
        # if -> IF CODE stmt (ELIF CODE stmt)* (ELSE stmt)? END
        if_branches: List[Tuple[str, Node]] = []
        self.parse_keyword('IF')
        if_branches.append((self.parse_code(), self.parse_stmts()))
        else_branch: Node = None

        while True:
            token, value = self._peek()
            if token == 'keyword':
                if value == 'ELIF':
                    self._next()
                    if_branches.append((self.parse_code(), self.parse_stmts()))
                    continue

                if value == 'ELSE':
                    self._next()
                    else_branch = self.parse_stmts()
                    break

                if value == 'END':
                    break

                raise NotImplementedError()  # pragma: no cover

        self.parse_keyword('END')

        return IfNode(
            context=self.context, if_branches=if_branches, else_branch=else_branch)

    def parse_for(self) -> ForNode:
        # for -> FOR code IN code (SEPARATOR code)? stmt END
        self.parse_keyword('FOR')
        var = self.parse_code()
        self.parse_keyword('IN')
        list_expr = self.parse_code()
        token, value = self._peek()
        if token == 'keyword' and value == 'SEPARATOR':
            self.parse_keyword('SEPARATOR')
            separator_expr = self.parse_code()
        else:
            separator_expr = None
        body = self.parse_stmts()
        self.parse_keyword('END')

        return ForNode(
            context=self.context, var=var, list_expr=list_expr, body=body,
            separator_expr=separator_expr)


def parse(input: str) -> StmtsNode:
    return Parser(input).parse_xtend()


def xtend(input: str, globals: dict = None, locals: dict = None) -> str:
    if globals is None:
        globals = inspect.currentframe().f_back.f_globals
    if locals is None:
        locals = inspect.currentframe().f_back.f_locals
    return parse(input).run(globals, locals)
