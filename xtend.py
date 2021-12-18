from typing import Tuple, Union, List
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


class Parser():
    def __init__(self, input):
        self.scanner = Scanner(input)
        self._lookahead = None

    def fail(self, expected: Union[str, List[str]], got: str):
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

    def parse_keyword(self, keyword: str):
        token, value = self._next()
        if token != 'keyword' and value != keyword:
            self.fail(expected=keyword, got=token)

    def parse_code(self):
        token, value = self._next()
        if token == 'code':
            return 'code', value
        self.fail(expected='code', got=token)

    def parse_string(self):
        string_value = []
        while True:
            token, value = self._peek()
            if token in ['string', 'indent', 'newline']:
                self._next()
                string_value.append(value)

            else:
                return 'string', ''.join(string_value)

    def parse_xtend(self):
        while self._peek()[0]:
            yield self.parse_stmt()
        self.scanner.end()

    def parse_stmt(self):
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

    def parse_expr(self):
        return 'expr', self.parse_code()

    def parse_if(self):
        # if -> IF CODE stmt (ELIF CODE stmt)* (ELSE stmt)? END
        results = []
        self.parse_keyword('IF')
        results.append((self.parse_code(), self.parse_stmt()))

        while True:
            token, value = self._peek()
            if token == 'keyword':
                if value == 'ELIF':
                    self._next()
                    results.append((self.parse_code(), self.parse_stmt()))
                    continue
                elif value == 'ELSE':
                    self._next()
                    results.append((self.parse_stmt()))
                    break
                elif value == 'END':
                    break

                raise NotImplementedError()  # pragma: no cover

        self.parse_keyword('END')

        return 'if', results

    def parse_for(self):
        # for -> FOR code IN code (SEPERATOR code)? stmt END
        self.parse_keyword('FOR')
        item_code = self.parse_code()
        self.parse_keyword('IN')
        list_code = self.parse_code()
        stmt = self.parse_stmt()
        self.parse_keyword('END')

        return 'for', (item_code, list_code, stmt)


def parse(input: str):
    return Parser(input).parse_xtend()
