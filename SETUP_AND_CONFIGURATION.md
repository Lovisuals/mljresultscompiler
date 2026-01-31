# Test Results Collation Automation System
## Comprehensive Setup & Implementation Guide

---

## 1. SYSTEM OVERVIEW

This automation system processes monthly test results (TEST 1-5) from multiple exam files and compiles them into a single unified result sheet with:
- Automatic participant matching across tests
- Missing data handling with warnings
- Consistent formatting and formulas
- Comprehensive error logging
- Quality assurance checks

### Problem It Solves
- ✅ Eliminates manual copy-paste errors
- ✅ Handles participant name variations automatically
- ✅ Maintains data consistency across all tests
- ✅ Creates audit trail of processing with error logs
- ✅ Reduces processing time from hours to minutes
- ✅ Prevents missing result complaints with detailed tracking

---

## 2. QUICK START

### Prerequisites
```bash
# Install required Python packages
pip install pandas openpyxl --break-system-packages
```

### Basic Usage
```bash
# Standard collation
python test_collation_automation.py ./input_folder ./output_folder JAN_2026

# Example with actual paths
python test_collation_automation.py /data/tests/january /data/results JAN_2026
```

### Input File Structure
```
input_folder/
├── TEST_1_Obstetrics___Gynecology_JANUARY_2026.xlsx
├── TEST_2_Obstetrics___Gynae_JANUARY_2026Total_Questions_25_.xlsx
├── TEST_3_Obstetrics___Gynaecology_JANUARY_15__2026_.xlsx
├── TEST_4_Obstetrics___GynecologyJANUARY_17th_2026.xlsx
└── Obstetrics_and_Gynaecology_Ultrasonography_Test_5_JANUARY_19__2026_.xlsx
```

### Output
```
output_folder/
├── OBS_JAN_2026_RESULT_SHEET.xlsx        # Main output
└── collation_log_JAN_2026_*.json         # Error log & audit trail
```

---

## 3. SYSTEM ARCHITECTURE

### Component 1: Test File Discovery
- Automatically locates test files (1-5) in input directory
- Matches files by pattern recognition (TEST_1, TEST_2, etc.)
- Validates file existence and format
- **Error tracking**: Logs missing or misnamed files

### Component 2: Data Extraction
- Reads each test sheet's "Responses" worksheet
- Standardizes column names (handles variations)
- Extracts: Full Names, Email, Result percentage
- **Error handling**: 
  - Missing required columns → Warning logged
  - Invalid data types → Skips row, continues
  - Empty sheets → Alert generated

### Component 3: Smart Matching
- Creates fuzzy match key from participant names
- Matches participants across all 5 tests
- Consolidates participant info when partial data exists
- **Handles**:
  - Name variations (DIKWAL vs Dikwal)
  - Whitespace inconsistencies
  - Missing email in some tests
  - Participants in only some tests

### Component 4: Result Compilation
- Merges all test scores into single record per participant
- Calculates aggregate scores using formulas (not hardcoded)
- Applies consistent formatting
- Generates PASS/FAIL status (threshold: 50%)
- **Quality checks**:
  - Validates score ranges (0-100%)
  - Detects missing values
  - Alerts on anomalies

### Component 5: Audit & Logging
- Comprehensive JSON error log
- Tracks:
  - All processed files
  - Data anomalies found
  - Merge conflicts resolved
  - Processing timestamp
  - Output file location
  - Error counts and types

---

## 4. CONFIGURATION

### Pass Mark Threshold
Default: 50%
To change, modify in the script:
```python
self.pass_mark = 50  # Change this value
```

### Input/Output Directories
Flexible - specify on command line:
```bash
python test_collation_automation.py /custom/input/path /custom/output/path MONTH_YEAR
```

### Test File Naming Patterns
Automatically recognized:
- TEST_1, test_1, Test_1
- TEST_2, test_2, Test_2
- TEST_3, test_3, Test_3
- TEST_4, test_4, Test_4
- TEST_5, test_5, Ultrasonography_Test_5

If your files use different naming, update `discover_test_files()` method.

---

## 5. AUTOMATION DEPLOYMENT OPTIONS

### Option A: Windows Task Scheduler (Recommended for Windows Users)

1. **Create batch script** (`run_collation.bat`):
```batch
@echo off
cd C:\path\to\scripts
python test_collation_automation.py C:\input_folder C:\output_folder JAN_2026
pause
```

2. **Schedule via Task Scheduler**:
   - Open Task Scheduler
   - Create Basic Task
   - Trigger: Monthly (1st of month at 9:00 AM)
   - Action: Start program → `run_collation.bat`
   - Configure to run whether user is logged in or not

3. **Monitor with email notification**:
   - Set task to send email on success/failure
   - Log outputs to dedicated folder

### Option B: Linux/Mac Cron Job (Recommended for Linux/Mac)

1. **Create shell script** (`run_collation.sh`):
```bash
#!/bin/bash
cd /path/to/scripts
python3 test_collation_automation.py /input_folder /output_folder JAN_2026
```

2. **Make executable**:
```bash
chmod +x run_collation.sh
```

