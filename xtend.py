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


def scan(input: str):
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
                yield ('code', current_string)
                current_string = []

            if token == 'close':
                state = 'string'
            elif token == 'keyword':
                yield ('keyword', value)
            else:
                raise NotImplementedError()

    if len(current_string) > 0:
        if state == 'string':
            yield ('string', ''.join(current_string))
        else:
            yield ('code', ''.join(current_string))
