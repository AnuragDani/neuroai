import subprocess
import sys

def main():
    print("Running comparison...")
    cmd1 = [
        "scripts/run_nn_v2_comparison.py",
        "--protocol", "configs/nn_protocol_v2_2026-09-23.json",
        "--out", "reports/generated/nn_20260923/ladder_v2",
        "--workers", "14"
    ]
    subprocess.run([sys.executable] + cmd1, check=True)
    
    print("Running summarizer...")
    cmd2 = [
        "scripts/summarize_nn_v2.py",
        "--run", "reports/generated/nn_20260923/ladder_v2",
        "--out", "docs/nn_v2"
    ]
    subprocess.run([sys.executable] + cmd2, check=True)

if __name__ == "__main__":
    main()
