# MLJ Results Compiler - Frontend

A Next.js terminal-style interface for uploading and processing Excel test result files.

## Features

- 🖥️ **Terminal UI** - Clean, retro terminal interface with color-coded output
- 📁 **Drag & Drop** - Simple file upload via drag-and-drop or file browser
- 📊 **Real-time Processing** - Live status updates as files are processed
- ✅ **Validation** - Automatic file type validation (Excel files only)
- 🎨 **Styled** - Dark theme with syntax highlighting and animations

## Getting Started

### Prerequisites

- Node.js 18+ installed
- Python 3.x with the automation scripts in parent directory

### Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

4. Open your browser to [http://localhost:3000](http://localhost:3000)

## Usage

1. **Upload Files**: Drag and drop your Excel files (TEST_1 through TEST_5) onto the upload area, or click to browse
2. **Review Selection**: Check the list of selected files
3. **Process**: Click the "Upload" button to send files for processing
4. **Monitor Progress**: Watch the terminal output for real-time status updates
5. **Results**: Processed files will be saved to the `output` directory

## File Structure

```
frontend/
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   └── process/
│   │   │       └── route.ts       # API endpoint for file processing
│   │   ├── globals.css            # Global styles and animations
│   │   ├── layout.tsx             # Root layout
│   │   └── page.tsx               # Home page
│   └── components/
│       ├── Terminal.tsx           # Main terminal interface
│       └── FileUpload.tsx         # File upload component
├── package.json
├── next.config.js
├── tailwind.config.js
└── tsconfig.json
```

## API Endpoint

### POST `/api/process`

Uploads Excel files and triggers Python processing script.

**Request**: `multipart/form-data` with files
**Response**:
```json
{
  "message": "Files processed successfully",
  "filesReceived": 5,
  "files": ["TEST_1.xlsx", "TEST_2.xlsx", ...],
  "outputFile": "Final_Results_January_2026.xlsx",
  "errorLog": "Collation_Errors_January_2026.txt"
}
```

## Build for Production

```bash
npm run build
npm start
```

## Technologies Used

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **react-dropzone** - File upload handling
- **Node.js** - Backend API

## Color Scheme

The terminal uses a professional dark theme:
- Background: `#0C0C0C`
- Text: `#CCCCCC`
- Success: `#0DBC79` (Green)
- Info: `#E5C07B` (Yellow)
- Error: `#E06C75` (Red)
- Links: `#3B78FF` (Blue)

## Troubleshooting

### Files not uploading
- Check that the Python scripts are in the parent directory
- Ensure Python is installed and accessible via command line
- Check browser console for error messages

### Processing fails
- Verify the Python automation scripts are working independently
- Check that all required Python packages are installed
- Review the terminal output for specific error messages

## License

Part of the MLJ Results Compiler automation system.
