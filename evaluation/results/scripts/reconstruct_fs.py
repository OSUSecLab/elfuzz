import networkx as nx
from typing import Collection, Sequence
import sys
import json
import os

class CovSet:
    def __init__(self, edges: Collection[str]) -> None:
        self.edges = frozenset(edges)
    def __gt__(self, other: 'CovSet') -> bool:
        return self.edges > other.edges
    def __lt__(self, other: 'CovSet') -> bool:
        return self.edges < other.edges
    def __eq__(self, other: 'CovSet') -> bool:
        return self.edges == other.edges
    def __hash__(self) -> int:
        return hash(self.edges)
    def __len__(self) -> int:
        return len(self.edges)
    def __add__(self, other: 'CovSet') -> 'CovSet':
        return CovSet(self.edges.union(other.edges))

class FuzzerSpace:
    def __init__(self, init_element: CovSet | None = None, condense=False) -> None:
        self.graph = nx.DiGraph()
        self.cov_sets = set()
        self.condense = condense
        self.init_element = init_element
        if init_element is not None:
            self.graph.add_node(init_element)
            self.cov_sets.add(init_element)
    
    def add_element(self, cov_set: CovSet):
        if self.init_element is None:
            self.init_element = cov_set
            self.graph.add_node(cov_set)
            self.cov_sets.add(cov_set)
            return
        if cov_set in self.cov_sets:
            return
        if not self.condense:
            for node in self.cov_sets:
                if cov_set < node:
                    self.graph.add_edge(cov_set, node)
                elif cov_set > node:
                    self.graph.add_edge(node, cov_set)
            self.cov_sets.add(cov_set)
        else:
            edges_to_add = set()
            for node in self.cov_sets:
                if cov_set < node:
                    return
                elif cov_set > node:
                    edges_to_add.add((node, cov_set))
            self.graph.add_edges_from(edges_to_add)
            self.cov_sets.add(cov_set)
    def __len__(self) -> int:
        return len(self.cov_sets)
    def maximum(self) -> CovSet:
        return max(self.cov_sets, key=lambda x: len(x))

START = 0
END = 50
# SEEDS = {
#     'jsoncpp': 'var_0158.infilled'
# }

def to_cov_set(cov_item: Sequence[str]) -> CovSet:
    s = set()
    for item in cov_item:
        edge, _ = item.split(':')
        s.add(edge.strip())
    return CovSet(s)

# TODO: Count this for ELFuzz-noFS
if __name__ == '__main__':
    target = sys.argv[1]
    dir = sys.argv[2]
    # seed = SEEDS[target]
    
    fs = FuzzerSpace()
    condensed_fs = FuzzerSpace(condense=True)
    
    cov_records = {}
    logtext = ''
    for i in range(START, END + 1):
        with open(f'{dir}/gen{i}/logs/coverage.json') as cov_f:
            json_cov = json.load(cov_f)['CodeLlama-13b-hf']
        
        max_cov = CovSet([])
        if len(cov_records) > 0:
            seeds = os.listdir(f'{dir}/gen{i}/seeds')
            reserve = set()
            for seed in seeds:
                gen, _, id_seg = seed.removesuffix('.py').split('-')
                gen_c = int(gen.removeprefix('gen').removesuffix('_CodeLlama'))
                id = id_seg.removeprefix('hf_')
                if gen_c == i - 1:
                    reserve.add(id)
                cov = to_cov_set(cov_records[gen_c][id])
                max_cov = max_cov + cov
        logtext += f'Max cov: {len(max_cov)}'
        cov_records[i] = json_cov
        if i != START:
            to_remove = cov_records[i - 1].keys() - reserve
            for id in to_remove:
                del cov_records[i - 1][id]
            
        for variant, cov_item in json_cov.items():
            cov_set = to_cov_set(cov_item)
            fs.add_element(cov_set)
            condensed_fs.add_element(cov_set)
        print(logtext, flush=True)
        
        logtext = f'Gen {i}: {len(fs)}, {len(condensed_fs)}, '
            
