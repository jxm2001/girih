#!/bin/bash
ROOT_DIR="$(dirname "$(dirname "$(realpath "$0")")")"

# Ensure result directory exists
mkdir -p "${ROOT_DIR}/result"

for ((kernel=6; kernel<=9; kernel++)); do
    for ((mwd=0; mwd<=3; mwd++)); do
		n1=1800
		n2=1800
		n3=600
		nt=1000
		problem_size="${n1}x${n2}x${n3}x${nt}"
		done_file="${ROOT_DIR}/result/kernel_${kernel}-mwd_${mwd}-${problem_size}.done"
		log_file="${ROOT_DIR}/result/kernel_${kernel}-mwd_${mwd}-${problem_size}.log"

		if [ -f "$done_file" ]; then
			echo "Skipping test: kernel=$kernel, mwd=$mwd, problem_size=$problem_size (done file exists)"
			continue
		fi

		numactl --interleave=all --physcpubind=0-59 \
			${ROOT_DIR}/build_dp/mwd_kernel --nz $n1 --ny $n2 --nx $n3 \
			--nt $nt --target-kernel $kernel --mwd-type $mwd --target-ts 2 \
			&> "$log_file"

		# Mark the test as completed
		touch "$done_file"
    done
done
