import pandas as pd
import time
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from src.excel_processor import ExcelProcessor

def simulate():
    print("Starting Performance Simulation...")
    input_dir = Path(".")
    output_dir = Path("simulation_output")
    output_dir.mkdir(exist_ok=True)

    processor = ExcelProcessor(str(input_dir), str(output_dir))
    
    start_time = time.time()
    
    # 1. Load files
    print("\n[STEP 1] Loading test files...")
    loaded = processor.load_all_tests()
    load_time = time.time() - start_time
    print(f"Loaded {loaded} test files in {load_time:.2f}s")
    
    for test_num, data in processor.test_data.items():
        print(f"   - Test {test_num}: {len(data)} participants")

    # 2. Consolidate
    print("\n[STEP 2] Consolidating results...")
    cons_start = time.time()
    consolidated = processor.consolidate_results()
    cons_time = time.time() - cons_start
    print(f"Consolidated {len(consolidated)} unique participants in {cons_time:.4f}s")

    # 3. Accuracy Check
    print("\n[STEP 3] Accuracy Assessment...")
    total_raw_entries = sum(len(data) for data in processor.test_data.values())
    print(f"   - Total raw entries across all files: {total_raw_entries}")
    print(f"   - Total unique participants: {len(consolidated)}")
    
    # Check for data loss
    all_emails = set()
    for test_num, data in processor.test_data.items():
        all_emails.update(data.keys())
    
    missing_emails = all_emails - set(consolidated.keys())
    if not missing_emails:
        print("   - Data Integrity: 100% (No participants lost during merge)")
    else:
        print(f"   - Merged/Lost Participants: {len(missing_emails)}")
        for e in sorted(missing_emails):
            name_in_raw = "Unknown"
            for test_num, data in processor.test_data.items():
                if e in data:
                    name_in_raw = data[e]['name']
                    break
            
            found_as_mapped = False
            for cons_email, cons_data in consolidated.items():
                if cons_data['name'].lower() == name_in_raw.lower():
                    print(f"     * {e} ({name_in_raw}) -> merged into {cons_email}")
                    found_as_mapped = True
                    break
            
            if not found_as_mapped:
                print(f"     ! {e} ({name_in_raw}) -> TRULY LOST")

    # 4. Save
    print("\n[STEP 4] Saving output file...")
    save_start = time.time()
    success = processor.save_consolidated_file(consolidated, "Simulation_Report.xlsx")
    save_time = time.time() - save_start
    
    if success:
        print(f"Saved output in {save_time:.2f}s")
    else:
        print("Failed to save output!")

    total_time = time.time() - start_time
    print(f"\nTotal Processing Time: {total_time:.2f}s")
    print(f"Efficiency: {len(consolidated)/total_time:.2f} participants/sec")

if __name__ == "__main__":
    simulate()
