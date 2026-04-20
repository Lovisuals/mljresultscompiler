# Test Results Collation Automation System
## Complete Automation Platform for Monthly Exam Result Processing

---

## 🚀 **NEW! Web Interface Available**

This system now includes a **beautiful terminal-style web interface**!

### Quick Start
```powershell
cd frontend
npm install
npm run dev
```
Then open: **http://localhost:3000**

**Features:**
- 🖥️ Terminal-style chat interface
- 📁 Drag & drop Excel file upload
- ⚡ Real-time processing status
- 🎨 Professional dark theme
- ✅ Automatic validation

---

## 🎯 What This System Does

This is a **production-ready automation platform** that eliminates manual errors in monthly exam result processing. Instead of hours of manual work and spreadsheet errors, you get:

✅ **Automatic** - Discovers and processes all 5 test files automatically  
✅ **Accurate** - Smart matching handles name variations and missing data  
✅ **Auditable** - Complete error logs and audit trails for compliance  
✅ **Fast** - Processes 100+ participants in minutes  
✅ **Reliable** - Built-in validation catches errors before they matter  

### The Problem It Solves
- ❌ Hours of manual copy-paste (error-prone)
- ❌ Participant name variations cause mismatch errors
- ❌ Missing results complaints from students
- ❌ No audit trail for "who made what change"
- ❌ Inconsistent formatting across result sheets

### The Solution
- ✅ Completely automated monthly processing
- ✅ Intelligent fuzzy matching of participants across tests
- ✅ Comprehensive error logs showing exactly what happened
- ✅ Consistent formatting and formulas every time
- ✅ Pre/post validation to catch errors early

---

## 📋 System Components

### 1. **test_collation_automation.py** - Core Engine
The main script that:
- Discovers test files (TEST_1 through TEST_5)
- Extracts participant names, emails, and scores
- Intelligently merges results across all tests
- Creates final result sheet with proper formatting
- Generates comprehensive error log

**Key Features:**
- Handles column name variations automatically
- Converts scores to consistent percentage format
- Calculates aggregate scores using Excel formulas (not hardcoded)
- Generates PASS/FAIL status based on configurable threshold
- Creates audit trail of all processing steps

### 2. **data_validator.py** - Quality Assurance
Runs before and after processing:
- **Pre-processing**: Validates all input files exist and have required structure
- **Post-processing**: Validates output file integrity and formula correctness
- Analyzes coverage (what % of participants have each test score)
- Generates validation report with issues/warnings

**Output:** JSON validation report with detailed findings

### 3. **master_automation.py** - Orchestration
Coordinates the entire process:
- Validates inputs
- Runs collation
- Validates outputs
- Archives results
- Generates execution summary

**Output:** Complete execution log showing what happened at each step

### 4. **Runner Scripts** - Easy Execution
- **Windows**: `run_automation_windows.bat` - Double-click to run
- **Linux/Mac**: `run_automation_linux.sh` - Run from terminal

---

## 🚀 Quick Start

### Step 1: Install Python & Dependencies (One-Time)

**Windows:**
1. Download Python from https://www.python.org/downloads/
2. Install (check "Add Python to PATH")
3. Open Command Prompt and run:
   ```
   pip install pandas openpyxl --break-system-packages
   ```

**Linux/Mac:**
```bash
# Ubuntu/Debian
sudo apt-get install python3 python3-pip
pip3 install pandas openpyxl --break-system-packages

# macOS
brew install python3
pip3 install pandas openpyxl --break-system-packages
```

### Step 2: Organize Your Files

```
your_project_folder/
├── input/                    # Create this folder
│   ├── TEST_1_Obstetrics_JANUARY_2026.xlsx
│   ├── TEST_2_Obstetrics_JANUARY_2026.xlsx
│   ├── TEST_3_Obstetrics_JANUARY_2026.xlsx
│   ├── TEST_4_Obstetrics_JANUARY_2026.xlsx
│   └── TEST_5_Ultrasonography_JANUARY_2026.xlsx
│
├── output/                   # Will be created automatically
│
├── (all Python scripts)      # Copy all .py files here
├── run_automation_windows.bat (Windows users)
└── run_automation_linux.sh   (Linux/Mac users)
```

### Step 3: Run the Automation

**Windows - Option A (Easiest):**
1. Double-click `run_automation_windows.bat`
2. Follow the prompts

**Windows - Option B (Command Line):**
```
python master_automation.py input output JAN_2026
```

