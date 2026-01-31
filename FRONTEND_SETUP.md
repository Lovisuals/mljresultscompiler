# MLJ Results Compiler - Complete Setup Guide

## System Overview

This system now includes:
1. **Backend**: Python automation scripts for processing Excel files
2. **Frontend**: Next.js web interface with terminal UI

## Directory Structure

```
MLJResultsCompiler/
├── frontend/                    # Next.js web interface
│   ├── src/
│   │   ├── app/
│   │   └── components/
│   ├── package.json
│   └── start_frontend.bat      # Quick start script
├── uploads/                     # Auto-created for incoming files
├── output/                      # Auto-created for processed results
├── master_automation.py         # Main Python processor
├── test_collation_automation.py # Core collation logic
├── data_validator.py            # Validation logic
└── [other Python scripts]
```

## Prerequisites

### Windows Setup

1. **Node.js 18+**
   - Download from: https://nodejs.org/
   - Verify: `node --version`

2. **Python 3.8+**
   - Already installed (based on your Python scripts)
   - Verify: `python --version`

3. **Python Dependencies**
   - openpyxl, pandas, fuzzywuzzy, etc.
   - Already configured in your project

## Installation

### Quick Start (Recommended)

1. Open the `frontend` folder
2. Double-click `start_frontend.bat`
3. Wait for installation and server start
4. Browser opens automatically to http://localhost:3000

### Manual Installation

```powershell
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Usage Flow

### 1. Start the Frontend
```powershell
cd frontend
npm run dev
```
- Opens on http://localhost:3000
- Terminal interface loads

### 2. Upload Files
- Drag & drop Excel files onto the upload area
- Or click to browse and select files
- Supported: TEST_1.xlsx through TEST_5.xlsx

### 3. Process Files
- Click "Upload" button
- Watch real-time progress in terminal
- Files are automatically:
  - Saved to `uploads/`
  - Processed by Python scripts
  - Results saved to `output/`

### 4. Review Results
- Terminal shows processing summary
- Output files:
  - `Final_Results_[Month]_[Year].xlsx`
  - `Collation_Errors_[Month]_[Year].txt`
- Files available in `output/` directory

## Features

### Terminal Interface
- ✅ Real-time status updates
- ✅ Color-coded messages (success/error/info)
- ✅ Timestamp for each operation
- ✅ Clean, professional dark theme

### File Handling
- ✅ Drag & drop support
- ✅ Multi-file selection
- ✅ File validation (Excel only)
- ✅ File size display
- ✅ Remove files before upload

### Backend Integration
- ✅ Automatic directory creation
- ✅ Python script execution
- ✅ Error handling and reporting
- ✅ Processing timeout protection

## Configuration

### Change Server Port

Edit `frontend/package.json`:
```json
"scripts": {
  "dev": "next dev -p 3001"
}
```

### Customize Upload Directory

Edit `frontend/src/app/api/process/route.ts`:
```typescript
const uploadDir = join(process.cwd(), '..', 'your-upload-folder')
```

### Adjust Processing Timeout

Edit `frontend/src/app/api/process/route.ts`:
```typescript
{ timeout: 120000 } // 120 seconds
```

## Production Deployment

### Build for Production

```powershell
cd frontend
npm run build
npm start
```

### Deploy to Server

1. Build the application
2. Copy entire `frontend/` folder to server
3. Install dependencies on server
4. Run with PM2 or similar:

```bash
pm2 start npm --name "mlj-compiler" -- start
```

## Troubleshooting

### "Port 3000 already in use"

```powershell
# Use different port
npm run dev -- -p 3001
```

### "Python script not found"

- Ensure `master_automation.py` is in parent directory
- Check file path in `route.ts`

### "Files not processing"

1. Check Python is installed: `python --version`
2. Verify Python script works independently
3. Check terminal output for errors
4. Review `uploads/` and `output/` directories exist

### "Cannot install dependencies"

```powershell
# Clear cache and reinstall
rd /s /q node_modules
del package-lock.json
npm install
```

### Browser Issues

- Clear browser cache
- Try incognito/private mode
- Check browser console (F12) for errors

## API Reference

### POST `/api/process`

Upload and process Excel files.

**Request:**
```
Content-Type: multipart/form-data
Body: files (array of File objects)
```

**Success Response (200):**
```json
{
  "message": "Files processed successfully",
  "filesReceived": 5,
  "files": ["TEST_1.xlsx", "TEST_2.xlsx", ...],
  "outputFile": "Final_Results_January_2026.xlsx",
  "errorLog": "Collation_Errors_January_2026.txt",
  "processingOutput": "... Python script output ..."
}
```

**Error Response (400/500):**
```json
{
  "error": "Error description",
  "details": "Detailed error message"
}
```

## Terminal Color Codes

- **Gray**: System messages and separators
- **Blue**: User actions
- **Green**: Success messages
- **Yellow**: Information messages
- **Red**: Error messages

## Development

### Project Structure

```
frontend/src/
├── app/
│   ├── api/process/route.ts    # API endpoint
│   ├── globals.css             # Styles
│   ├── layout.tsx              # Layout wrapper
│   └── page.tsx                # Home page
└── components/
    ├── Terminal.tsx            # Terminal UI
    └── FileUpload.tsx          # Upload component
```

### Add New Features

1. **Terminal Commands**: Edit `Terminal.tsx`
2. **Upload Validation**: Edit `FileUpload.tsx`
3. **Processing Logic**: Edit `api/process/route.ts`
4. **Styling**: Edit `globals.css` or Tailwind classes

### Hot Reload

Development server automatically reloads on file changes.

## Best Practices

1. **File Naming**: Use standard TEST_1.xlsx through TEST_5.xlsx
2. **File Size**: Keep files under 10MB for best performance
3. **Batch Processing**: Upload all files at once
4. **Error Review**: Always check error logs after processing
5. **Backup**: Keep original files as backup

## Support

For issues or questions:
1. Check this guide
2. Review terminal error messages
3. Check Python script documentation
4. Verify all dependencies installed

## Next Steps

1. ✅ Run `npm install` in frontend directory
2. ✅ Start server with `npm run dev`
3. ✅ Upload test files
4. ✅ Verify output files generated
5. ✅ Review processing logs

Enjoy your new terminal interface! 🚀
