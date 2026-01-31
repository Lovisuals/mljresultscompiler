# Quick Start - Frontend Setup

## Install and Run (Windows)

1. Open PowerShell in the `frontend` directory
2. Run:

```powershell
npm install
npm run dev
```

3. Open browser to: http://localhost:3000

## What You'll See

A terminal-style interface where you can:
- Drag and drop Excel files
- See real-time processing status
- View results and error logs

## Upload Files

The interface accepts Excel files named:
- TEST_1.xlsx
- TEST_2.xlsx
- TEST_3.xlsx
- TEST_4.xlsx
- TEST_5.xlsx

Simply drag them onto the upload area or click to browse.

## Output

Processed files are saved to `../output/` directory:
- `Final_Results_[Month]_[Year].xlsx`
- `Collation_Errors_[Month]_[Year].txt`

## Troubleshooting

**Port already in use?**
```powershell
# Use a different port
npm run dev -- -p 3001
```

**Python script not found?**
- Ensure `master_automation.py` is in the parent directory
- Check that Python is installed: `python --version`

**Build for production:**
```powershell
npm run build
npm start
```
