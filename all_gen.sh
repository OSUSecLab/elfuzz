#!/bin/bash

# Be strict about failures
set -euo pipefail

if [ "$#" -eq 1 ]; then
    start_gen=-1
elif [ "$#" -eq 2 ]; then
    start_gen=$2
else
    echo "Usage: $0 rundir [start_gen]"
    exit 1
fi

# This needs to be the first thing we do because elmconfig.py uses it
# to find the config file ($ELMFUZZ_RUNDIR/config.yaml)
export ELMFUZZ_RUNDIR="$1"
export ELMFUZZ_RUN_NAME=$(basename "$ELMFUZZ_RUNDIR")
seeds=$(./elmconfig.py get run.seeds)
if [ -n "${NUM_GENERATIONS:-}" ]; then
    num_gens=${NUM_GENERATIONS}
else
    num_gens=$(./elmconfig.py get run.num_generations)
fi
# Generations are zero-indexed
last_gen=$((num_gens - 1))
genout_dir=$(./elmconfig.py get run.genoutput_dir -s GEN=. -s MODEL=.)
export ENDPOINTS=$(./elmconfig.py get model.endpoints)
export TYPE=$(./elmconfig.py get type)
export PROJECT_NAME=$(./elmconfig.py get project_name)
# normalize the path
genout_dir=$(realpath -m "$genout_dir")
# Check if we should remove the output dirs if they exist
should_clean=$(./elmconfig.py get run.clean)
if [ -d "$genout_dir" ]; then
    if [ "$should_clean" == "True" ]; then
        echo "Removing generated outputs in $genout_dir"
        rm -rf "$genout_dir"
    else
        echo "Generated output directory $genout_dir already exists; exiting."
        echo "Set run.clean to True to remove existing rundirs."
        exit 1
    fi
fi
# See if we have any gen*, initial, or stamps directories
if [ $start_gen -eq -1 ]; then
    for pat in "gen*" "initial" "stamps"; do
            if compgen -G "$ELMFUZZ_RUNDIR"/$pat > /dev/null; then
                if [ "$should_clean" == "True" ]; then
                    echo "Removing existing rundir(s):" "$ELMFUZZ_RUNDIR"/$pat
                    rm -rf "$ELMFUZZ_RUNDIR"/$pat
                else
                    echo "Found existing rundir(s):" "$ELMFUZZ_RUNDIR"/$pat
                    echo "Set run.clean to True to remove existing rundirs."
                    exit 1
                fi
            fi
    done
else
    for g in $(seq $start_gen $((last_gen+1))); do
        if [ -d "$ELMFUZZ_RUNDIR/gen$g" ]; then
            if [ "$should_clean" == "True" ]; then
                echo "Removing existing rundir(s):" "$ELMFUZZ_RUNDIR/gen$g"
                rm -rf "$ELMFUZZ_RUNDIR/gen$g"
            else
                echo "Found existing rundir(s):" "$ELMFUZZ_RUNDIR/gen$g"
                echo "Set run.clean to True to remove existing rundirs."
                exit 1
            fi
        fi
        if [ -f "$ELMFUZZ_RUNDIR/stamps/gen$g.stamp" ]; then
            if [ "$should_clean" == "True" ]; then
                echo "Removing existing rundir(s):" "$ELMFUZZ_RUNDIR/stamps/gen$g.stamp"
                rm -rf "$ELMFUZZ_RUNDIR/stamps/gen$g.stamp"
            else
                echo "Found existing rundir(s):" "$ELMFUZZ_RUNDIR/stamps/gen$g.stamp"
                echo "Set run.clean to True to remove existing rundirs."
                exit 1
            fi
        fi
    done
fi

if [ "$TYPE" == "fuzzbench" ]; then
    python prepare_fuzzbench.py
elif [ "$TYPE" == "oss-fuzz" ]; then
    python prepare_fuzzbench.py -d /home/appuser/oss-fuzz -t oss-fuzz
elif [ "$TYPE" == "docker" ]; then
    python prepare_fuzzbench.py -t docker
fi

if [ $start_gen -eq -1 ]; then
    mkdir -p "$ELMFUZZ_RUNDIR"/initial/{variants,seeds,logs}
    # Stamp dir tells us when a generation is fully finished
    # In the future this will let us resume a run
    mkdir -p "$ELMFUZZ_RUNDIR"/stamps
    cp -v $seeds "$ELMFUZZ_RUNDIR"/initial/seeds/
    ./do_gen.sh initial gen0
    for i in $(seq 0 $last_gen); do
        ./do_gen.sh gen$i gen$((i+1))
    done
else
    if [ $start_gen -eq 0 ]; then
        real_start_gen=0
        ./do_gen.sh initial gen0
    else
        real_start_gen=$((start_gen-1))
    fi
    for i in $(seq $real_start_gen $last_gen); do
        ./do_gen.sh gen$i gen$((i+1))
    done
fi
