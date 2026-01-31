#!/bin/bash
# Linux/Mac Bash Script for Test Results Collation Automation
# Run this script monthly to automate result processing

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Configuration
PYTHON_EXE=${PYTHON_EXE:-python3}
MONTH_YEAR=${1:-$(date +%b_%Y | tr '[a-z]' '[A-Z]')}
INPUT_DIR=${2:-./input}
OUTPUT_DIR=${3:-./output}

# Display header
echo ""
echo "===================================================================="
echo "Test Results Collation Automation - Linux/Mac Shell Runner"
echo "===================================================================="
echo ""
echo "Configuration:"
echo "  Script Directory: $SCRIPT_DIR"
echo "  Input Directory: $INPUT_DIR"
echo "  Output Directory: $OUTPUT_DIR"
echo "  Month/Year: $MONTH_YEAR"
echo ""

# Check if Python is installed
if ! command -v $PYTHON_EXE &> /dev/null; then
    echo -e "${RED}ERROR: Python 3 is not installed or not in PATH${NC}"
    echo "Please install Python 3.7+ using:"
    echo "  Ubuntu/Debian: sudo apt-get install python3 python3-pip"
    echo "  macOS: brew install python3"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_EXE --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
echo -e "${BLUE}Found Python ${PYTHON_VERSION}${NC}"

# Check if input directory exists
if [ ! -d "$INPUT_DIR" ]; then
    echo -e "${RED}ERROR: Input directory not found: $INPUT_DIR${NC}"
    echo "Please create the directory and add test Excel files."
    exit 1
fi

# Check for test files
TEST_COUNT=$(find "$INPUT_DIR" -name "TEST_*.xlsx" -o -name "*ultrasonography*.xlsx" | wc -l)
if [ "$TEST_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}WARNING: No test files found in $INPUT_DIR${NC}"
fi

echo -e "${GREEN}Found $TEST_COUNT test files${NC}"
echo ""

# Check and install required Python packages
echo "Checking required Python packages..."
$PYTHON_EXE -c "import pandas, openpyxl" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Installing required packages...${NC}"
    $PYTHON_EXE -m pip install --upgrade pandas openpyxl --break-system-packages
    if [ $? -ne 0 ]; then
        echo -e "${RED}ERROR: Failed to install packages${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}All required packages are available${NC}"
echo ""

# Create output directory if needed
if [ ! -d "$OUTPUT_DIR" ]; then
    echo "Creating output directory: $OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"
fi

# Run the master automation script
echo "Starting collation process..."
echo ""

$PYTHON_EXE "$SCRIPT_DIR/master_automation.py" "$INPUT_DIR" "$OUTPUT_DIR" "$MONTH_YEAR"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ SUCCESS: Collation process completed!${NC}"
    echo -e "${GREEN}Results saved to: $OUTPUT_DIR${NC}"
    echo ""
    
    # List output files
    echo "Generated files:"
    if [ -d "$OUTPUT_DIR" ]; then
        ls -lh "$OUTPUT_DIR"/*.xlsx "$OUTPUT_DIR"/*.json 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
    fi
else
    echo ""
    echo -e "${RED}❌ ERROR: Process failed. Check the log files in $OUTPUT_DIR${NC}"
    exit 1
fi
