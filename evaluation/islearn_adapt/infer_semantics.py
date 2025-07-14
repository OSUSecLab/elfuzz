import click as clk
import importlib
import sys
import os
import logging
from typing import Any
import json

from islearn.learner import InvariantLearner
from isla.language import ISLaUnparser, Formula, DerivationTree
from isla.solver import parse_bnf
from isla.parser import EarleyParser, ParseTree

TARGET = os.environ['ISLA_TARGET']

logger = logging.getLogger(__name__)

FORBIDDEN = {
}

ENABLE = {
    're2': ['Existence Numeric String Smaller Than',
             'Existence Numeric String Larger Than',
             'Balance',
             'Equal Count'],
    'cvc5': ['Existence Numeric String Smaller Than',
             'Existence Numeric String Larger Than',
             'Balance',
             'Equal Count'],
    'libxml2': ['Def-Use (XML-Attr)',
                'Def-Use (XML-Attr Strict)',
                'Def-Use (XML-Attr Disjunctive)',
                'Def-Use (XML-Tag)',
                'Def-Use (XML-Tag Strict)',
                'String Existence',
                'Positioned String Existence (CSV)',
                'Existence String Fixed Length',
                'Existence String Max Length',
                'Existence Strings Relative Order',
                'Balance',
                'Equal Count'],

    # The SVG seeds are too complex. We must forbid patterns deeper than 3,
    #  or it will run out of memory.
    'librsvg': ['String Existence',
                'Positioned String Existence (CSV)',
                'Existence String Fixed Length',
                'Existence String Max Length',
                'Existence Numeric String Smaller Than',
                'Existence Numeric String Larger Than',
                'Balance',
                'Equal Count'],
    "sqlite3": ['String Existence',
                'Positioned String Existence (CSV)',
                'Balance',
                'Equal Count'],

    # No def-use since whether a variable is defined in python is dynamic.
    #  It can only be determined at runtime, and our fuzzing target is the compiler,
    #  which don't know that.
    "cpython3": ['String Existence',
                'Positioned String Existence (CSV)',
                'Balance',
                'Equal Count',
                'Existence String Fixed Length',
                'Existence String Max Length'],
}

@clk.command()
@clk.argument('grammar_file', type=clk.File('r'))
@clk.option('--output', '-o', type=clk.Path(dir_okay=False, file_okay=True), default='-')
@clk.option('--log-level', '-l', type=clk.Choice(['DEBUG', 'INFO']), default='INFO', required=False)
@clk.option('--gen-new-seeds/--no-gen-new-seeds', type=bool, default=True, required=False)
def main(grammar_file, output, log_level, gen_new_seeds):
    match log_level:
        case 'DEBUG':
            logging.basicConfig(level=logging.DEBUG)
        case 'INFO':
            logging.basicConfig(level=logging.INFO)
        case _:
            raise ValueError(f'Invalid log level: {log_level}')
    grammar = parse_bnf(grammar_file.read())


    p_seeds = None
    seed_dir = './positive_seeds'
    if os.path.exists(seed_dir):
        seed_files = os.listdir(seed_dir)
        p_seeds = []
        for seed_f in seed_files:
            parser = EarleyParser(grammar)
            with open(os.path.join(seed_dir, seed_f)) as f:
                tmp = list(parser.parse(f.read()))
                parse_tree: ParseTree = tmp[0]
                derive_tree = DerivationTree.from_parse_tree(parse_tree)
                p_seeds.append(derive_tree)

    n_seeds = None
    seed_dir = './negative_seeds'
    if os.path.exists(seed_dir):
        seed_files = os.listdir(seed_dir)
        n_seeds = []
        for seed_f in seed_files:
            parser = EarleyParser(grammar)
            with open(os.path.join(seed_dir, seed_f)) as f:
                tmp = list(parser.parse(f.read()))
                parse_tree: ParseTree = tmp[0]
                derive_tree = DerivationTree.from_parse_tree(parse_tree)
                n_seeds.append(derive_tree)

    match TARGET:
        case 'sqlite3':
            target_num_pos_samples = 3
        case _:
            target_num_pos_samples = 10

    oracle_module = importlib.import_module('oracle')
    validate = oracle_module.validate_lang
    learner = InvariantLearner(
        grammar,
        prop=validate,
        positive_examples=p_seeds,
        negative_examples=n_seeds,
        generate_new_learning_samples=gen_new_seeds,
        deactivated_patterns=FORBIDDEN[TARGET] if TARGET in FORBIDDEN else None,
        activated_patterns=ENABLE[TARGET] if TARGET in ENABLE else None,
        target_number_positive_samples=target_num_pos_samples,
        target_number_positive_samples_for_learning=min(10, target_num_pos_samples),
    )

    results: dict[Formula, tuple[float, float]] = learner.learn_invariants()

    json_dict: dict[str, dict[str, Any]] = {}
    for idx, (rule, p) in enumerate(results.items()):
        json_dict[str(idx)] = {
            'rule': ISLaUnparser(rule).unparse(),
            'precision': p[0],
            'recall': p[1],
        }
    with clk.open_file(output, 'w') as output:
        json.dump(json_dict, output, indent=2)
if __name__ == '__main__':
    sys.path.insert(0, '.')
    main()
