#!/bin/bash
ROOT_DIR="$(dirname "$(dirname "$(realpath "$0")")")"
if [ ! -d "${ROOT_DIR}/result" ]; then
    mkdir -p "${ROOT_DIR}/result"
fi
for ((kernel=6;kernel<=10;kernel=kernel+1)); do
	for ((mwd=0;mwd<=3;mwd=mwd+1)); do
		numactl --interleave=0-1 --physcpubind=0-35 ${ROOT_DIR}/build_dp/mwd_kernel --nx 400 --ny 400 --nz 400 --nt 1000 --target-kernel $kernel --mwd-type $mwd --target-ts 2 &> ${ROOT_DIR}/result/kernel_$kernel-mwd_$mwd-z400.log
		numactl --interleave=0-1 --physcpubind=0-35 ${ROOT_DIR}/build_dp/mwd_kernel --nx 600 --ny 600 --nz 600 --nt 800 --target-kernel $kernel --mwd-type $mwd --target-ts 2 &> ${ROOT_DIR}/result/kernel_$kernel-mwd_$mwd-z600.log
		numactl --interleave=0-1 --physcpubind=0-35 ${ROOT_DIR}/build_dp/mwd_kernel --nx 800 --ny 800 --nz 800 --nt 600 --target-kernel $kernel --mwd-type $mwd --target-ts 2 &> ${ROOT_DIR}/result/kernel_$kernel-mwd_$mwd-z800.log
		numactl --interleave=0-1 --physcpubind=0-35 ${ROOT_DIR}/build_dp/mwd_kernel --nx 1000 --ny 1000 --nz 1000 --nt 500 --target-kernel $kernel --mwd-type $mwd --target-ts 2 &> ${ROOT_DIR}/result/kernel_$kernel-mwd_$mwd-z1000.log
	done
done
