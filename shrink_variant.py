"""
LLMs tend to insert lengthy functions unreachable from the entry point. This script shrinks the LLMs by removing the unreachable functions.
"""

import ast_comments
from typing import Set
import sys

import click

import util

def collect_reachable_single_func(func: ast_comments.FunctionDef) -> Set[str]:
    """
    Collects the names of the functions reachable from the given function.
    """
    reachable = set()
    for node in ast_comments.walk(func):
        if isinstance(node, ast_comments.Call):
            if isinstance(node.func, ast_comments.Name):
                reachable.add(node.func.id)
            elif isinstance(node.func, ast_comments.Attribute):
                reachable.add(node.func.attr)
    return reachable

def collect_reachable(program, entry_points: Set[ast_comments.FunctionDef]) -> Set[str]:
    ast_comments.dump(program)
    reachable = set(map(lambda x: x.name, entry_points))
    func_map = dict()

    for node in ast_comments.walk(program):
        if isinstance(node, ast_comments.FunctionDef):
            func_map[node.name] = node

    worklist = []
    worklist += list(entry_points)
    while worklist:
        current = worklist.pop(0)
        tmp = collect_reachable_single_func(current)
        reachable.update(tmp)
        worklist += list(map(lambda x: func_map[x], filter(lambda x: x in func_map, tmp)))
    
    return reachable

@click.command()
@click.argument('source', type=click.File('r+'))
def main(source: click.File):
    """
    Shrinks the given LLM by removing the unreachable functions.
    """
    # print(f'Shrink {source.name}', file=sys.stderr)
    
    try:
        tree = ast_comments.parse(source.read())
    except SyntaxError:
        return
    
    entry_point = util.get_config('cli.genoutputs.driver.function_name')
    
    funcs = filter(lambda f: entry_point == f.name , [node for node in ast_comments.walk(tree) if isinstance(node, ast_comments.FunctionDef)])

    reachable = collect_reachable(tree, funcs)


    class Transformer(ast_comments.NodeTransformer):
        def visit_FunctionDef(self, node):
            if node.name in reachable:
                return node
            else:
                return None
    
    tree = Transformer().visit(tree)

    lines = ast_comments.unparse(tree).splitlines()

    new_lines = []

    for i in range(0, len(lines)):
        l = lines[i]
        if l.strip().startswith('#') and i >= 1 and lines[i - 1].strip() and not lines[i - 1].strip().startswith('#'):
            new_lines.append('')
        if not l.strip() and i >= 1 and lines[i -1 ].strip().startswith('#'):
            continue
        new_lines.append(l)

    new_src = '\n'.join(new_lines)
                
    
    if source.name == '<stdin>':
        print(new_src)
    else:
        source.seek(0)
        source.truncate()
        source.write(new_src)

if __name__ == '__main__':
    main()
