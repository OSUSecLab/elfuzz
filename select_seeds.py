import click
import json
import sys
import os
from typing import Union, Literal, Optional
import random
from tqdm import tqdm

MODEL = 'CodeLlama-13b-hf'

def superior_than(edge_coverage1: set[str], edge_coverage2: set[str]) -> bool:
    return len(edge_coverage1) > len(edge_coverage2) and ((not edge_coverage2) or edge_coverage2.issubset(edge_coverage1))

def inferior_than(edge_coverage1: set[str], edge_coverage2: set[str]) -> bool:
    return len(edge_coverage1) < len(edge_coverage2) and ((not edge_coverage1) or edge_coverage1.issubset(edge_coverage2))

def equal_to(edge_coverage1: set[str], edge_coverage2: set[str]) -> bool:
    return edge_coverage1 == edge_coverage2

@click.command()
@click.option('--generation', '-g', type=str)
@click.option('--current-covfile', '-c', 'current_covfile', type=click.Path(exists=False), help='Current coverage file')
@click.option('--max-elites', '-n', 'max_elites', type=int)
@click.option('--input-elite-file', '-i', 'input_elite_file', type=click.Path(exists=False), help='Elite seeds file')
@click.option('--output-elite-file', '-o', 'output_elite_file', type=click.File('w'), help='Elite seeds file')
@click.option('--baseline', '-b', type=click.Path(exists=False), default=None)
def main(generation: str, current_covfile, max_elites: int, input_elite_file, output_elite_file, baseline):
    if generation == 'initial':
        coverage_raw: dict[str, dict[str, list[str]]] = dict()
    else:
        with open(click.format_filename(current_covfile), 'r') as f:
            coverage_raw: dict[str, dict[str, list[str]]] = json.loads(f.read())
    ELMFUZZ_RUNDIR = os.environ.get('ELMFUZZ_RUNDIR')
    
    if baseline is not None:
        with open(click.format_filename(baseline)) as base_edges_f:
            base_edges: set[str] = set()
            for l in base_edges_f:
                if not l.strip():
                    continue
                base_edges.add(l.strip())
    
    coverage = {model: {key: set(map(lambda x: x.split(':')[0], val)) for key, val in coverage.items()} for model, coverage in coverage_raw.items()}
    
    if generation == 'initial' or generation == 'gen0':
        elites = dict()
    else:
        with open(click.format_filename(input_elite_file), 'r') as f:
            elites_raw: dict[str, tuple[list[str], int]] = json.loads(f.read())
            # The edge sets of the elites cannot be a subset of each other
            elites = {key: (set(edges), size) for key, (edges, size) in elites_raw.items()}
    coverage_modulo_model = coverage.get(MODEL, {})

    elite_filtering_record: dict[frozenset[str], tuple[str, int]] = dict()
    for descendant_key, descendant_edges_raw in coverage_modulo_model.items():
        descendant_edges = frozenset(descendant_edges_raw)
        with open(f'{ELMFUZZ_RUNDIR}/{generation}/variants/{MODEL}/{descendant_key}.py', 'r') as f:
            descendant_size = len(f.read())
        if descendant_edges in elite_filtering_record:
            record_key, record_size = elite_filtering_record[descendant_edges]
            if descendant_size < record_size:
                elite_filtering_record[descendant_edges] = (descendant_key, descendant_size)
        else:
            elite_filtering_record[descendant_edges] = (descendant_key, descendant_size)
    filtered_descendants0: dict[str, tuple[set[str], int]] = dict()
    for descendant_edges, (descendant_key, descendant_size) in elite_filtering_record.items():
        filtered_descendants0[descendant_key] = (set(descendant_edges), descendant_size)

    filtered_descendants: dict[str, tuple[set[str], int]] = dict()
    
    comparison_raw: dict[tuple[str, str], Union[Literal['l'], Literal['r'], Literal['b']]] = dict()
    for elite_key1, (elite_edges1, elite_size1) in filtered_descendants0.items():
        for elite_key2, (elite_edges2, elite_size2) in filtered_descendants0.items():
            if elite_key1 == elite_key2 or (elite_key2, elite_key1) in comparison_raw:
                continue
            else:
                if equal_to(elite_edges1, elite_edges2):
                    if elite_size2 < elite_size1:
                        comparison_raw[(elite_key1, elite_key2)] = 'l'
                    else:
                        comparison_raw[(elite_key1, elite_key2)] = 'r'
                elif superior_than(elite_edges1, elite_edges2):
                    comparison_raw[(elite_key1, elite_key2)] = 'l'
                elif inferior_than(elite_edges1, elite_edges2):
                    comparison_raw[(elite_key1, elite_key2)] = 'r'
                else:
                    comparison_raw[(elite_key1, elite_key2)] = 'b'
                    
    comparison: dict[str, dict[str, Union[Literal['l'], Literal['r'], Literal['b']]]] = dict()
    for (key1, key2), comp in comparison_raw.items():
        if key1 not in comparison:
            comparison[key1] = dict()
        comparison[key1][key2] = comp
    
    selected: set[str] = set()
    for key in filtered_descendants0.keys():
        comps = comparison.get(key, {})
        if not any(comp == 'r' for comp in comps.values()):
            selected.add(key)
    for key in selected:
        filtered_descendants[key] = filtered_descendants0[key]
    
    replace: dict[str, str] = dict()
    newly_added = set()
    failed_descendant = set()
    if not elites:
        newly_added.update(filtered_descendants.keys())
    else:
        for elite_key, (elite_edges, elite_size) in elites.items():
            for descendant_key, (descendant_edges, descendant_size) in filtered_descendants.items():
                if descendant_key in failed_descendant:
                    continue
                if equal_to(descendant_edges, elite_edges):
                    if descendant_size < elite_size:
                        replace[elite_key] = descendant_key
                    else:
                        failed_descendant.add(descendant_key)
                elif superior_than(descendant_edges, elite_edges):
                    replace[elite_key] = descendant_key
                elif inferior_than(descendant_edges, elite_edges):
                    failed_descendant.add(descendant_key)
                else:
                    newly_added.add(descendant_key)
    
    new_elites: dict[str, tuple[list[str], int]] = dict()
    
    for elite_key, (elite_edges, elite_size) in elites.items():
        if elite_key in replace:
            replaced_by = replace[elite_key]
            s, sz = filtered_descendants[replaced_by]
            new_elites[f'{generation}-{replaced_by}'] = (list(s), sz)
        else:
            new_elites[elite_key] = (list(elite_edges), elite_size)
    
    for n in newly_added:
        s, sz = filtered_descendants[n]
        new_elites[f'{generation}-{n}'] = (list(s), sz)

    if baseline is not None:
        max_interesting_edges = 0
        interesting = set()
        for elite_key, (elite_edges, _) in new_elites.items():
            edge_set = set(elite_edges)
            if not inferior_than(edge_set, base_edges):
                interesting.add(elite_key)
                interesting_edges = len(edge_set.difference(base_edges))
                max_interesting_edges = max(max_interesting_edges, interesting_edges)
        if interesting:
            print(f'Found {len(interesting)} interesting elites with max interesting edges {max_interesting_edges}', file=sys.stderr)
    
    THRESHOLD_FACTOR = 1
    if baseline is not None and len(interesting) > THRESHOLD_FACTOR * max_elites:
        print(f'WARNING: The number of interesting elites {len(interesting)} exceeds the limit {max_elites} x {THRESHOLD_FACTOR}', file=sys.stderr)
        
        new_elites_filtering: dict[frozenset[str], tuple[str, int]] = dict()

        for elite_key, (elite_edges_raw, elite_size) in new_elites.items():
            elite_edges = frozenset(set(elite_edges_raw).union(base_edges))
            if elite_edges in new_elites_filtering:
                record_key, record_size = new_elites_filtering[elite_edges]
                if elite_size < record_size:
                    new_elites_filtering[elite_edges] = (elite_key, elite_size)
            else:
                new_elites_filtering[elite_edges] = (elite_key, elite_size)
        
        filtered_new_elites0: dict[str, tuple[set[str], int]] = dict()
        for elite_edges, (elite_key, elite_size) in new_elites_filtering.items():
            filtered_new_elites0[elite_key] = (set(elite_edges), elite_size)
        
        
        comparison_raw: dict[tuple[str, str], Union[Literal['l'], Literal['r'], Literal['b']]] = dict()
        for elite_key1, (elite_edges1_raw, elite_size1) in filtered_new_elites0.items():
            elite_edges1 = elite_edges1_raw.union(base_edges)
            for elite_key2, (elite_edges2_raw, elite_size2) in filtered_new_elites0.items():
                elite_edges2 = elite_edges2_raw.union(base_edges)
                if elite_key1 == elite_key2 or (elite_key2, elite_key1) in comparison_raw:
                    continue
                else:
                    if equal_to(elite_edges1, elite_edges2):
                        if elite_size2 < elite_size1:
                            comparison_raw[(elite_key1, elite_key2)] = 'l'
                        else:
                            comparison_raw[(elite_key1, elite_key2)] = 'r'
                    elif superior_than(elite_edges1, elite_edges2):
                        comparison_raw[(elite_key1, elite_key2)] = 'l'
                    elif inferior_than(elite_edges1, elite_edges2):
                        comparison_raw[(elite_key1, elite_key2)] = 'r'
                    else:
                        comparison_raw[(elite_key1, elite_key2)] = 'b'
                        
        comparison: dict[str, dict[str, Union[Literal['l'], Literal['r'], Literal['b']]]] = dict()
        for (key1, key2), comp in comparison_raw.items():
            if key1 not in comparison:
                comparison[key1] = dict()
            comparison[key1][key2] = comp
        
        selected: set[str] = set()
        for key in filtered_new_elites0.keys():
            comps = comparison.get(key, {})
            if not any(comp == 'r' for comp in comps.values()):
                selected.add(key)
        tmp = dict()
        for s in selected:
            tmp[s] = new_elites[s]
        new_elites = tmp
    
    
    if len(new_elites.items()) > max_elites:
        if len(new_elites) > THRESHOLD_FACTOR * max_elites:
            print(f'WARNING: The number of elites {len(new_elites)} exceeds the limit {max_elites} x {THRESHOLD_FACTOR}', file=sys.stderr)
            def random_search(set_family: list[tuple[str, set[str], int]], num: int = max_elites, baseline: set[str] = set()) -> list[tuple[str, set[str], int]]:
                def union_all(set_family: list[tuple[str, set[str], int]], baseline: set[str] = set()) -> tuple[set[str], int, set[str]]:
                    edges = baseline.copy()
                    keys = set()
                    max_size = 0
                    for k, e, s in set_family:
                        edges.update(e)
                        keys.add(k)
                        max_size = max(max_size, s)
                    return edges, max_size, keys
                
                TRY_TIMES = 10
                
                candidates: list[list[tuple[str, set[str], int]]] = []
                
                for _ in tqdm(range(TRY_TIMES), desc='Selecting'):
                    candidate = random.sample(set_family, num)
                    
                    changed = True
                    while changed:
                        changed = False
                        indices = list(range(len(set_family)))
                        random.shuffle(indices)
                        for idx in indices:
                            key, edges, size = set_family[idx]
                            original_set, original_size, keys = union_all(candidate, baseline)
                            if key in keys:
                                continue
                            for i in range(num):
                                new_candidate = candidate.copy()
                                new_candidate[i] = (key, edges, size)
                                new_set, new_size, keys = union_all(new_candidate, baseline)
                                if len(new_set) > len(original_set):
                                    candidate = new_candidate
                                    original_set = new_set
                                    original_size = new_size
                                    changed = True
                                    break
                                elif len(new_set) == len(original_set) and new_size < original_size:
                                    candidate = new_candidate
                                    original_set = new_set
                                    original_size = new_size
                                    changed = True
                                    break
                    candidates.append(candidate)
                with_stat = list(map(lambda item: (item, union_all(item, baseline)), candidates))
                sorted_ = list(sorted(with_stat, key=lambda item: (-len(item[1][0]), item[1][1])))
                stat = list(map(lambda item: item[1], sorted_))
                print(f'Get almost bests: {" ".join(map(lambda item: f"({len(item[0])}, {item[1]})", stat))}', file=sys.stderr)
                return list(map(lambda item: item[0], sorted_))[0]
            if baseline is None:
                almost_best = random_search(
                    list(map(lambda item: (item[0], set(item[1][0]), item[1][1]), new_elites.items())),
                )
                tmp = dict()
                for key, edges, size in almost_best:
                    tmp[key] = (list(edges), size)
                new_elites = tmp
            else:
                if len(interesting) < max_elites:
                    interesting_items: list[tuple[str, tuple[list[str], int]]] = list()
                    trivial_items: list[tuple[str, tuple[list[str], int]]] = list()
                    for k, item in new_elites.items():
                        if k in interesting:
                            interesting_items.append((k, item))
                        elif len(interesting) < max_elites:
                            trivial_items.append((k, item))
                    almost_best = random_search(list(map(lambda item: (item[0], set(item[1][0]), item[1][1]), trivial_items)), max_elites - len(interesting))
                    tmp: dict[str, tuple[list[str], int]] = dict()
                    for key, edges, size in almost_best:
                        tmp[key] = (list(edges), size)
                    for item in interesting_items:
                        tmp[item[0]] = item[1]
                    new_elites = tmp
                else:
                    almost_best = random_search(list(map(lambda item: (item[0], set(item[1][0]), item[1][1]), new_elites.items())), max_elites, base_edges)
                    tmp = dict()
                    for key, edges, size in almost_best:
                        tmp[key] = (list(edges), size)
                    new_elites = tmp
        else:
            print(f'WARNING: The number of elites {len(new_elites)} exceeds the limit {max_elites}', file=sys.stderr)
            if baseline is not None:
                interesting_items: list[tuple[str, tuple[list[str], int]]] = list()
                trivial_items: list[tuple[str, tuple[list[str], int]]] = list()
                for k, item in new_elites.items():
                    if k in interesting:
                        interesting_items.append((k, item))
                    elif len(interesting) < max_elites:
                        trivial_items.append((k, item))
                sorted_intrested = sorted(interesting_items, key=lambda item: (-len(set(item[1][0]).union(base_edges)), item[1][1]))
                if len(interesting) >= max_elites:
                    new_elites = dict(sorted_intrested[:max_elites])
                else:
                    sorted_trivial = sorted(trivial_items, key=lambda item: (-len(item[1][0]), item[1][1]))
                    new_elites = dict(sorted_intrested + sorted_trivial[:max_elites - len(sorted_intrested)])
            else:
                new_elites = dict(sorted(new_elites.items(), key=lambda item: (-len(item[1][0]), item[1][1]))[:max_elites])
    if set(new_elites.keys()) != set(elites.keys()):
        print('Elites updated', file=sys.stderr)
    output_elite_file.write(json.dumps(new_elites))
    
    for elite_key, (elite_edges, _) in sorted(new_elites.items(), key=lambda item: (len(item[1][0]), -item[1][1])):
        try:
            gen, generator = elite_key.split('-')
        except:
            print(f'DEBUG: elite_key = {elite_key}', file=sys.stderr, flush=True)
            raise
        print(f'{len(elite_edges)} {gen} {MODEL} {generator}', flush=True)
    
if __name__ == '__main__':
    main()
