from isla.solver import parse_bnf, delete_unreachable
from grammar_graph.gg import GrammarGraph
import click as clk
import networkx as nx
import logging
import random

logger = logging.getLogger(__file__)

def escape(text: str) -> str:
    return text.encode('ascii').decode('unicode_escape')

def unescape(text: str) -> str:
    result = text.encode('unicode_escape').decode('ascii')
    if result.startswith('"') and result.endswith('"'):
        result = result[1:-1]
        result = result.replace('"', '\\"')
        result = f'"{result}"'
    return result

@clk.command()
@clk.argument('grammar', type=clk.Path(exists=True, file_okay=True, dir_okay=False))
@clk.option('--output', '-o', type=clk.Path(exists=False, file_okay=True, dir_okay=False), required=False, default=None)
@clk.option('--persist', '-p', type=clk.Path(exists=False, file_okay=True, dir_okay=False), required=False, default='./removed_edges.txt')
@clk.option('--load', '-l', type=clk.Path(exists=True, file_okay=True, dir_okay=False), required=False, default=None)
def main(grammar, output, persist, load):
    MAX_CYCLE_LEN = 70
    with open(grammar, 'r') as f:
        grammar = f.read()
    grammar = parse_bnf(grammar)
    grammar = delete_unreachable(grammar)
    graph = GrammarGraph.from_grammar(grammar)
    edges = set()

    for s, v in graph.all_edges:
        edges.add((s, v))
    
    to_delete = {}
    if load is None:
        del graph
        removed_edges = set()
        broken_cycle_count = 0
        changed = True
        while changed:
            nx_graph = nx.DiGraph(edges)
            cycles = nx.simple_cycles(nx_graph)
            changed = False
            to_break = None
            # We cannot control the randomness in finding cycles.
            # Sorting them doesn't work, since it cost too much time.
            # Thus, we have to persist the deleted edges later to make the result reproducible.
            for cycle in cycles:
                logger.debug(f'Check one cycle')
                l = len(cycle)
                if l > MAX_CYCLE_LEN:
                    e1 = (cycle[0], cycle[1])
                    e2 = (cycle[-1], cycle[0])
                    v1: str = e1[1].quote_symbol()
                    v2: str = e2[1].quote_symbol()
                    if '>-choice-' in v1:
                        to_break = e1
                    else:
                        assert '>-choice-' in v2
                        to_break = e2
                    logger.info(f'One {l}-length cycle detected, to delete {to_break[0].quote_symbol()}, {to_break[1].quote_symbol()}')
                    changed = True
                    broken_cycle_count += 1
                    break
            if to_break is not None:
                assert changed
                removed_edges.add(to_break)
                edges.remove(to_break)
        logger.info(f'Delete {len(removed_edges)} edges to break {broken_cycle_count} cycles')

        max_cycle = 0
        nx_graph = nx.DiGraph(edges)
        cycles = nx.simple_cycles(nx_graph)
        for cycle in cycles:
            l = len(cycle)
            logger.debug(f'Find one {l}-length cycle')
            max_cycle = max(max_cycle, l)
        logger.info(f'Max cycle length: {max_cycle}')
        
        with clk.open_file(persist, 'w') as f:
            for rule_head_node, alt_arm_node in removed_edges:
                rule_head = rule_head_node.quote_symbol().removesuffix('"').removeprefix('"')
                alt_str = alt_arm_node.quote_symbol().removesuffix('"').removeprefix('"')
                print(f'{rule_head} -> {alt_str}', file=f)
                alt_idx = int(alt_str.split('-')[-1]) - 1
                if rule_head not in to_delete:
                    to_delete[rule_head] = set()
                to_delete[rule_head].add(alt_idx)
    else:
        with clk.open_file(load, 'r') as f:
            for line in f:
                rule_head, alt_idx = line.strip().split(' -> ')
                alt_idx = int(alt_idx.split('-')[-1]) - 1
                if rule_head not in to_delete:
                    to_delete[rule_head] = set()
                to_delete[rule_head].add(alt_idx)

    def split_tokens(alt: str) -> list[str]:
        if not alt:
            return ['""']
        non_terminal = False

        tokens = []
        token = ''
        for c in alt:
            if not non_terminal:
                if c == '<':
                    if token:
                        tokens.append(token)
                    token = '<'
                    non_terminal = True
                else:
                    token += c
            else:
                if c == '>':
                    token += '>'
                    if token:
                        tokens.append(token)
                    token = ''
                    non_terminal = False
                else:
                    token += c
            first = False
        if token != '':
            tokens.append(token)
        result = []
        
        for token in tokens:
            if token.startswith('<') and token.endswith('>'):
                result.append(token)
            else:
                result.append(f'"{token}"')
        return result
        
    simplified: dict[str, list[list[str]]] = {}
    for rule_head, alts in grammar.items():
        alt_list = []
        for alt in alts:
            alt_list.append(split_tokens(alt))
        if rule_head not in to_delete:
            simplified[rule_head] = alt_list
        else:
            new_alts = []
            for i, alt in enumerate(alt_list):
                if i not in to_delete[rule_head]:
                    new_alts.append(alt)
            if len(new_alts) > 0:
                simplified[rule_head] = new_alts
            else:
                simplified[rule_head] = [['""']]
    
    def dfs(current: str, sorted_nodes: list[str]):
        for alt in simplified[current]:
            for token in alt:
                if token.startswith('<') and token.endswith('>') and token not in sorted_nodes:
                    assert token in simplified
                    sorted_nodes.append(token)
                    dfs(token, sorted_nodes)
    sorted_nodes = ['<start>']
    dfs('<start>', sorted_nodes)
        
    with clk.open_file(output, 'w') as f:
        for rule_head in sorted_nodes:
            alts = simplified[rule_head]
            alt_list = []
            for alt in alts:
                alt_list.append(' '.join(map(lambda t: '\\\\' if t == '\\' else unescape(t), alt)))
            indent = ' ' * (len(rule_head) + 3)
            print(f'{rule_head} ::= {f"\n{indent}| ".join(alt_list)}', file=f)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
