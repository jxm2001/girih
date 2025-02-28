#!/bin/bash
ROOT_DIR="$(dirname "$(dirname "$(realpath "$0")")")"

# Ensure result directory exists
mkdir -p "${ROOT_DIR}/result"

# Define nt values for each size
declare -A nt_values
nt_values[400]=1000
nt_values[600]=800
nt_values[800]=600
nt_values[1000]=500

for ((kernel=6; kernel<=10; kernel++)); do
    for ((mwd=0; mwd<=3; mwd++)); do
        for size in 400 600 800 1000; do
            done_file="${ROOT_DIR}/result/kernel_${kernel}-mwd_${mwd}-z${size}.done"
            log_file="${ROOT_DIR}/result/kernel_${kernel}-mwd_${mwd}-z${size}.log"

            if [ -f "$done_file" ]; then
                echo "Skipping test: kernel=$kernel, mwd=$mwd, size=$size (done file exists)"
                continue
            fi

            numactl --interleave=0-1 --physcpubind=0-35 \
                ${ROOT_DIR}/build_dp/mwd_kernel --nx $size --ny $size --nz $size \
                --nt ${nt_values[$size]} --target-kernel $kernel --mwd-type $mwd --target-ts 2 \
                &> "$log_file"

            # Mark the test as completed
            touch "$done_file"
        done
    done
done
