from concurrent.futures import ProcessPoolExecutor, as_completed
from idontwannadoresearch import MailLogger, watch
import logging

logger = logging.getLogger(__file__)
mailogger = MailLogger.load_from_config(__file__, "/home/appuser/elmfuzz/cli/config.toml", chained_logger=logger)

def read_cov(file) -> frozenset[str]:
    result = set()
    with open(file) as f:
        for l in f:
            edge, _ = l.split(':')
            result.add(edge)
    r = frozenset(result)
    del result
    return r

def cluster_cov(cov_files: list[str]) -> list[tuple[frozenset[str], list[str]]]:
    clusters: list[tuple[frozenset[str], list[str]]] = []
    for f in cov_files:
        cov = read_cov(f)
        found = False
        for c_cov, c in clusters:
            if cov == c_cov:
                c.append(f)
                found = True
                del cov
                break
        if not found:
            clusters.append((cov, [f]))
    return clusters

class QuickSet:
    def __init__(self, data: list[str]):
        self.data = data
        self.data.sort()
    
    def __eq__(self, other):
        if len(self.data) != len(other.data):
            return False
        for a, b in zip(self.data, other.data):
            if a != b:
                return False
        return True


def combine_clusters(clusters_list: list[list[tuple[frozenset[str], list[str]]]]) -> list[tuple[frozenset[str], list[str]]]:
    result: list[tuple[frozenset[str], list[str]]] = []
    for clusters in clusters_list:
        total = len(clusters) * len(result)
        count = 0
        for cov, files in clusters:
            found = False
            for c_cov, c in result:
                count += 1
                print(f'{count/total:.2f}')
                if cov == c_cov:
                    c.extend(files)
                    found = True
                    del cov
                    break
            if not found:
                result.append((cov, files))
    return result

def recursive_del(to_del: list[tuple[frozenset[str], list[str]]]):
    for cov, files in to_del:
        del cov
        del files
    del to_del
    
def one_big_batch(big_batch: list[str], parallel: int, output_file: str, prefix: str):
    BATCH_SIZE = 20
    with tqdm(total=len(big_batch)) as pbar:
        result: list[tuple[frozenset[str], list[str]]] = (
            project(big_batch) >>
            segment(len(big_batch) // BATCH_SIZE) >>
            mapping(cluster_cov, para_num=parallel, callback=lambda input, _future: pbar.update(len(input))) >> # type: ignore
            accumulate(combine_clusters)
        )
    with open(output_file, 'w') as f:
        for cov, files in result:
            trimmed = []
            for ff in files:
                trimmed.append(ff.removeprefix(prefix))
            f.write(';'.join(cov) + '|' + ';'.join(trimmed) + '\n')

def read_and_combine(files: list[str], output_file: str) -> tuple[int, str]:
    cluster_list = []
    for file in files:
        with open(file, 'r') as f:
            tmp = []
            for l in f:
                cov, file_list = l.split('|')
                cov_s =frozenset(cov.split(';'))
                file_s = file_list.split(';')
                tmp.append((cov_s, file_s)) 
        cluster_list.append(tmp)
    combined = combine_clusters(cluster_list)
    with open(output_file, 'w') as f:
        for cov, files in combined:
            f.write(';'.join(cov) + '|' + ';'.join(files) + '\n')
    return len(combined), output_file


import click as clk
@clk.command()
@clk.option('--input', '-i', type=clk.Path(exists=True))
@clk.option('--output', '-o', type=clk.File('w'))
@clk.option('--cache', '-c', type=clk.Path(exists=True))
@clk.option('--parallel', '-j', type=int, default=1)
@watch(mailogger, report_ok=True)
def main(input, output, parallel, cache):
    files = [
        os.path.join(input, f) for f in os.listdir(input)
    ]
    BIGBATCH_SIZE = 50000
    big_batches = []
    for i in range(0, len(files), BIGBATCH_SIZE):
        big_batches.append(files[i:i + BIGBATCH_SIZE])
    residule = len(files) % BIGBATCH_SIZE
    big_batches[-1].extend(files[-residule:])
    
    time_records = []
    # with ProcessPoolExecutor(max_workers=1) as executor:
    for i, big_batch in enumerate(big_batches):
        tmp_out = os.path.join(cache, f'big_batch_{i}')
        if os.path.exists(tmp_out):
            print(f'Skipping big batch {i} / {len(big_batches)}')
            continue
        start_time = time.time()
        p = mp.Process(target=one_big_batch, args=(big_batch, parallel, tmp_out, input + '/'))
        p.start()
        p.join()
        p.close()
        end_time = time.time()
        elapsed = end_time - start_time
        time_records.append(elapsed)
        already_elapsed = sum(time_records)
        mean = already_elapsed / len(time_records)
        rest = mean * (len(big_batches) - i)
        print(f'Finished big batch {i} / {len(big_batches)} ({already_elapsed/3600:.2f}h / {rest/3600:.2f}h)')

    cluster_lists: list[str] = []
    for i in range(len(big_batches)):
        cluster_lists.append(os.path.join(cache, f'big_batch_{i}'))

    CLUSTER_BATCH_SIZE = 2
    epoch = 1
    def update(pbar, num):
        def __update(_f):
            pbar.update(num)
        return __update
    while len(cluster_lists) > 1:
        cluster_batches = []
        for i in range(0, len(cluster_lists), CLUSTER_BATCH_SIZE):
            cluster_batches.append(cluster_lists[i:i + CLUSTER_BATCH_SIZE])
        residule = len(cluster_lists) % CLUSTER_BATCH_SIZE
        cluster_batches[-1].extend(cluster_lists[-residule:])
        with ProcessPoolExecutor(max_workers=parallel) as executor, \
            tqdm(total=len(cluster_batches)) as pbar:
                futures = []
                merged = []
                for i, cluster_batch in enumerate(cluster_batches):
                    future = executor.submit(read_and_combine, cluster_batch, os.path.join(cache, f'cluster_batch_{epoch}_{i}'))
                    future.add_done_callback(update(pbar, len(cluster_batch)))
                    futures.append(future)
                for future in as_completed(futures):
                    r, m = future.result()
                    merged.append(m)
                    print(f'{m}: {r}')
                print(f'After epoch {epoch}, {len(merged)} clusters')
                cluster_lists = merged
                epoch += 1
                
    print(f'Final result: {cluster_lists[0]}')

if __name__ == '__main__':
    from tqdm import tqdm
    import os
    import os.path
    from idontwannadoresearch.mapreduce import project, segment, mapping, accumulate
    import tempfile
    import multiprocessing as mp
    import time

    main()
