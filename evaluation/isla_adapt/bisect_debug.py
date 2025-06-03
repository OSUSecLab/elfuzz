import parsy as ps
from parsy import eof as EOF
from transpile_g4 import BNFTerminal, BNFNonTerminal, BNFRuleKind, BNFRule, BNFAlt, BNFGrammar, Transpiler
import click as clk
import os
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class TokenKind(Enum):
    TERMINAL = 1
    NON_TERMINAL = 2
    PIPE = 3
    DEF = 4
    WS = 5
    DEF_HEAD = 6

class Token:
    def __init__(self, kind: TokenKind, value: BNFNonTerminal | BNFTerminal | None):
        self.kind = kind
        self.value = value

NON_TERMINAL = ps.regex(r'<[_a-zA-Z][_a-zA-Z0-9]*+>').map(
    lambda text: 
        Token(TokenKind.NON_TERMINAL, BNFNonTerminal(text.removeprefix('<').removesuffix('>')))
)

TERMINAL = ps.regex(r'(?<!\\)"([^"\\]|\\(\\\\)*.)*"').map(
    lambda text: 
        Token(TokenKind.TERMINAL, BNFTerminal(text.removeprefix('"').removesuffix('"')))
)
PIPE = ps.string('|').map(lambda _: Token(TokenKind.PIPE, None))
DEF = ps.string('::=').map(lambda _: Token(TokenKind.DEF, None))
WS = ps.regex(r'[ \t\n\r]+').map(lambda _: Token(TokenKind.WS, None))

def __process_raw_tokens(raw_tokens: list[Token]) -> list[Token]:
    tmp = list(filter(lambda t: t.kind != TokenKind.WS, raw_tokens))
    result = []
    for i in range(len(tmp) - 1):
        if tmp[i + 1].kind == TokenKind.DEF:
            assert tmp[i].kind == TokenKind.NON_TERMINAL
            result.append(Token(TokenKind.DEF_HEAD, tmp[i].value))
        elif tmp[i].kind == TokenKind.DEF:
            continue
        else:
            result.append(tmp[i])
    result.append(tmp[-1])
    return result

tokenizer = (PIPE | DEF | TERMINAL | NON_TERMINAL | WS).many().map(
    lambda tokens: __process_raw_tokens(tokens)
)

terminal_token = ps.test_item(lambda t: t.kind == TokenKind.TERMINAL, 'terminal')
non_terminal_token = ps.test_item(lambda t: t.kind == TokenKind.NON_TERMINAL, 'non_terminal')
pipe_token = ps.test_item(lambda t: t.kind == TokenKind.PIPE, 'pipe')
def_head_token = ps.test_item(lambda t: t.kind == TokenKind.DEF_HEAD, 'def_head')

alt = (
    terminal_token.map(lambda t: t.value) | non_terminal_token.map(lambda t: t.value)
).at_least(1).map(
    lambda token_seq: 
        BNFAlt(token_seq)
)
alt_list = alt.sep_by(pipe_token)
rule = ps.seq(def_head_token.map(lambda t: t.value), alt_list).map(
    lambda head_and_alts: 
        BNFRule(head_and_alts[0], BNFRuleKind.PARSER, head_and_alts[1])
)

grammar = rule.many().map(
    lambda rules: 
        BNFGrammar('debug', rules)
)

def parse(text: str) -> BNFGrammar:
    tokens = tokenizer.parse(text)
    g = grammar.parse(tokens)
    return g

@clk.group(name='bisect_debug')
def main():
    pass


def cut(grammar: BNFGrammar, start: int, end: int) -> BNFGrammar:
    return remove(grammar, list(range(start, end + 1)))

def remove(grammar: BNFGrammar, to_remove: list[int]) -> BNFGrammar:
    assert all(r >= 0 and r < len(grammar.rules) for r in to_remove)
    to_remove_set = set(to_remove)
    new_rules = []
    for i, rule in enumerate(grammar.rules):
        if i not in to_remove_set:
            new_rules.append(rule)
    
    defined_non_terminals = set()
    all_non_terminals = set()
    
    for rule in new_rules:
        defined_non_terminals.add(rule.head)
        for alt in rule.alts:
            for token in alt.seq:
                if isinstance(token, BNFNonTerminal):
                    all_non_terminals.add(token)

    for nt in all_non_terminals - defined_non_terminals:
        new_rules.append(BNFRule(nt, BNFRuleKind.PARSER, [BNFAlt([])]))
    
    new_g = BNFGrammar('debug', new_rules)
    new_g = Transpiler.shrink(new_g)
    return new_g

@clk.command('cut')
@clk.argument('input_grammar', type=clk.Path(exists=True, dir_okay=False, file_okay=True), required=True)
@clk.argument('to_remove', type=str, required=True)
@clk.option('--output', '-o', type=clk.Path(exists=False, dir_okay=False, file_okay=True), default='-', required=False)
def cut_cmd(input_grammar, to_remove, output):
    with clk.open_file(input_grammar) as f:
        g: BNFGrammar = parse(f.read())
    if ',' in to_remove:
        start_s, end_s = to_remove.split(',')
        start = int(start_s)
        end = int(end_s)
        new_g = cut(g, start, end)
    else:
        to_remove = list(map(int, to_remove.split(';')))
        new_g = remove(g, to_remove)

    with clk.open_file(output, 'w') as f:
        f.write(new_g.to_str())

