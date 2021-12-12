from typing import Generator, Tuple, Union, List
import re


class Scanner:
    tokens = {
        'keyword': r'IF|ELSE|ELIF|FOR|IN|END|SEPERATOR',
        'open': r'(?<!{){(?!{)',
        'close': r'(?<!})}(?!})',
        'nl': r'\n',
        'indent': r'    |\t',
        'other': r'.'
    }

    token_pattern = re.compile('|'.join([
        f'(?P<{name}>{expr})' for name, expr in tokens.items()
    ]))

    def __init__(self, input):
        self.input = Scanner.token_pattern.finditer(input)
        self._lookahead = None
        self.state = 'string'
        self.position = 0

    def _next(self) -> Tuple[str, str]:
        if self._lookahead:
            next_item = self._lookahead
            self._lookahead = None
            return next_item
        match = next(self.input, None)
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
        if self.state == 'string':
            if token in ['other', 'keyword']:
                values = [value]
                while self._peek()[0] in ['other', 'keyword']:
                    _, value = self._next()
                    values.append(value)
                return 'string', ''.join(values)

            if token in ['nl', 'indent']:
                return (token, value)

            if token == 'open':
                self.state = 'xtend'
                return self.next()

        if self.state == 'xtend':
            if token in ['other', 'nl', 'indent']:
                values = [value]
                while self._peek()[0] in ['other', 'nl', 'indent']:
                    _, value = self._next()
                    values.append(value)
                return 'code', ''.join(values)

            if token == 'keyword':
                return token, value

            if token == 'close':
                self.state = 'string'
                return self.next()

        if token is None:
            return None, None

        raise NotImplementedError()

    def scan(self):
        results = []
        while True:
            token, value = self.next()
            if token is None:
                break
            results.append((token, value))
        return results


class Parser():
    def __init__(self, input):
        self.scanner = Scanner(input)
        self._lookahead = None

    def fail(self, expected=Union[str, List[str]]):
        raise Exception('cannot parse')

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
            self.fail(expected=keyword)

    def parse_code(self):
        token, value = self._next()
        if token == 'code':
            if value.strip() == '':
                self.fail(expected='code')
            return 'code', value
        self.fail(expected='code')

    def parse_string(self):
        string_value = []
        while True:
            token, value = self._peek()
            if token in ['string', 'indent', 'nl']:
                self._next()
                string_value.append(value)

            else:
                break

        if len(string_value) == 0:
            self.fail(expected='string')

        return 'string', ''.join(string_value)

    def parse_xtend(self):
        while self._peek()[0]:
            yield self.parse_stmt()

    def parse_stmt(self):
        # stmt -> string | if | for | expr
        token, value = self._peek()
        if token == 'keyword':
            if value == 'IF':
                return self.parse_if()

            if value == 'FOR':
                return self.parse_for()

            self.fail(expected=['if', 'for'])

        if token == 'string':
            return self.parse_string()

        if token == 'code':
            return self.parse_expr()

        self.fail(expected=['if', 'for', 'string', 'code'])

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

                self.fail(expected=['ELIF', 'ELSE', 'END'])

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