**Linux/Mac:**
```bash
bash run_automation_linux.sh JAN_2026 ./input ./output
```

**All Platforms - Python Direct:**
```bash
python master_automation.py ./input ./output JAN_2026
```

### Step 4: Check Results

Output files created in `output/` folder:
- `OBS_JAN_2026_RESULT_SHEET.xlsx` - Main result file (open in Excel)
- `collation_log_JAN_2026_*.json` - Detailed error log
- `validation_report_*.json` - QA validation results
- `execution_log_*.json` - Complete process history

---

## 📊 Input File Requirements

Each test file must have:
- **Sheet name**: Must be "Responses"
- **Columns**: Must include Full Names, Email, Result (with % sign)
- **Format**: Standard .xlsx Excel format
- **Naming**: Must contain TEST_1, TEST_2, etc. in filename

### File Naming (Flexible)
Files are recognized by pattern:
- ✅ `TEST_1_anything.xlsx` - Recognized
- ✅ `test_1_anything.xlsx` - Recognized
- ✅ `TEST_1.xlsx` - Recognized
- ✅ `Obstetrics_and_Gynaecology_Ultrasonography_Test_5_JANUARY.xlsx` - Recognized as TEST_5
- ❌ `Exam1.xlsx` - NOT recognized (no TEST_1 pattern)

---

## 📈 Output File Structure

The generated result sheet has these columns:

| Column | Description | Format |
|--------|-------------|--------|
| S/N | Serial number | Number |
| NAMES | Participant name | Text |
| EMAIL | Participant email | Text |
| TEST 1-5 | Individual test scores | Percentage (0-100%) |
| GRP DISCUSSION | Group discussion points | Fixed at 0.8 |
| TOTAL MARK | Sum of all components | Formula: =SUM(D:I) |
| SCORE | Final calculated score | Formula: =TOTAL*weight |
| STATUS | Pass/Fail | Formula: IF(SCORE>=50,"PASS","FAIL") |

---

## 🔍 Error Handling & Logging

### Error Log (JSON Format)
Located at: `collation_log_JAN_2026_YYYYMMDD_HHMMSS.json`

Contains:
```json
{
  "errors": [
    {"file": "TEST_3.xlsx", "error": "Failed to load: Sheet not named 'Responses'"}
  ],
  "warnings": [
    {"test": "TEST_2", "warning": "2 rows with invalid data skipped"}
  ],
  "processed_files": [
    {"test": "TEST_1", "filename": "TEST_1.xlsx"},
    ...
  ],
  "output_file": "/path/to/OBS_JAN_2026_RESULT_SHEET.xlsx",
  "timestamp": "2026-01-31T12:30:45.123456"
}
```

### How to Read Errors

**Issue: "Required columns not found"**
- Check that column headers include: Full Names, Email, Result
- Spelling must match exactly (case-insensitive)

**Issue: "Empty or invalid data extracted"**
- Check that data starts in row 1 with headers
- Verify participant data is present in the sheet

**Issue: "No test data could be merged"**
- All test files failed - check error log for specific issues
- Verify all files have "Responses" worksheet

### Validation Report
Located at: `validation_report_YYYYMMDD_HHMMSS.json`

Shows:
- Pre-processing checks (input file validation)
- Post-processing checks (output file validation)
- Coverage analysis (% of participants in each test)
- Data quality metrics

---

## 🔧 Configuration & Customization

### Change Pass Mark Threshold
Edit `test_collation_automation.py`, find this line:
```python
self.pass_mark = 50  # Change this to 60, 70, etc.
```

### Change Output Filename
Modify the save call:
```python
collator.save_results(wb, filename="CUSTOM_NAME_JAN_2026.xlsx")
```

### Add Custom Columns
Edit `create_final_sheet()` method to add columns after STATUS (column L)

### Adjust Score Formula
Modify the SCORE formula:
```python
# Current: All tests weighted equally + 0.8 for group discussion
ws[f'K{row_num}'] = f'=J{row_num}*16.6666'

# To weight tests differently:
# 80% tests, 20% group discussion
ws[f'K{row_num}'] = f'=((D{row_num}+E{row_num}+F{row_num}+G{row_num}+H{row_num})/5*0.8) + (I{row_num}*0.2)'
```

---

## 🔄 Scheduling Monthly Automation

