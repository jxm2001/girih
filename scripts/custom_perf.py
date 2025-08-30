import os
import re
import subprocess
from pathlib import Path
import pandas as pd

kernel_id_mapping = {6:"j3d7pt",
                    7:"j3d13pt",
                    8:"j3d27pt",
                    9:"poisson"}

best_mwd = {}

def parse_log_file(file_path):
    perf = None
    params = {}
    patterns = {
        "t_dim": r"Time\s+unroll:\s*(\d+)",
        "num_wavefronts": r"Multi-wavefront\s+updates:\s*(\d+)",
        "thread_group_size": r"Thread\s+group\s+size:\s*(\d+)",
        "thz": r"Threads\s+along\s+z-axis:\s*(\d+)",
        "thy": r"Threads\s+along\s+y-axis:\s*(\d+)",
        "thx": r"Threads\s+along\s+x-axis:\s*(\d+)"
    }
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if "Total RANK0 MStencil/s MAX:" in line:
                perf = float(line.split(":")[-1].strip())
            for key, pattern in patterns.items():
                match = re.search(pattern, line)
                if match:
                    params[key] = int(match.group(1))
    
    return perf, params if len(params) == len(patterns) else None

def extract_data(gstencil_s, kernel, problem_size, ncores, numa):
    attributes = {"Kernel": kernel, "Method": "Girih", "Problem Size": problem_size, "GStencil/s": gstencil_s, "Ncores": ncores, "NUMA": numa}
    return attributes

def perfTest(kernel_id, problem_size, ncores, numa, ntests):
    data = best_mwd[(kernel_id, problem_size)]
    
    n1, n2, n3, nt = problem_size
    problem_size_str = f'{n1}x{n2}x{n3}x{nt}'
    mwd_id = data["mwd_id"]
    params = data["params"]
    
    output_file = result_dir / f"numactl_{kernel_id}_{problem_size_str}.out"
    error_file = result_dir / f"numactl_{kernel_id}_{problem_size_str}.err"

    if numa == 1:
        numa_param = "--localalloc"
        core_bind_param = f'0-{ncores-1}'
    else:
        numa_param = "--interleave=all"
        if ncores < 128:
            core_bind_param = f'0-{ncores//2-1},64-{64+ncores//2-1}'
        else:
            core_bind_param = f'0-{ncores-1}'
    
    command = [
        "numactl", numa_param, f"--physcpubind={core_bind_param}", f"{root_dir}/build_dp/mwd_kernel",
        "--nz", str(n1), "--ny", str(n2), "--nx", str(n3), "--nt", str(nt),
        "--target-kernel", str(kernel_id), "--mwd-type", str(mwd_id), "--target-ts", "2",
        "--t-dim", str(params["t_dim"]), "--thread-group-size", str(params["thread_group_size"]),
        "--thz", str(params["thz"]), "--thy", str(params["thy"]), "--thx", str(params["thx"]),
        "--num-wavefronts", str(params["num_wavefronts"]), "--n-tests", str(ntests)
    ]
    
    print("Executing:", " ".join(command))
    
    with open(output_file, "w") as out, open(error_file, "w") as err:
        process = subprocess.run(command, env=os.environ, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out.write(process.stdout)
        err.write(process.stderr)
        print("output:")
        print(process.stdout)
        if process.stderr:
            print("errors:")
            print(process.stderr)
    
    match = re.search(r"Total RANK0 MStencil/s MAX:\s*([\d\.]+)", process.stdout)
    if match:
        return extract_data(float(match.group(1)) / 1000, kernel_id_mapping[kernel_id], f"{n1} {n2} {n3} {nt}", ncores, numa)
    else:
        print("error!!!")
        return None

if __name__ == "__main__":
    overview_res = []
    scalability_res = []
    script_path = Path(__file__).resolve()
    root_dir = script_path.parent.parent
    result_dir = root_dir / "result"
    
    pattern = re.compile(r"kernel_(\d+)-mwd_(\d+)-(\d+)x(\d+)x(\d+)x(\d+)\.log")
    
    
    for file in result_dir.iterdir():
        match = pattern.match(file.name)
        if not match:
            continue
        
        kernel_id, mwd_id, n1, n2, n3, nt = map(int, match.groups())
        perf, params = parse_log_file(file)
        
        if perf is None or params is None:
            continue
        
        key = (kernel_id, (n1, n2, n3, nt))
        if key not in best_mwd or best_mwd[key]["perf"] < perf:
            best_mwd[key] = {"mwd_id": mwd_id, "perf": perf, "params": params}
    
    for kernel_id in kernel_id_mapping.keys():
        problem_size = (1800, 1800, 600, 1000)
        if (kernel_id, problem_size) not in best_mwd or kernel_id not in kernel_id_mapping:
            continue
        overview_res.append(perfTest(kernel_id, problem_size, 128, 2, 1))
    df = pd.DataFrame(overview_res)
    df.to_csv(result_dir / 'perf-overview-girih-amd.csv', index=False)
