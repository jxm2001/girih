import os
import re
import subprocess
from pathlib import Path
import csv
import pandas as pd

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

def extract_data(csv_file, gstencil_s, kernel, problem_size):
    elements = []
    
    with open(csv_file, newline='', encoding='utf-8') as csvfile:
        reader = list(csv.reader(csvfile))  # Read the entire CSV file into a list
        
        num_rows = len(reader)
        
        attributes = {"Kernel": kernel, "Method": "Girih", "Problem Size": problem_size, "GStencil/s": gstencil_s}
        attributes[reader[86][0]] = reader[86][5]  # Row 87, Column 1 as key, Column 6 as value
        
        for j in range(193, 221):  # Rows 194 to 221 (0-based index)
            attr_name = reader[j][0]
            attr_value = reader[j][4]
            attributes[attr_name] = attr_value
            
        elements.append(attributes)
    
    return elements

def main():
    elements = []
    script_path = Path(__file__).resolve()
    root_dir = script_path.parent.parent
    result_dir = root_dir / "result"
    
    pattern = re.compile(r"kernel_(\d+)-mwd_(\d+)-z(\d+)\.log")
    
    best_mwd = {}
    
    for file in result_dir.iterdir():
        match = pattern.match(file.name)
        if not match:
            continue
        
        kernel_id, mwd_id, zlen = map(int, match.groups())
        perf, params = parse_log_file(file)
        
        if perf is None or params is None:
            continue
        
        key = (kernel_id, zlen)
        if key not in best_mwd or best_mwd[key]["perf"] < perf:
            best_mwd[key] = {"mwd_id": mwd_id, "perf": perf, "params": params}
    
    nt_mapping = {400: 1000, 600: 800, 800: 600, 1000: 500}
    kernel_id_mapping = {6:"Heat3D/const-coef",
                         7:"Heat3D/origin-symmetry-vari-coef",
                         8:"Wave3D/r1",
                         9:"Wave3D/r2",
                         10:"Wave3D/r3"}
    
    for (kernel_id, zlen), data in sorted(best_mwd.items(), key=lambda x: (x[0][0], x[0][1])):
        if zlen not in nt_mapping:
            continue
        
        nt = nt_mapping[zlen]
        mwd_id = data["mwd_id"]
        params = data["params"]
        
        output_file = result_dir / f"likwid_{kernel_id}_z{zlen}.out"
        error_file = result_dir / f"likwid_{kernel_id}_z{zlen}.err"
        likwid_csv = result_dir / f"likwid_{kernel_id}_z{zlen}.csv"
        
        command = [
            "likwid-perfctr", "-c", "0-35", "-g", "CACHES", "-m", "-O", "-o", str(likwid_csv),
            "numactl", "--interleave=0-1", "--physcpubind=0-35", f"{root_dir}/build_dp/mwd_kernel",
            "--nx", str(zlen), "--ny", str(zlen), "--nz", str(zlen), "--nt", str(nt),
            "--target-kernel", str(kernel_id), "--mwd-type", str(mwd_id), "--target-ts", "2",
            "--t-dim", str(params["t_dim"]), "--thread-group-size", str(params["thread_group_size"]),
            "--thz", str(params["thz"]), "--thy", str(params["thy"]), "--thx", str(params["thx"]),
            "--num-wavefronts", str(params["num_wavefronts"]), "--n-tests", "1"
        ]
        
        print("Executing:", " ".join(command))
        
        with open(output_file, "w") as out, open(error_file, "w") as err:
            process = subprocess.run(command, env=os.environ, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out.write(process.stdout)
            err.write(process.stderr)
            print("likwid-perfctr output:")
            print(process.stdout)
            if process.stderr:
                print("likwid-perfctr errors:")
                print(process.stderr)
        
        match = re.search(r"Total RANK0 MStencil/s MAX:\s*([\d\.]+)", process.stdout)
        if match:
            elements.extend(extract_data(likwid_csv, float(match.group(1)) / 1000, kernel_id_mapping[kernel_id], f"{zlen} {zlen} {zlen} {nt}"))
    df = pd.DataFrame(elements)
    df.to_csv(result_dir / 'perf-girih.csv', index=False)

if __name__ == "__main__":
    main()
