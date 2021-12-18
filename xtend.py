from typing import Tuple, Union, List, Optional, NoReturn
from dataclasses import dataclass
import re


class Scanner:
    tokens = {
        'keyword': r'IF|ELSE|ELIF|FOR|IN|END|SEPERATOR',
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
            raise XtendParseException(self, '{')

    def scan(self):
        results = []
        while True:
            token, value = self.next()
            if token is None:
                break
            results.append((token, value))
        self.end()
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


StmtNode = Union['IfNode', 'ForNode', 'ExprNode', str]


@dataclass(frozen=True)
class XtendNode():
    stmts: List[StmtNode]


@dataclass(frozen=True)
class IfNode():
    if_branches: List[Tuple[str, StmtNode]]
    else_branch: Optional[StmtNode] = None


@dataclass(frozen=True)
class ForNode():
    var: str
    list_expr: str
    body: StmtNode
    seperator_expr: Optional[str] = None


@dataclass(frozen=True)
class ExprNode():
    expr: str


class Parser():
    def __init__(self, input):
        self.scanner = Scanner(input)
        self._lookahead = None

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
        if token != 'keyword' and value != keyword:
            self.fail(expected=keyword, got=token)

    def parse_code(self) -> str:
        token, value = self._next()
        if token == 'code':
            return value
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

    def parse_xtend(self) -> XtendNode:
        stmts = []
        while self._peek()[0]:
            stmts.append(self.parse_stmt())
        self.scanner.end()
        return XtendNode(stmts=stmts)

    def parse_stmt(self) -> StmtNode:
        # stmt -> string | if | for | expr
        token, value = self._peek()
        if token == 'keyword':
            if value == 'IF':
                return self.parse_if()

            if value == 'FOR':
                return self.parse_for()

            self.fail(expected=['IF', 'FOR'], got=token)

        if token in ['string', 'indent', 'newline']:
            return self.parse_string()

        if token == 'code':
            return self.parse_expr()

        self.fail(expected=['IF', 'FOR', 'string', 'code'], got=token)

    def parse_expr(self) -> ExprNode:
        return ExprNode(expr=self.parse_code())

    def parse_if(self) -> IfNode:
        # if -> IF CODE stmt (ELIF CODE stmt)* (ELSE stmt)? END
        if_branches: List[Tuple[str, StmtNode]] = []
        self.parse_keyword('IF')
        if_branches.append((self.parse_code(), self.parse_stmt()))
        else_branch: StmtNode = None

        while True:
            token, value = self._peek()
            if token == 'keyword':
                if value == 'ELIF':
                    self._next()
                    if_branches.append((self.parse_code(), self.parse_stmt()))
                    continue
                elif value == 'ELSE':
                    self._next()
                    else_branch = self.parse_stmt()
                    break
                elif value == 'END':
                    break

                raise NotImplementedError()  # pragma: no cover

        self.parse_keyword('END')

        return IfNode(if_branches=if_branches, else_branch=else_branch)

    def parse_for(self) -> ForNode:
        # for -> FOR code IN code (SEPERATOR code)? stmt END
        self.parse_keyword('FOR')
        var = self.parse_code()
        self.parse_keyword('IN')
        list_expr = self.parse_code()
        body = self.parse_stmt()
        self.parse_keyword('END')

        return ForNode(var=var, list_expr=list_expr, body=body)


def parse(input: str) -> XtendNode:
    return Parser(input).parse_xtend()
