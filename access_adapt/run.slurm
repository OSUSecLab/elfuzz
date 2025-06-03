#!/usr/bin/env bash

#SBATCH --job-name=elfuzz
#SBATCH --nodes=1
#SBATCH --cpus-per-task=20
#SBATCH --gpus-per-node=4
#SBATCH --partition=gpuA100x4
#SBATCH --account=bdil-delta-gpu
#SBATCH --mem=100G
#SBATCH --time=48:00:00
#SBATCH --output=tmp/elf-slurm-%j-out.log
#SBATCH --error=tmp/elf-slurm-%j-err.log
#SBATCH --mail-type=END,FAIL,BEGIN
#SBATCH --mail-user=chuyangchen2018@outlook.com

mkdir -p tmp/fuzzdata

if [ "$#" -eq 1 ]; then
    start_gen=-1
    rundir="$1"
    with_start_gen=0
elif [ "$#" -eq 2 ]; then
    rundir="$1"
    start_gen="$2"
    with_start_gen=1
else
    echo "Usage: $0 <num_gen> [start_gen] <rundir>"
    exit 1
fi

function unused_port() {
    N=${1:-1}
    comm -23 \
        <(seq "1025" "65535" | sort) \
        <(ss -Htan |
            awk '{print $4}' |
            cut -d':' -f2 |
            sort -u) |
        shuf |
        head -n "$N"
}
export PORT=$(unused_port)

echo "Running $rundir"
echo "Job started on $(hostname):$PORT"

timestamp=$(date +"%y%m%d_%H%M%S")
tgi_prefix="tmp/tgi-$timestamp"
tgi_out="${tgi_prefix}-out.log"
tgi_err="${tgi_prefix}-err.log"

echo "Starting TGI with outputs to ${tgi_prefix}"

bash access_adapt/start_tgi_servers.sh > $tgi_out 2> $tgi_err &

SLEEP_TIME=${TGI_DELAY:-180}
echo "Waiting $SLEEP_TIME seconds after $(date) for TGI to start"
sleep $SLEEP_TIME

echo "Starting ELF"
if [ $with_start_gen -eq 1 ]; then
    bash access_adapt/all_gen_access.sh $rundir $start_gen "http://localhost:$PORT"
else
    bash access_adapt/all_gen_access.sh $rundir "http://localhost:$PORT"
fi
