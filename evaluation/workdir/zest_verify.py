import os
from typing import Collection
from functools import reduce
from copy import deepcopy

ZEST_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), 'cvc5_zest'))

def read_cov(i) -> set[str]:
    cov_file = os.path.join(ZEST_DIR, f'zest_cov_{i}')
    result = set()
    with open(cov_file, 'r') as f:
        for line in f:
            token = line.strip().split(':')[0].strip()
            result.add(token)
    return result

class Coverage:
    def __init__(self, edges: Collection[str]):
        self.edges = set(edges)
        
    def add(self, edge: str) -> None:
        self.edges.add(edge)
    
    def update(self, edges: Collection[str]) -> None:
        self.edges.update(edges)
    
    def contained_in(self, other: 'Coverage') -> bool:
        return self.edges.issubset(other.edges)
    
    def diff_count(self, other: 'Coverage') -> int:
        return len(self.edges - other.edges)
    
    def __or__(self, other: 'Coverage') -> 'Coverage':
        return Coverage(self.edges | other.edges)
    
    def __ror__(self, other: 'Coverage') -> 'Coverage':
        return other | self
    
    def __len__(self) -> int:
        return len(self.edges)

SELECTED_BATCH_SIZE = 3
def select_batch(i: int, cov: Coverage, selected_batches: dict[int, Coverage]) -> int:
    assert i not in selected_batches
    if len(selected_batches) < SELECTED_BATCH_SIZE:
        selected_batches[i] = cov
        return -2
    sum_cov = reduce(lambda x, y: x | y, selected_batches.values())
    original_num = len(sum_cov)
    if cov.contained_in(sum_cov):
        return -1

    max_index = -1
    max_num = original_num
    for j in selected_batches:
        try_replace = deepcopy(selected_batches)
        del try_replace[j]
        try_replace[i] = cov
        new_num = len(reduce(lambda x, y: x | y, try_replace.values()))
        if new_num > max_num:
            max_num = new_num
            max_index = j
    if max_index == -1:
        return -1
    del selected_batches[max_index]
    selected_batches[i] = cov
    return max_index

if __name__ == '__main__':
    selected_batches = {}
    zest_survivors = []
    for i in range(10):
        tmp = set()
        with open(os.path.join(ZEST_DIR, f'survivor_{i}'), 'r') as f:
            for line in f:
                tmp.add(int(line.strip()))
        zest_survivors.append(tmp)
    for i in range(10):
        assert set(selected_batches.keys()) == zest_survivors[i], f"{i}: {set(selected_batches.keys())} != {zest_survivors[i]}"
        cov = read_cov(i)
        select_batch(i, Coverage(cov), selected_batches)
    print('Verified!')