@clk.command('interpret')
@clk.argument('input_grammar', type=clk.Path(exists=True, dir_okay=False, file_okay=True), required=True)
@clk.option('--output', '-o', type=clk.Path(exists=False, dir_okay=False, file_okay=True), default='-', required=False)
@clk.option('--full', is_flag=True, default=False)
def interpret(input_grammar, output, full):
    with clk.open_file(input_grammar) as f:
        g: BNFGrammar = parse(f.read())
    if not os.path.exists('.bisect'):
        with clk.open_file('.bisect', 'w') as f:
            f.write(f'0,{len(g.rules)}')
    with clk.open_file('.bisect', 'r') as f:
        range_history = []
        for line in f:
            _range = line.split(',')
            _start = int(_range[0])
            _end = int(_range[1])
            range_history.append((_start, _end))
    start, end = range_history[-1]
    rules = g.rules[start:end + 1]
    count = start
    with clk.open_file(output, 'w') as f:
        for rule in rules:
            f.write(f'{count}: ')
            count += 1
            if full:
                f.write(rule.to_str())
            else:
                f.write(str(rule.head))
            f.write('\n')

@clk.command(name='pop')
@clk.argument('input_grammar', type=clk.Path(exists=True, dir_okay=False, file_okay=True), required=True)
@clk.option('--bisect-grammar', '-o', type=clk.Path(exists=False, dir_okay=False, file_okay=True), default='bisect.bnf', required=False)
def pop(input_grammar, bisect_grammar):
    with clk.open_file(input_grammar) as f:
        g: BNFGrammar = parse(f.read())

    with open('.bisect') as f:
        range_history = []
        for line in f:
            _range = line.split(',')
            _start = int(_range[0])
            _end = int(_range[1])
            range_history.append((_start, _end))
    range_history.pop()
    
    new_begin, new_end = range_history[-1]

    with open('.bisect', 'w') as f:
        for _start, _end in range_history:
            f.write(f'{_start},{_end}\n')
    
    new_g = cut(g, new_begin, new_end)
    
    with clk.open_file(bisect_grammar, 'w') as f:
        f.write(new_g.to_str())

@clk.command(name='push')
@clk.argument('range', type=str, required=True)
@clk.argument('input_grammar', type=clk.Path(exists=True, dir_okay=False, file_okay=True), required=True)
@clk.option('--bisect-grammar', '-o', type=clk.Path(exists=False, dir_okay=False, file_okay=True), default='bisect.bnf', required=False)
def push(range, input_grammar, bisect_grammar):
    with clk.open_file(input_grammar) as f:
        g: BNFGrammar = parse(f.read())
    
    if not os.path.exists('.bisect'):
        with open('.bisect', 'w') as f:
            f.write(f'0,{len(g.rules)}')
    
    with open('.bisect') as f:
        range_history = []
        for line in f:
            _range = line.split(',')
            _start = int(_range[0])
            _end = int(_range[1])
            range_history.append((_start, _end))
        prev_start, prev_end = range_history[-1]
    
    assert prev_end > prev_start + 1
    assert prev_start >= 0
    assert prev_end <= len(g.rules)
    
    mid = (prev_start + prev_end) // 2
    match range:
        case 'left':
            new_range = [prev_start, mid]
        case 'right':
            new_range = [mid, prev_end]
        case _:
            new_range = list(map(int, range.split(',')))
    new_start = new_range[0]
    new_end = new_range[1]

    assert new_start >= 0
    assert new_end <= len(g.rules)
    assert new_end > new_start
    assert new_start >= prev_start
    assert new_end <= prev_end
    assert new_start > prev_start or new_end < prev_end

    range_history.append(new_range)
    
    with open('.bisect', 'w') as f:
        for _start, _end in range_history:
            f.write(f'{_start},{_end}\n')
            
    new_g = cut(g, new_start, new_end)
    
    with clk.open_file(bisect_grammar, 'w') as f:
        f.write(new_g.to_str())
        
@clk.command(name='start')
@clk.option('--force', '-f', is_flag=True, default=False)
@clk.option('--range', '-r', type=str, default='0,-1', required=False)
@clk.option('--bisect-grammar', '-o', type=clk.Path(exists=False, dir_okay=False, file_okay=True), default='bisect.bnf', required=False)
@clk.argument('input_grammar', type=clk.Path(exists=True, dir_okay=False, file_okay=True), default=None, required=False)
def start(force, range, bisect_grammar, input_grammar):
    if os.path.exists('.bisect'):
        if force:
            logger.warning('Overwriting existing .bisect file')
            os.remove('.bisect')
        else:
            logger.error('Refusing to overwrite existing .bisect file. Use --force to override')
            return
    if range == '0,-1':
        return
    assert input_grammar is not None
    with clk.open_file(input_grammar) as f:
        g: BNFGrammar = parse(f.read())
    _start, _end = range.split(',')
    start = int(_start)
    end = int(_end)
    assert start >= 0
    assert end <= len(g.rules)
    assert end > start
    with open('.bisect', 'w') as f:
        f.write(f'{start},{end}\n')
        
main.add_command(pop)
main.add_command(push)
main.add_command(start)
main.add_command(interpret)
main.add_command(cut_cmd)

if __name__ == '__main__':
    main()