3. **Add to crontab**:
```bash
# Run on 1st of each month at 9:00 AM
0 9 1 * * /path/to/run_collation.sh >> /var/log/test_collation.log 2>&1
```

4. **Check logs**:
```bash
tail -f /var/log/test_collation.log
```

### Option C: Python Web Dashboard (Advanced)

Create a simple web interface for manual/scheduled runs:
```python
# Using Flask (install: pip install flask --break-system-packages)
from flask import Flask, render_template, jsonify
from test_collation_automation import TestResultsCollator

app = Flask(__name__)

@app.route('/api/collate', methods=['POST'])
def run_collation():
    collator = TestResultsCollator('./input', './output', 'JAN_2026')
    result_path, success = collator.run()
    return jsonify({
        'success': success,
        'output_file': result_path,
        'errors': collator.error_log
    })

if __name__ == '__main__':
    app.run(debug=False, port=5000)
```

---

## 6. ERROR HANDLING & TROUBLESHOOTING

### Common Issues & Solutions

#### Issue: "No test files found"
**Cause**: File naming doesn't match patterns
**Solution**: 
- Check files in input directory exist
- Verify they end with `.xlsx`
- File must contain "TEST_1", "TEST_2", etc. in filename
- Or rename files to match pattern

#### Issue: "Required columns not found"
**Cause**: Sheet column names differ from expected
**Solution**:
- Check sheet is named "Responses"
- Verify columns exist: Full Names, Email, Result
- Update `col_mapping` in script if needed

#### Issue: "No test data could be merged"
**Cause**: All test sheets failed to load
**Solution**:
- Check error log JSON file for specific errors
- Verify all test sheets have "Responses" worksheet
- Ensure data starts from row 1 with headers

#### Issue: Participant count mismatch
**Cause**: Name variations preventing matches
**Solution**:
- Check error log for warnings
- Review "merge_key" matching in code
- May need manual name standardization

### Reading Error Logs

Error log location: `collation_log_JAN_2026_YYYYMMDD_HHMMSS.json`

Example structure:
```json
{
  "errors": [
    {
      "file": "/path/to/TEST_3.xlsx",
      "error": "Required columns not found"
    }
  ],
  "warnings": [
    {
      "test": "TEST_2",
      "warning": "2 rows with invalid data skipped"
    }
  ],
  "processed_files": [
    {"test": "TEST_1", "filename": "TEST_1.xlsx"},
    {"test": "TEST_2", "filename": "TEST_2.xlsx"}
  ],
  "output_file": "/output_folder/OBS_JAN_2026_RESULT_SHEET.xlsx",
  "timestamp": "2026-01-31T12:30:45.123456"
}
```

---

## 7. QUALITY ASSURANCE CHECKLIST

After running automation:

- [ ] **Check error log** - Review collation_log JSON for errors/warnings
- [ ] **Verify participant count** - Matches expected enrollment
- [ ] **Spot check scores** - Open output, verify 2-3 random participants match source
- [ ] **Check missing values** - Are blank cells expected or errors?
- [ ] **Validate formulas** - Excel formulas calculating correctly
- [ ] **Review PASS/FAIL** - Verify status matches score threshold
- [ ] **Compare with previous month** - Check for unusual changes

### Sample Manual Verification Steps:
```
1. Open OBS_JAN_2026_RESULT_SHEET.xlsx
2. Pick participant randomly (e.g., row 15)
3. Note their scores: TEST_1=85%, TEST_2=92%, etc.
4. Open corresponding source files (TEST_1.xlsx, TEST_2.xlsx, etc.)
5. Find same participant and verify scores match
6. Check TOTAL_MARK formula is calculating sum
7. Check SCORE formula is calculating percentage correctly
8. Check STATUS shows PASS if SCORE >= 50
```

---

## 8. INTEGRATION WITH EXISTING SYSTEMS

### Integration Point 1: Email Notification
```python
import smtplib
from email.mime.text import MIMEText

def send_completion_email(output_path, success, error_log):
    """Send completion notification"""
    msg = MIMEText(f"Collation {'succeeded' if success else 'failed'}\n\n"
                   f"Output: {output_path}\n\n"
                   f"Errors: {len(error_log['errors'])}")
    msg['Subject'] = f"Test Results Collation {datetime.now().strftime('%b %Y')}"
    msg['From'] = 'noreply@medicallocum.org'
    msg['To'] = 'admin@medicallocum.org'
    
    # Configure SMTP server and send...
```

### Integration Point 2: Database Upload
```python
def upload_to_database(df, month_year):
    """Upload results to central database"""
    # Pseudocode for database integration
    for idx, row in df.iterrows():
        db.insert('exam_results', {
            'participant_name': row['Full Names'],
            'email': row['Email'],
            'test_scores': {
                'test_1': row['TEST_1'],
                'test_2': row['TEST_2'],
                # ...
            },
            'final_score': row['SCORE'],
            'status': row['STATUS'],
            'month_year': month_year
        })
```

### Integration Point 3: Google Sheets/OneDrive Sync
```python
# Option: Auto-upload to Google Drive
from google.colab import drive  # If using Google Cloud
drive.mount('/content/drive')
# Copy output file to Drive for stakeholder access
```

