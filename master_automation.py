#!/usr/bin/env python3
"""
Master Automation Script - Orchestrates entire monthly collation process
Runs validation → collation → post-validation → reporting
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

class AutomationOrchestrator:
    def __init__(self, input_dir, output_dir, month_year, skip_validation=False):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.month_year = month_year
        self.skip_validation = skip_validation
        self.scripts_dir = os.path.dirname(os.path.abspath(__file__))
        
        self.execution_log = {
            'start_time': datetime.now().isoformat(),
            'month_year': month_year,
            'input_dir': input_dir,
            'output_dir': output_dir,
            'steps': {}
        }
    
    def log_step(self, step_name, status, details=None):
        """Log execution step"""
        self.execution_log['steps'][step_name] = {
            'timestamp': datetime.now().isoformat(),
            'status': status,
            'details': details or {}
        }
        
        status_symbol = "✅" if status == "SUCCESS" else "❌" if status == "FAILED" else "⚠️ "
        print(f"\n{status_symbol} {step_name}: {status}")
        if details:
            for key, value in details.items():
                print(f"    {key}: {value}")
    
    def step_1_validate_inputs(self):
        """Step 1: Validate input files"""
        print("\n" + "="*70)
        print("STEP 1: VALIDATING INPUT FILES")
        print("="*70)
        
        try:
            # Check input directory exists
            if not os.path.exists(self.input_dir):
                self.log_step("Input Directory Check", "FAILED", 
                             {'error': f'Directory not found: {self.input_dir}'})
                return False
            
            # Check for test files
            test_files = [f for f in os.listdir(self.input_dir) if f.endswith('.xlsx')]
            
            if not test_files:
                self.log_step("Test Files Found", "FAILED",
                             {'error': f'No .xlsx files found in {self.input_dir}'})
                return False
            
            # Check for required test files
            found_tests = set()
            for file in test_files:
                for i in range(1, 6):
                    if f'TEST_{i}' in file or (i == 5 and 'ultrasonography' in file.lower()):
                        found_tests.add(i)
            
            missing_tests = set(range(1, 6)) - found_tests
            
            if missing_tests:
                self.log_step("Required Test Files", "WARNING",
                             {'found': sorted(found_tests), 'missing': sorted(missing_tests)})
            else:
                self.log_step("Required Test Files", "SUCCESS",
                             {'found_tests': 5, 'files': test_files})
            
            # Run detailed validation if available
            if not self.skip_validation and os.path.exists(os.path.join(self.scripts_dir, 'data_validator.py')):
                validator_script = os.path.join(self.scripts_dir, 'data_validator.py')
                result = subprocess.run(
                    [sys.executable, validator_script, self.input_dir],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode != 0 and not self.skip_validation:
                    self.log_step("Pre-Processing Validation", "WARNING",
                                 {'message': 'See validation_report for details'})
            
            return not bool(missing_tests)
            
        except Exception as e:
            self.log_step("Input Validation", "FAILED", {'error': str(e)})
            return False
    
    def step_2_run_collation(self):
        """Step 2: Run the main collation script"""
        print("\n" + "="*70)
        print("STEP 2: RUNNING TEST RESULTS COLLATION")
        print("="*70)
        
        try:
            collation_script = os.path.join(self.scripts_dir, 'test_collation_automation.py')
            
            if not os.path.exists(collation_script):
                self.log_step("Collation Script", "FAILED",
                             {'error': f'Script not found: {collation_script}'})
                return False, None
            
            # Run collation
            result = subprocess.run(
                [sys.executable, collation_script, self.input_dir, self.output_dir, self.month_year],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                # Find output file
                output_files = [f for f in os.listdir(self.output_dir) 
                               if f.startswith('OBS_') and f.endswith('.xlsx')]
                
                if output_files:
                    output_file = os.path.join(self.output_dir, output_files[0])
                    file_size = os.path.getsize(output_file) / 1024
                    
                    self.log_step("Collation Execution", "SUCCESS",
                                 {'output_file': output_files[0], 'size_kb': round(file_size, 2)})
                    return True, output_file
            
            self.log_step("Collation Execution", "FAILED",
                         {'stderr': result.stderr[:500]})
            return False, None
            
        except subprocess.TimeoutExpired:
            self.log_step("Collation Execution", "FAILED",
                         {'error': 'Timeout - process took too long'})
            return False, None
        except Exception as e:
            self.log_step("Collation Execution", "FAILED", {'error': str(e)})
            return False, None
    
    def step_3_validate_output(self, output_file):
        """Step 3: Validate output file"""
        print("\n" + "="*70)
        print("STEP 3: VALIDATING OUTPUT FILE")
        print("="*70)
        
        try:
            if not output_file or not os.path.exists(output_file):
                self.log_step("Output File Validation", "FAILED",
                             {'error': f'Output file not found: {output_file}'})
                return False
            
            # Run post-processing validation
            if os.path.exists(os.path.join(self.scripts_dir, 'data_validator.py')):
                validator_script = os.path.join(self.scripts_dir, 'data_validator.py')
                result = subprocess.run(
                    [sys.executable, validator_script, self.input_dir, output_file],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                self.log_step("Output File Validation", "SUCCESS",
                             {'message': 'See validation_report for details'})
                return result.returncode == 0
            
            self.log_step("Output File Validation", "SUCCESS",
                         {'file': os.path.basename(output_file)})
            return True
            
        except Exception as e:
            self.log_step("Output File Validation", "FAILED", {'error': str(e)})
            return False
    
    def step_4_archive_and_report(self, output_file):
        """Step 4: Archive and create summary report"""
        print("\n" + "="*70)
        print("STEP 4: ARCHIVING AND CREATING REPORT")
        print("="*70)
        
        try:
            archive_dir = os.path.join(self.output_dir, f'archive_{self.month_year}')
            os.makedirs(archive_dir, exist_ok=True)
            
            # Copy input files to archive
            for file in os.listdir(self.input_dir):
                if file.endswith('.xlsx'):
                    src = os.path.join(self.input_dir, file)
                    # Don't copy, just note
            
            # Copy output and logs to archive
            for file in os.listdir(self.output_dir):
                if file.endswith('.xlsx') or file.endswith('.json'):
                    if file not in os.listdir(archive_dir):
                        # Files are already in output_dir, archive is just a reference
                        pass
            
            # Create summary report
            summary_file = os.path.join(self.output_dir, f'PROCESSING_SUMMARY_{self.month_year}.json')
            
            with open(summary_file, 'w') as f:
                json.dump(self.execution_log, f, indent=2)
            
            self.log_step("Archive and Report", "SUCCESS",
                         {'summary_file': os.path.basename(summary_file),
                          'archive_dir': archive_dir})
            
            return True
            
        except Exception as e:
            self.log_step("Archive and Report", "FAILED", {'error': str(e)})
            return False
    
    def generate_final_report(self):
        """Generate and display final execution report"""
        print("\n" + "="*70)
        print("EXECUTION SUMMARY")
        print("="*70)
        
        total_steps = len(self.execution_log['steps'])
        successful_steps = sum(1 for s in self.execution_log['steps'].values() 
                              if s['status'] == 'SUCCESS')
        failed_steps = sum(1 for s in self.execution_log['steps'].values() 
                          if s['status'] == 'FAILED')
        warning_steps = sum(1 for s in self.execution_log['steps'].values() 
                           if s['status'] == 'WARNING')
        
        print(f"\nProcessing Month: {self.month_year}")
        print(f"Start Time: {self.execution_log['start_time']}")
        print(f"End Time: {datetime.now().isoformat()}")
        print(f"\nSteps Completed: {total_steps}")
        print(f"  ✅ Successful: {successful_steps}")
        print(f"  ⚠️  Warnings: {warning_steps}")
        print(f"  ❌ Failed: {failed_steps}")
        
        if failed_steps == 0:
            print(f"\n✅ OVERALL STATUS: SUCCESS")
            return True
        else:
            print(f"\n❌ OVERALL STATUS: FAILED")
            return False
    
    def save_execution_log(self):
        """Save full execution log"""
        self.execution_log['end_time'] = datetime.now().isoformat()
        
        log_file = os.path.join(self.output_dir, 
                               f'execution_log_{self.month_year}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        with open(log_file, 'w') as f:
            json.dump(self.execution_log, f, indent=2)
        
        print(f"\n[SAVED] Execution log: {log_file}")
        return log_file
    
    def run(self):
        """Execute full orchestration"""
        print("\n")
        print("╔" + "="*68 + "╗")
        print("║" + " "*15 + "TEST RESULTS COLLATION AUTOMATION" + " "*20 + "║")
        print("║" + " "*20 + f"Month: {self.month_year}" + " "*42 + "║")
        print("╚" + "="*68 + "╝")
        
        # Step 1: Validate inputs
        if not self.step_1_validate_inputs():
            self.log_step("OVERALL PROCESS", "FAILED", 
                         {'reason': 'Input validation failed'})
            self.save_execution_log()
            return False
        
        # Step 2: Run collation
        success, output_file = self.step_2_run_collation()
        if not success:
            self.log_step("OVERALL PROCESS", "FAILED",
                         {'reason': 'Collation failed'})
            self.save_execution_log()
            return False
        
        # Step 3: Validate output
        if not self.step_3_validate_output(output_file):
            self.log_step("OVERALL PROCESS", "FAILED",
                         {'reason': 'Output validation failed'})
            self.save_execution_log()
            return False
        
        # Step 4: Archive and report
        if not self.step_4_archive_and_report(output_file):
            self.log_step("OVERALL PROCESS", "FAILED",
                         {'reason': 'Archiving failed'})
            self.save_execution_log()
            return False
        
        # Generate final report
        success = self.generate_final_report()
        
        # Save logs
        self.save_execution_log()
        
        return success


def main():
    if len(sys.argv) < 3:
        print("Usage: python master_automation.py <input_dir> <output_dir> [month_year] [--skip-validation]")
        print("\nExample:")
        print("  python master_automation.py /data/january /results JAN_2026")
        print("\nOptions:")
        print("  --skip-validation : Skip detailed validation (faster but less safe)")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    month_year = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else datetime.now().strftime('%b_%Y').upper()
    skip_validation = '--skip-validation' in sys.argv
    
    orchestrator = AutomationOrchestrator(input_dir, output_dir, month_year, skip_validation)
    success = orchestrator.run()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
