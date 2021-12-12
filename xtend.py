from typing import Generator, Tuple, Union, List
import re

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


def scan(input: str) -> Generator[Tuple[str, str], None, None]:
    state = 'string'
    current_string = []

    for match in token_pattern.finditer(input):
        token, value = match.lastgroup, match.group()
        if state == 'string':
            if token in ['other', 'keyword']:
                current_string.append(value)
                continue

            if len(current_string) > 0:
                yield ('string', ''.join(current_string))
                current_string = []

            if token in ['nl', 'indent']:
                yield (token, value)
            elif token == 'open':
                state = 'xtend'
            else:
                raise NotImplementedError()

        elif state == 'xtend':
            if token in ['other', 'nl', 'indent']:
                current_string.append(value)
                continue

            if len(current_string) > 0:
                yield 'code', ''.join(current_string)
                current_string = []

            if token == 'close':
                state = 'string'
            elif token == 'keyword':
                yield 'keyword', value
            else:
                raise NotImplementedError()

    if len(current_string) > 0:
        if state == 'string':
            yield ('string', ''.join(current_string))
        else:
            yield ('code', ''.join(current_string))


class Parser():
    def __init__(self, input):
        self.input = scan(input)
        self.lookahead = None

    def fail(self, expected=Union[str, List[str]]):
        raise Exception('cannot parse')

    def next(self) -> Tuple[str, str]:
        if self.lookahead:
            next_item = self.lookahead
            self.lookahead = None
            return next_item
        return next(self.input, (None, None))

    def peek(self) -> Tuple[str, str]:
        if not self.lookahead:
            self.lookahead = self.next()
        return self.lookahead

    def parse_keyword(self, keyword: str):
        token, value = self.next()
        if token != 'keyword' and value != keyword:
            self.fail(expected=keyword)

    def parse_code(self):
        token, value = self.next()
        if token == 'code':
            if value.strip() == '':
                self.fail(expected='code')
            return 'code', value
        self.fail(expected='code')

    def parse_string(self):
        string_value = []
        while True:
            token, value = self.peek()
            if token in ['string', 'indent', 'nl']:
                self.next()
                string_value.append(value)

            else:
                break

        if len(string_value) == 0:
            self.fail(expected='string')

        return 'string', ''.join(string_value)

    def parse_xtend(self):
        while self.peek()[0]:
            yield self.parse_stmt()

    def parse_stmt(self):
        # stmt -> string | if | for | expr
        token, value = self.peek()
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
            token, value = self.peek()
            if token == 'keyword':
                if value == 'ELIF':
                    self.next()
                    results.append((self.parse_code(), self.parse_stmt()))
                    continue
                elif value == 'ELSE':
                    self.next()
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