### Windows: Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. **Trigger tab**: Set to 1st of each month at 9:00 AM
4. **Action tab**: Start program
   - Program: `C:\Python\python.exe`
   - Arguments: `C:\path\to\master_automation.py C:\input C:\output`
5. **Conditions**: Check "Run whether user is logged in"
6. **Settings**: Check "If task fails, restart every 1 minute"

### Linux/Mac: Cron Job

```bash
# Edit crontab
crontab -e

# Add this line (runs 1st of month at 9 AM)
0 9 1 * * /path/to/run_automation_linux.sh JAN_2026 /path/to/input /path/to/output >> /var/log/test_collation.log 2>&1

# View logs
tail -f /var/log/test_collation.log
```

---

## ✅ Quality Assurance Checklist

After each automated run:

- [ ] Check error log - any errors listed?
- [ ] Verify participant count - matches enrollment?
- [ ] Spot check 3 random participants
  - [ ] Open result file
  - [ ] Find participant in TEST_1, TEST_2, TEST_3, etc.
  - [ ] Verify scores match source files
- [ ] Check formulas calculating correctly
- [ ] Verify PASS/FAIL status (should be PASS if score >= 50)
- [ ] Archive copy for records

---

## 📁 File Structure Reference

### All Files Included

```
test_results_collation_automation/
│
├── Core Scripts:
│   ├── test_collation_automation.py   - Main collation engine
│   ├── data_validator.py              - Pre/post validation
│   ├── master_automation.py           - Orchestration & coordination
│   │
│   ├── Runners:
│   ├── run_automation_windows.bat     - Windows execution (double-click)
│   └── run_automation_linux.sh        - Linux/Mac execution
│
├── Documentation:
│   └── README.md                      - This file
│
└── Work Directories (created at runtime):
    ├── input/                         - Place test Excel files here
    └── output/                        - Results generated here
```

---

## 🚨 Troubleshooting

### "No test files found"
- Check files are in the input folder
- Verify they end with `.xlsx`
- Filename must contain TEST_1, TEST_2, etc.

### "Module not found: pandas"
```bash
# Install missing package
pip install pandas --break-system-packages
pip install openpyxl --break-system-packages
```

### "Module 'openpyxl' has no attribute 'load_workbook'"
- Python installation issue
- Run: `pip install --upgrade openpyxl --break-system-packages`

### Script runs but produces no output
- Check error log: `collation_log_*.json`
- Verify input folder path is correct
- Ensure input Excel files have "Responses" worksheet

### Participant count doesn't match
- Check validation report for coverage
- Review error log for skipped rows
- Some participants may be missing from some tests (normal)

---

## 📞 Support

### Getting Help
1. **First**: Check error log (`collation_log_*.json`)
2. **Second**: Review validation report (`validation_report_*.json`)
3. **Third**: Check execution log (`execution_log_*.json`)
4. **Last**: Review this README for common issues

### Contacting Support
When reporting issues, include:
- Error log content
- Validation report
- Which step failed (see execution log)
- How many test files you have
- Any error messages from the script

---

## 💡 Tips for Best Results

1. **Consistency**: Use same filename pattern every month
2. **Backup**: Keep copies of input files before processing
3. **Review**: Always check error log after running
4. **Archive**: Save results and logs in monthly folders
5. **Test First**: Run with sample data to verify setup before production

### Example Directory Structure for Archives
```
results_archive/
├── 2026-01-january/
│   ├── OBS_JAN_2026_RESULT_SHEET.xlsx
│   ├── collation_log_JAN_2026_*.json
│   ├── validation_report_*.json
│   └── execution_log_*.json
│
├── 2026-02-february/
│   └── ...
│
└── 2026-03-march/
    └── ...
```

---

## 📝 Version Information

- **System Version**: 1.0
- **Last Updated**: January 31, 2026
- **Python Required**: 3.7+
- **Dependencies**: pandas 1.x, openpyxl 3.x
- **Operating Systems**: Windows, Linux, macOS

---

## 📜 License & Usage

This system is provided for educational and organizational use. Feel free to:
- Modify the scripts for your needs
- Customize formulas and calculations
- Integrate with other systems
- Schedule automated monthly runs

---

## Next Steps

1. ✅ Install Python and dependencies (see Quick Start)
2. ✅ Copy all scripts to a working folder
3. ✅ Place test Excel files in `input/` folder
4. ✅ Run the automation (Windows batch file or command line)
5. ✅ Check results in `output/` folder
6. ✅ Review error logs and validation reports
7. ✅ Archive results for your records
