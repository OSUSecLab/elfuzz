import os
import os.path
import itertools
import venn

RESULT_ROOT = os.path.join(os.path.dirname(__file__), '..')
ALL_ROOTS = ['rq1', 'rq3']

def sum_cov(cov_cases: set[tuple[str, str, str]]) -> dict[str, set[str]]:
    files = []
    for root in ALL_ROOTS:
        files.extend([(root, f) for f in os.listdir(os.path.join(RESULT_ROOT, root)) if f.endswith('.cov')])
    
    file_name_records: dict[tuple[str, str, str], str] = {}
    
    for root, f in files:
        benchmark, method, _ = f.removesuffix('.cov').split('_')
        file_name_records[(root, benchmark, method)] = os.path.join(RESULT_ROOT, root, f)
    coverage_records: dict[tuple[str, str, str], frozenset[str]] = {}
    for key in cov_cases:
        _, benchmark, _ = key
        cov_set = set()
        f = file_name_records[key]
        with open(f) as cov_file:
            for l in cov_file:
                edge, _ = l.split(':')
                cov_set.add(f'{benchmark}_{edge}')
        coverage_records[key] = frozenset(cov_set)
    
    results: dict[str, set] = {}
    for (_, _, method), cov_set in coverage_records.items():
        if method not in results:
            results[method] = set()
        results[method].update(cov_set)
    return results

METHOD_MAPPING = {
    'elm': 'ELMFuzz',
    'grmr': 'Grammarinator + ANTLR4',
    'isla': 'ISLa + ANTLR4',
    'islearn': 'ISLa + ANTLR4 + ISLearn',
    'alt': 'ELMFuzz-noFS'
}

METHODS = ['elm', 'grmr', 'isla', 'islearn']

# METHODS_ALT = ['elm', 'alt']

BENCHMARKS = [
    'jsoncpp', 'libxml2', 're2', 'sqlite3', 'cpython3', 'cvc5', 'librsvg'
]

if __name__ == '__main__':
    cov_cases = set([
        ('rq1', benchmark, 'elm') 
        for benchmark in BENCHMARKS
        # for method in METHODS
        ] + [
          ('rq3', benchmark, 'alt')
          for benchmark in BENCHMARKS
        ]) - set([('rq1', 'jsoncpp', 'islearn'), ('rq1', 're2', 'islearn')])

    
    cov_sets = sum_cov(cov_cases)

    subsets: set[frozenset[str]] = set()
    for m in range(1, len(cov_sets.keys())+1):
        for subset in itertools.combinations(cov_sets.keys(), m):
            subsets.add(frozenset(subset))
    
    lattice: set[tuple[frozenset[str], frozenset[str]]] = set()
    for s1 in subsets:
        for s2 in subsets:
            if s1 != s2 and s1.issubset(s2):
                lattice.add((s2, s1))
                
    venn_sets: dict[frozenset[str], frozenset[str]] = {}
    union_set = set()
    for s in cov_sets.values():
        union_set.update(s)
    
    for subset in subsets:
        intersection = set(union_set)
        for method in subset:
            s = cov_sets[method]
            intersection.intersection_update(s)
        venn_sets[subset] = frozenset(intersection)
    
    uniq_venn_sets: dict[frozenset[str], frozenset[str]] = {}
    for s, edges in venn_sets.items():
        ss = set(edges)
        for sub, super in lattice:
            if super == s:
                ss.difference_update(venn_sets[sub])
        uniq_venn_sets[s] = frozenset(ss)
    
    universe = set()
    for _, edges in uniq_venn_sets.items():
        universe.update(edges)
    total_num = len(universe)

    for s, edges in uniq_venn_sets.items():
        print(f'{":".join(s)} {len(edges)} {len(edges)/total_num}')
        
    # filtered = {k: v for k, v in uniq_venn_sets.items() if len(v) / total_num >= 0.01}
    
    # print('=====')
    
    # for s, edges in filtered.items():
    #     print(f'{":".join(s)} {len(edges)}')

    names = ['elm', 'alt']
    filtered_venn_sets = []
    for lb in names:
        cov = set()
        for key, edges in uniq_venn_sets.items():
            if lb in key:
                cov.update(edges)
        filtered_venn_sets.append(cov)
    labels = venn.get_labels(filtered_venn_sets)
    
    fig, ax = venn.venn2(
        labels,
        [METHOD_MAPPING[l] for l in names],
        figsize=(12, 8)
    )
    fig.savefig('rq3_venn.pdf')
