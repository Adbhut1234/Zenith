import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agent_tools.code_phasing import phase_scan_directory

def test():
    print("Testing Code Phasing Engine...")
    res = phase_scan_directory(PROJECT_ROOT)
    print(f"Root: {res['root']}")
    print(f"Scanned files count: {res['scanned_files_count']}")
    print("\nSample Extracted Symbols:")
    for f in res['files'][:6]:
        syms = [s['name'] for s in f['symbols'][:4]]
        if syms:
            print(f"  • {f['rel_path']}: {syms}")
            
    assert res['scanned_files_count'] > 0
    print("\nSUCCESS: Code Phasing Engine operational.")

if __name__ == "__main__":
    test()
