#!/usr/bin/env python3
"""
Obstetrics & Gynecology Test Results Collation Automation
Processes individual test result sheets and compiles into unified result sheet
Designed for monthly automated processing with error tracking
"""

import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import os
from pathlib import Path
from datetime import datetime
import json
import sys
from typing import Dict, Tuple

class TestResultsCollator:
    def __init__(self, input_dir: str, output_dir: str, month_year: str):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.month_year = month_year
        self.error_log = {
            'errors': [],
            'warnings': [],
            'processed_files': [],
            'timestamp': datetime.now().isoformat(),
            'skipped_test1_count': 0,
            'retakes_handled': 0
        }
        self.pass_mark = 50
        
    def discover_test_files(self) -> Dict[int, str]:
        """Discover test files in input directory"""
        test_mapping = {}
        patterns = {
            1: ['TEST_1', 'test_1'],
            2: ['TEST_2', 'test_2'],
            3: ['TEST_3', 'test_3'],
            4: ['TEST_4', 'test_4'],
            5: ['TEST_5', 'test_5', 'Ultrasonography_Test_5']
        }
        
        for file in os.listdir(self.input_dir):
            if not file.endswith('.xlsx'):
                continue
            for test_num, pats in patterns.items():
                if any(p in file for p in pats):
                    test_mapping[test_num] = os.path.join(self.input_dir, file)
                    self.error_log['processed_files'].append({'test': f'TEST_{test_num}', 'filename': file})
                    break
        if not test_mapping:
            raise FileNotFoundError(f"No test files found in {self.input_dir}")
        return test_mapping
    
    def load_test_sheet(self, filepath: str) -> pd.DataFrame:
        """Load Responses sheet with flexible column mapping"""
        try:
            df = pd.read_excel(filepath, sheet_name='Responses')
            
            # Robust column detection
            col_map = {}
            for col in df.columns:
                c = str(col).strip().upper()
                if any(k in c for k in ['FULL NAME', 'FULL NAMES', 'NAMES', 'NAME']):
                    col_map[col] = 'Full Names'
                elif 'EMAIL' in c:
                    col_map[col] = 'Email'
                elif any(k in c for k in ['RESULT', 'SCORE', 'MARK']):
                    col_map[col] = 'Result'
            
            df.rename(columns=col_map, inplace=True)
            
            if not all(c in df.columns for c in ['Full Names', 'Email', 'Result']):
                self.error_log['warnings'].append({
                    'file': os.path.basename(filepath),
                    'warning': f'Missing key columns. Found: {df.columns.tolist()}'
                })
                return pd.DataFrame()
            
            df_subset = df[['Full Names', 'Email', 'Result']].copy()
            
            df_subset['Full Names'] = df_subset['Full Names'].astype(str).str.strip()
            df_subset['Email'] = df_subset['Email'].astype(str).str.strip()
            df_subset['Result'] = pd.to_numeric(
                df_subset['Result'].astype(str).str.rstrip('%'), errors='coerce'
            )
            df_subset = df_subset.dropna(subset=['Result'])
            
            return df_subset
        except Exception as e:
            self.error_log['errors'].append({'file': os.path.basename(filepath), 'error': str(e)})
            return pd.DataFrame()
    
    def merge_test_results(self, test_mapping: Dict[int, str]) -> pd.DataFrame:
        """Core logic: First attempt only + support for missing Test 1"""
        all_rows = []
        
        for test_num in sorted(test_mapping.keys()):
            filepath = test_mapping[test_num]
            test_df = self.load_test_sheet(filepath)
            if test_df.empty:
                continue
                
            test_df = test_df.rename(columns={'Result': f'TEST_{test_num}'})
            test_df['TEST_NUMBER'] = test_num
            test_df['SOURCE_FILE'] = os.path.basename(filepath)
            all_rows.append(test_df)
        
        if not all_rows:
            raise ValueError("No valid test data found")
        
        combined = pd.concat(all_rows, ignore_index=True)
        
        # Normalization
        combined['EMAIL_NORM'] = combined['Email'].str.strip().str.lower()
        combined['NAME_NORM'] = combined['Full Names'].str.strip().str.upper()
        
        # Sort so first attempt appears first
        combined = combined.sort_values(by=['EMAIL_NORM', 'NAME_NORM', 'TEST_NUMBER', 'SOURCE_FILE'])
        
        # Keep only the FIRST attempt per test per participant
        deduped = combined.drop_duplicates(subset=['EMAIL_NORM', 'NAME_NORM', 'TEST_NUMBER'], keep='first')
        
        # Pivot: one row per participant, blanks where test is missing
        pivoted = deduped.pivot_table(
            index=['EMAIL_NORM', 'NAME_NORM', 'Full Names', 'Email'],
            columns='TEST_NUMBER',
            values=[f'TEST_{i}' for i in range(1, 6)],
            aggfunc='first'
        ).reset_index()
        
        # Ensure all TEST columns exist (missing = blank)
        pivoted.columns = [col[0] if isinstance(col, tuple) else col for col in pivoted.columns]
        test_cols = [f'TEST_{i}' for i in range(1, 6)]
        for tc in test_cols:
            if tc not in pivoted.columns:
                pivoted[tc] = pd.NA
        
        pivoted = pivoted.sort_values(by='Full Names').reset_index(drop=True)
        
        # Derived columns
        pivoted['GRP DISCUSSION'] = 0.8
        pivoted['TOTAL MARK'] = pivoted[test_cols].sum(axis=1, skipna=True)
        pivoted['SCORE'] = pivoted['TOTAL MARK'] * (100 / 6.0)
        pivoted['STATUS'] = pivoted['SCORE'].apply(lambda x: "PASS" if x >= self.pass_mark else "FAIL")
        pivoted['TESTS_COMPLETED'] = pivoted[test_cols].notna().sum(axis=1)
        
        # Flag participants who missed Test 1 but took others (your color code)
        mask_skipped_test1 = pivoted['TEST_1'].isna() & pivoted[['TEST_2','TEST_3','TEST_4','TEST_5']].notna().any(axis=1)
        pivoted['REVIEW_FLAG'] = ''
        pivoted.loc[mask_skipped_test1, 'REVIEW_FLAG'] = 'Skipped Test 1 - Verify manually'
        
        # Update log
        self.error_log['skipped_test1_count'] = int(mask_skipped_test1.sum())
        self.error_log['retakes_handled'] = int(combined.duplicated(subset=['EMAIL_NORM', 'NAME_NORM', 'TEST_NUMBER']).any())
        
        return pivoted
    
    def create_final_sheet(self, master_df: pd.DataFrame) -> openpyxl.Workbook:
        """Create formatted sheet with yellow highlight for skipped Test 1"""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Responses'
        
        headers = ['S/N', 'NAMES', 'EMAIL', 'TEST 1', 'TEST 2', 'TEST 3', 
                   'TEST 4', 'TEST 5', 'GRP DISCUSSION', 'TOTAL MARK', 'SCORE', 
                   'STATUS', 'TESTS_COMPLETED', 'REVIEW_FLAG']
        
        ws.append(headers)
        
        # Header styling
        header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
        header_font = Font(bold=True, color='FFFFFF')
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        
        thin_border = Border(left=Side(style='thin'), right=Side(style='thin'),
                             top=Side(style='thin'), bottom=Side(style='thin'))
        yellow_fill = PatternFill(start_color='FFFFE0', end_color='FFFFE0', fill_type='solid')
        
        test_cols = ['TEST_1', 'TEST_2', 'TEST_3', 'TEST_4', 'TEST_5']
        
        for idx, row in master_df.iterrows():
            row_num = idx + 2
            
            ws[f'A{row_num}'] = idx + 1
            ws[f'B{row_num}'] = row['Full Names']
            ws[f'C{row_num}'] = row['Email']
            
            # Test scores (leave blank if missing)
            for col_idx, test_col in enumerate(test_cols):
                col_letter = get_column_letter(4 + col_idx)
                val = row.get(test_col)
                if pd.notna(val):
                    v = float(val)
                    ws[f'{col_letter}{row_num}'] = v / 100 if v <= 100 else v
                    ws[f'{col_letter}{row_num}'].number_format = '0.0%'
                else:
                    ws[f'{col_letter}{row_num}'] = None   # Explicitly blank
            
            ws[f'I{row_num}'] = 0.8
            ws[f'J{row_num}'] = f'=SUM(D{row_num}:I{row_num})'
            ws[f'K{row_num}'] = f'=J{row_num}*16.6666'
            ws[f'L{row_num}'] = f'=IF(K{row_num}>={self.pass_mark},"PASS","FAIL")'
            ws[f'M{row_num}'] = row.get('TESTS_COMPLETED', 0)
            ws[f'N{row_num}'] = row.get('REVIEW_FLAG', '')
            
            # Apply borders and alignment
            for col in range(1, 15):
                cell = ws.cell(row=row_num, column=col)
                cell.border = thin_border
                cell.alignment = Alignment(horizontal='center', vertical='center')
                if 4 <= col <= 9 and cell.value is not None:
                    cell.number_format = '0.0%'
            
            # Yellow highlight for participants who missed Test 1
            if row.get('REVIEW_FLAG'):
                for col in range(1, 15):
                    ws.cell(row=row_num, column=col).fill = yellow_fill
        
        # Column widths
        ws.column_dimensions['A'].width = 5
        ws.column_dimensions['B'].width = 35
        ws.column_dimensions['C'].width = 30
        for col in list('DEFGHIJKLMN'):
            ws.column_dimensions[col].width = 12
        
        ws.freeze_panes = 'A2'
        return wb
    
    def save_results(self, wb: openpyxl.Workbook, filename: str = None):
        if filename is None:
            filename = f"OBS_{self.month_year}_RESULT_SHEET.xlsx"
        filepath = os.path.join(self.output_dir, filename)
        os.makedirs(self.output_dir, exist_ok=True)
        wb.save(filepath)
        self.error_log['output_file'] = filepath
        return filepath
    
    def save_error_log(self):
        log_filename = f"collation_log_{self.month_year}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        log_path = os.path.join(self.output_dir, log_filename)
        os.makedirs(self.output_dir, exist_ok=True)
        with open(log_path, 'w') as f:
            json.dump(self.error_log, f, indent=2)
        return log_path
    
    def run(self) -> Tuple[str, bool]:
        try:
            print(f"[INFO] Starting collation for {self.month_year}")
            test_mapping = self.discover_test_files()
            print(f"  Found tests: {sorted(test_mapping.keys())}")
            
            print("[STEP 2] Merging results (keeping first attempt, blanks for missed tests)...")
            master_df = self.merge_test_results(test_mapping)
            print(f"  Processed {len(master_df)} unique participants")
            
            print("[STEP 3] Creating final formatted sheet...")
            wb = self.create_final_sheet(master_df)
            
            print("[STEP 4] Saving output...")
            output_path = self.save_results(wb)
            log_path = self.save_error_log()
            
            print(f"  Output Excel: {output_path}")
            print(f"  Log: {log_path}")
            print(f"  Skipped Test 1 cases: {self.error_log['skipped_test1_count']} (highlighted in yellow)")
            
            success = len(self.error_log['errors']) == 0
            return output_path, success
            
        except Exception as e:
            self.error_log['errors'].append({'error': str(e)})
            self.save_error_log()
            print(f"[ERROR] {str(e)}")
            return None, False


def main():
    if len(sys.argv) < 3:
        print("Usage: python test_collation_automation.py <input_dir> <output_dir> [month_year]")
        sys.exit(1)
    
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]
    month_year = sys.argv[3] if len(sys.argv) > 3 else datetime.now().strftime('%b_%Y').upper()
    
    collator = TestResultsCollator(input_dir, output_dir, month_year)
    output_path, success = collator.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()