---

## 9. MONTHLY WORKFLOW

### Before Running Script
1. Collect all test Excel files from course platform
2. Place in dedicated input folder
3. Ensure files follow naming convention
4. Verify "Responses" sheet exists in each file

### Running Script
1. Execute via Task Scheduler, Cron, or CLI
2. Note output file path
3. Check error log immediately for issues

### After Running Script
1. **QA Check** (using checklist from Section 7)
2. **Resolve Issues** - If errors found:
   - Review error log details
   - Manually fix problem files if needed
   - Re-run if necessary
3. **Distribute Results**:
   - Share output file with stakeholders
   - Archive copy for records
   - Update any dependent systems
4. **Document** - Note any manual corrections made

---

## 10. CUSTOMIZATION & ADVANCED USAGE

### Modify Pass Mark
```python
# In main() function, before creating collator:
collator = TestResultsCollator(input_dir, output_dir, month_year)
collator.pass_mark = 60  # Change from default 50%
```

### Custom Output Filename
```python
# In save_results() call:
output_path = collator.save_results(wb, filename="Custom_Results.xlsx")
```

### Add Additional Columns
Edit `create_final_sheet()` method:
```python
# Add new column after STATUS
headers = [..., 'FEEDBACK']

# In data loop:
ws[f'M{row_num}'] = "Feedback here"
ws.column_dimensions['M'].width = 20
```

### Change Score Calculation
Edit `create_final_sheet()` method:
```python
# Current: TOTAL MARK = SUM(all tests + group discussion)
# To weight differently:
ws[f'K{row_num}'] = f'=((D{row_num}+E{row_num}+F{row_num}+G{row_num}+H{row_num})/5)*0.8 + I{row_num}*0.2'
```

---

## 11. BACKUP & RECOVERY

### Recommended Backup Strategy
```
/backups/
├── 2026-01/
│   ├── OBS_JAN_2026_RESULT_SHEET.xlsx
│   ├── collation_log_JAN_2026_*.json
│   └── source_files_backup/
│       ├── TEST_1.xlsx
│       ├── TEST_2.xlsx
│       └── ... (all 5 tests)
├── 2026-02/
└── ...
```

### Automated Backup Script
```bash
#!/bin/bash
# run_collation_with_backup.sh
DATE=$(date +%Y-%m)
BACKUP_DIR="/backups/$DATE"

# Create backup
mkdir -p "$BACKUP_DIR/source"
cp /input_folder/*.xlsx "$BACKUP_DIR/source/"

# Run collation
python test_collation_automation.py /input_folder /output_folder "$DATE"

# Archive output
cp /output_folder/OBS_*.xlsx "$BACKUP_DIR/"
cp /output_folder/collation_log_*.json "$BACKUP_DIR/"
```

---

## 12. SUPPORT & MAINTENANCE

### Log File Location
- Windows: `C:\path\to\output\collation_log_*.json`
- Linux/Mac: `/path/to/output/collation_log_*.json`

### Updating the System
- Update Python packages: `pip install --upgrade pandas openpyxl`
- Backup before making code changes
- Test changes on sample data first
- Keep version history of script changes

### Getting Help
When troubleshooting:
1. Check error log JSON first
2. Review this guide for common issues
3. Verify input file formats
4. Test with smaller sample set
5. Check Python version (3.7+)

---

## 13. EXAMPLE: FULL MONTHLY WORKFLOW

**Scenario**: Running January 2026 processing on the 1st of February

```bash
# Step 1: Verify input files
ls -la /data/tests/january/TEST_*.xlsx
# Expected output:
# TEST_1_Obstetrics___Gynecology_JANUARY_2026.xlsx
# TEST_2_Obstetrics___Gynae_JANUARY_2026Total_Questions_25_.xlsx
# ... (all 5 tests)

# Step 2: Run automation
python test_collation_automation.py /data/tests/january /data/results JAN_2026

# Expected output:
# [INFO] Starting test results collation for JAN_2026
# [STEP 1] Discovering test files...
#   Found tests: [1, 2, 3, 4, 5]
# [STEP 2] Merging test results...
#   Merged 98 participants
# [STEP 3] Creating final result sheet...
# [STEP 4] Saving files...
#   Output: /data/results/OBS_JAN_2026_RESULT_SHEET.xlsx
#   Log: /data/results/collation_log_JAN_2026_20260201_143022.json
# [SUCCESS] Collation completed without errors

# Step 3: QA Check
# a) Review error log
cat /data/results/collation_log_JAN_2026_*.json | python -m json.tool

# b) Open result file in Excel
# c) Spot-check 3 random participants
# d) Verify PASS/FAIL status

# Step 4: Archive and distribute
mkdir -p /archive/JAN_2026
cp /data/results/OBS_JAN_2026_RESULT_SHEET.xlsx /archive/JAN_2026/
cp /data/results/collation_log_JAN_2026_*.json /archive/JAN_2026/

# Done!
```

---

## Document Version
- Version: 1.0
- Last Updated: January 31, 2026
- Compatible with: Python 3.7+, pandas 1.x, openpyxl 3.x
