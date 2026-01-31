# 🚀 Quick Start - Get Running in 2 Minutes!

## For Windows Users (Easiest Way)

### Step 1: Open PowerShell in the frontend folder
```powershell
cd frontend
```

### Step 2: Run the startup script
Double-click: `start_frontend.bat`

**OR** type in PowerShell:
```powershell
.\start_frontend.bat
```

### Step 3: Open your browser
Go to: **http://localhost:3000**

**That's it!** 🎉

---

## What Happens Next?

1. **You'll see**: A cool terminal interface (black background, colorful text)
2. **Drag files**: Drop your Excel files (TEST_1.xlsx through TEST_5.xlsx) onto the upload area
3. **Click Upload**: Watch the terminal process your files in real-time
4. **Get Results**: Files appear in the `output/` folder

---

## If You Want to Install Manually

```powershell
cd frontend
npm install
npm run dev
```

Then open: http://localhost:3000

---

## Expected File Names

Your Excel files should be named:
- TEST_1.xlsx
- TEST_2.xlsx
- TEST_3.xlsx
- TEST_4.xlsx
- TEST_5.xlsx

You can upload any or all of them!

---

## Where Are My Results?

After processing, check:
- `MLJResultsCompiler/output/Final_Results_[Month]_[Year].xlsx`
- `MLJResultsCompiler/output/Collation_Errors_[Month]_[Year].txt`

---

## Troubleshooting

**"Port already in use"?**
```powershell
npm run dev -- -p 3001
```
Then open: http://localhost:3001

**"npm not found"?**
- Install Node.js from: https://nodejs.org/

**Files not processing?**
- Make sure Python is installed
- Check that `master_automation.py` exists in parent folder

---

## Need Help?

Read the detailed guides:
- `FRONTEND_SETUP.md` - Complete setup instructions
- `INTERFACE_PREVIEW.md` - See what the interface looks like
- `README.md` - Technical documentation

---

**Enjoy your new terminal interface!** 🎯
