"""
Excel Processing Module
Handles loading, processing, and merging Excel files from SurveyHeart
"""

from pathlib import Path
from typing import List, Dict, Tuple, Optional
import openpyxl
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter
import logging

from src.validators import clean_name, clean_email, parse_score, validate_row_data
from src.color_config import get_fill_for_test, TEST_COLORS
from src.participation_bonus import ParticipationBonusCalculator

logger = logging.getLogger(__name__)

class ExcelProcessor:
    """Process and consolidate test results from multiple Excel files"""
    
    REQUIRED_COLUMNS = ['Full Name', 'Email', 'Score', 'Result', '%']
    
    def __init__(self, input_dir: str, output_dir: str):
        """
        Initialize the Excel processor
        
        Args:
            input_dir (str): Directory containing input XLSX files
            output_dir (str): Directory for output files
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        # CRITICAL FIX: Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_data = {}  # {test_num: {email: {name, score}}}
        
    # Expanded header patterns — covers SurveyHeart, Google Forms, Microsoft Forms, etc.
    NAME_PATTERNS = [
        'full name', 'fullname', 'name', 'participant', 'student',
        'respondent', 'student name', 'candidate', 'your name',
        'first name', 'surname', 'learner',
    ]
    EMAIL_PATTERNS = [
        'email', 'e-mail', 'email address', 'mail', 'e mail',
        'your email', 'student email', 'respondent email',
        'email id', 'emailaddress',
    ]
    SCORE_PATTERNS = [
        'score', 'result', 'percentage', 'marks', 'total',
        'grade', 'point', 'total score', 'total marks',
        'mark', 'obtained', 'marks obtained',
    ]

    def find_column_index(self, sheet, column_names: List[str]) -> Optional[int]:
        """
        Find the index of a column by any of the possible names (substring match).
        
        Args:
            sheet: openpyxl worksheet
            column_names (List[str]): Possible column names to search for
            
        Returns:
            int: Column index (1-based) or None if not found
        """
        for row in sheet.iter_rows(min_row=1, max_row=1):
            for cell_idx, cell in enumerate(row, 1):
                if cell.value and any(name.lower() in str(cell.value).lower() for name in column_names):
                    return cell_idx
        return None
    
    def _get_all_headers(self, sheet) -> Dict[int, str]:
        """Read all header cells from row 1 and return {col_index: header_text}"""
        headers = {}
        for row in sheet.iter_rows(min_row=1, max_row=1):
            for cell_idx, cell in enumerate(row, 1):
                if cell.value:
                    headers[cell_idx] = str(cell.value).strip()
        return headers
    
    def _sniff_columns(self, sheet) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """
        Content-sniffing fallback: scan the first 10 data rows to auto-detect
        which column contains emails, names, and numeric scores.
        
        Returns:
            Tuple of (name_col, email_col, score_col) — 1-based indices, or None
        """
        import re
        email_regex = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        
        # Collect stats per column: how many look like emails, names, scores
        col_stats = {}   # {col_idx: {'email': count, 'text': count, 'number': count}}
        
        sample_rows = list(sheet.iter_rows(min_row=2, max_row=12, values_only=True))
        if not sample_rows:
            return None, None, None

        num_cols = max(len(r) for r in sample_rows)
        
        for col_idx in range(num_cols):
            stats = {'email': 0, 'text': 0, 'number': 0, 'total': 0}
            for row in sample_rows:
                if col_idx >= len(row) or row[col_idx] is None:
                    continue
                val = row[col_idx]
                stats['total'] += 1
                
                if isinstance(val, str):
                    val_stripped = val.strip()
                    if email_regex.match(val_stripped):
                        stats['email'] += 1
                    elif val_stripped.replace('%', '').strip().replace('.', '', 1).isdigit():
                        # Basic check to see if it's a number/percentage string
                        stats['number'] += 1
                    elif len(val_stripped) > 1:
                        stats['text'] += 1
                elif isinstance(val, (int, float)):
                    if 0 <= val <= 100:
                        stats['number'] += 1
                    else:
                        stats['number'] += 1  # still a number, even if out of range
            
            col_stats[col_idx + 1] = stats  # Store as 1-based
        
        # Identify columns
        email_col = None
        name_col = None
        score_col = None
        
        # Email: column with most email-like values
        email_candidates = [(idx, s['email']) for idx, s in col_stats.items() if s['email'] >= 2]
        if email_candidates:
            email_col = max(email_candidates, key=lambda x: x[1])[0]
        
        # Score: column with most numeric values (exclude email column)
        score_candidates = [(idx, s['number']) for idx, s in col_stats.items()
                           if s['number'] >= 2 and idx != email_col]
        if score_candidates:
            # Prefer the LAST numeric column (usually the score/result, not an ID/serial number)
            score_col = max(score_candidates, key=lambda x: (x[1], x[0]))[0]
        
        # Name: column with most text values (exclude email and score columns)
        name_candidates = [(idx, s['text']) for idx, s in col_stats.items()
                          if s['text'] >= 2 and idx != email_col and idx != score_col]
        if name_candidates:
            name_col = max(name_candidates, key=lambda x: x[1])[0]
        
        logger.info(f"  Content-sniff results: name_col={name_col}, email_col={email_col}, score_col={score_col}")
        return name_col, email_col, score_col
    
    def load_test_file(self, filepath: Path, test_number: int) -> bool:
        """
        Load a single test file and extract data.
        Uses header-matching first, falls back to content-sniffing if headers
        are not recognized.
        
        Args:
            filepath (Path): Path to the test XLSX file
            test_number (int): Test number
            
        Returns:
            bool: True if successful
        """
        try:
            logger.info(f"Loading test {test_number} from {filepath.name}")
            wb = openpyxl.load_workbook(filepath, data_only=True)
            ws = wb.active
            
            # === Step 1: Log every header in the file for debugging ===
            headers = self._get_all_headers(ws)
            logger.info(f"  Headers in {filepath.name}: {headers}")
            
            # === Step 2: Try header-based matching (expanded patterns) ===
            name_col = self.find_column_index(ws, self.NAME_PATTERNS)
            email_col = self.find_column_index(ws, self.EMAIL_PATTERNS)
            
            # For score, try test-specific column first, then generic
            score_col = self.find_column_index(ws, [
                f'Test {test_number} Score', f'Test {test_number} Result',
                f'Test {test_number}', f'test{test_number}',
            ])
            if not score_col:
                score_col = self.find_column_index(ws, self.SCORE_PATTERNS + ['%'])
            
            matched_via = "header-match"
            
            # === Step 3: Content-sniffing fallback ===
            if not all([name_col, score_col]) or not email_col:
                logger.warning(f"  Header match incomplete (name={name_col}, email={email_col}, score={score_col}). "
                              f"Falling back to content-sniffing...")
                
                sniffed_name, sniffed_email, sniffed_score = self._sniff_columns(ws)
                
                # Only fill in what header matching couldn't find
                if not name_col and sniffed_name:
                    name_col = sniffed_name
                if not email_col and sniffed_email:
                    email_col = sniffed_email
                if not score_col and sniffed_score:
                    score_col = sniffed_score
                
                matched_via = "content-sniff (fallback)"
            
            # === Step 4: Final check ===
            if not all([name_col, score_col]):
                logger.error(f"Could not find required columns (Name & Score) in {filepath.name}")
                logger.error(f"  Name col: {name_col}, Email col: {email_col}, Score col: {score_col}")
                logger.error(f"  Available headers: {headers}")
                return False
            
            logger.info(f"  Columns resolved via {matched_via} — Name: col {name_col} ('{headers.get(name_col, '?')}'), "
                        f"Email: col {email_col} ('{headers.get(email_col, 'MISSING')}'), "
                        f"Score: col {score_col} ('{headers.get(score_col, '?')}')")
            
            # === Step 5: Extract data ===
            import re
            
            # Detect if score needs scaling to percentage based on header like "Total Marks (17)"
            score_header = str(headers.get(score_col, ''))
            scale_max = None
            m = re.search(r'\((\d+)\)', score_header)
            if m:
                scale_max = float(m.group(1))
                logger.info(f"  Detected max score of {scale_max} from header '{score_header}'. Scores will be scaled to 100%.")
                
            self.test_data[test_number] = {}
            row_count = 0
            
            for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                full_name = clean_name(row[name_col - 1] if name_col <= len(row) else "")
                email = clean_email(row[email_col - 1] if email_col and email_col <= len(row) else "")
                
                # Handle test files that do not collect emails (SurveyHeart sometimes ignores them)
                if not email and full_name:
                    safe_name = re.sub(r'[^a-zA-Z0-9]', '', full_name.lower())
                    email = f"{safe_name}@no-email.local"
                
                score = parse_score(row[score_col - 1] if score_col <= len(row) else None)
                
                # Scale raw score (e.g., 17/17 -> 100%) so that final average logic works correctly
                if score is not None and scale_max and scale_max > 0:
                    if score <= scale_max:
                        score = round((score / scale_max) * 100.0, 1)
                
                is_valid, error_msg = validate_row_data(full_name, email, score)
                
                if is_valid:
                    self.test_data[test_number][email] = {
                        'name': full_name,
                        'score': score
                    }
                    row_count += 1
                    # Log first few records to verify correct file
                    if row_count <= 3:
                        logger.info(f"  Test {test_number} row {row_idx}: {full_name} = {score}")
                else:
                    if row_count == 0 and row_idx <= 5:
                        # Log early failures in detail to help debug column misalignment
                        logger.warning(f"  Row {row_idx} REJECTED: name='{full_name}', email='{email}', score={score} → {error_msg}")
                    else:
                        logger.warning(f"Row {row_idx} in test {test_number}: {error_msg}")
            
            logger.info(f"Loaded {row_count} valid records from test {test_number}")
            wb.close()
            return True
            
        except Exception as e:
            logger.error(f"Error loading {filepath.name}: {str(e)}")
            return False
    
    def load_all_tests(self, max_tests: Optional[int] = None) -> int:
        """
        Load all test files from input directory dynamically
        
        Args:
            max_tests (int): Maximum number of tests to load. If None, loads all found tests.
            
        Returns:
            int: Number of tests successfully loaded
        """
        loaded_count = 0
        
        logger.info(f"Loading tests from: {self.input_dir}")
        
        # List ALL files in directory first
        if self.input_dir.exists():
            all_files = list(self.input_dir.iterdir())
            logger.debug(f"All files in directory ({len(all_files)}): {[f.name for f in all_files]}")
        
        # Find all XLSX files and extract test numbers
        all_xlsx_files = sorted(self.input_dir.glob("*.xlsx"))
        test_nums = set()
        
        logger.info(f"Found {len(all_xlsx_files)} XLSX files")
        
        for f in all_xlsx_files:
            test_num = self._extract_test_number_from_file(f.name)
            logger.debug(f"  '{f.name}' -> Test {test_num}")
            if test_num:
                test_nums.add(test_num)
        
        logger.info(f"Detected test numbers: {sorted(test_nums)}")
        
        if not test_nums:
            logger.warning("No test files found in directory")
            return 0
        
        # Load each test
        for test_num in sorted(test_nums):
            matching_file = self._find_test_file(test_num)
            
            if matching_file:
                success = self.load_test_file(matching_file, test_num)
                if success:
                    loaded_count += 1
                    participant_count = len(self.test_data.get(test_num, {}))
                    logger.info(f"  Test {test_num}: {participant_count} participants loaded from {matching_file.name}")
                else:
                    logger.error(f"  Test {test_num}: FAILED to load from {matching_file.name}")
            else:
                logger.warning(f"  Test {test_num}: detected but file not found")
        
        logger.info(f"Total: {loaded_count} tests loaded successfully")
        return loaded_count
    
    def _find_test_file(self, test_num: int) -> Optional[Path]:
        """Find the file matching a specific test number"""
        logger.info(f"_find_test_file: Looking for Test {test_num}")
        files_checked = []
        for f in sorted(self.input_dir.glob("*.xlsx")):
            extracted = self._extract_test_number_from_file(f.name)
            files_checked.append((f.name, extracted))
            if extracted == test_num:
                logger.info(f"_find_test_file: Found Test {test_num} in file: {f.name}")
                return f
        
        logger.error(f"_find_test_file: Test {test_num} NOT FOUND! Files checked: {files_checked}")
        return None
    
    @staticmethod
    def _extract_test_number_from_file(filename: str) -> Optional[int]:
        """
        Extract test number from filename (matches _extract_test_number in telegram_bot)
        Supports: 'Test 1', 'test1', '1.xlsx', 'result_1', 'exam(1)', etc.
        """
        import re
        name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
        
        # Try 1: Look for "Test N" or "test N" format first
        match = re.search(r'[Tt]est\s*(\d+)', name_without_ext)
        if match:
            result = int(match.group(1))
            logger.debug(f"  Extract '{filename}': matched 'Test N' pattern -> {result}")
            return result
        
        # Try 2: Look for any number in the filename
        match = re.search(r'(\d+)', name_without_ext)
        if match:
            result = int(match.group(1))
            logger.debug(f"  Extract '{filename}': matched number pattern -> {result}")
            return result
        
        logger.warning(f"  Extract '{filename}': NO MATCH - no numbers found!")
        return None
    
    def validate_data_integrity(self) -> Dict:
        """
        Validate data integrity across all tests and return error report
        
        Returns:
            Dict with keys: 'valid', 'errors', 'warnings', 'missing_participants', 'name_mismatches', 'duplicate_scores'
        """
        report = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'missing_participants': [],  # Email in base test but missing in other tests
            'name_mismatches': [],  # Same email with different names
            'duplicate_scores': [],  # Same email with identical scores across tests
        }
        
        if not self.test_data:
            report['valid'] = False
            report['errors'].append("No test data loaded")
            return report
        
        # Use FIRST available test as base (not hardcoded Test 1)
        available_tests = sorted(self.test_data.keys())
        base_test = available_tests[0]
        
        base_test_emails = set(self.test_data[base_test].keys())
        test_nums = sorted(self.test_data.keys())
        
        # Check each base test participant
        for email, base_test_data in self.test_data[base_test].items():
            base_test_name = base_test_data['name']
            base_test_score = base_test_data['score']
            
            # Check for missing in other tests
            for test_num in test_nums:
                if test_num != base_test:
                    if email not in self.test_data[test_num]:
                        report['missing_participants'].append({
                            'email': email,
                            'name': base_test_name,
                            'missing_in_test': test_num
                        })
            
            # Check for name mismatches across tests
            name_variants = {base_test_name}
            for test_num in test_nums:
                if test_num != base_test and email in self.test_data[test_num]:
                    other_name = self.test_data[test_num][email]['name']
                    if other_name.lower() != base_test_name.lower():
                        name_variants.add(other_name)
                        report['name_mismatches'].append({
                            'email': email,
                            'test_1_name': base_test_name,
                            'test_num': test_num,
                            'conflicting_name': other_name
                        })
            
            # Check for duplicate scores (possible copy-paste error)
            scores_by_test = {}
            scores_by_test[base_test] = base_test_score
            for test_num in test_nums:
                if test_num != base_test and email in self.test_data[test_num]:
                    scores_by_test[test_num] = self.test_data[test_num][email]['score']
            
            # Flag if all scores are identical
            unique_scores = set(scores_by_test.values())
            if len(unique_scores) == 1 and len(scores_by_test) > 1:
                report['duplicate_scores'].append({
                    'email': email,
                    'name': base_test_name,
                    'score': base_test_score,
                    'in_tests': sorted(scores_by_test.keys()),
                    'note': 'Identical scores in all tests - possible copy-paste error?'
                })
        
        # Set validity
        if report['errors'] or report['name_mismatches']:
            report['valid'] = False
        
        if report['missing_participants'] or report['duplicate_scores']:
            report['warnings'].append(
                f"{len(report['missing_participants'])} missing participant(s) and "
                f"{len(report['duplicate_scores'])} potential duplicate score(s)"
            )
        
        logger.info(f"Data integrity check: {len(report['missing_participants'])} missing, "
                   f"{len(report['name_mismatches'])} name mismatches, "
                   f"{len(report['duplicate_scores'])} duplicate scores")
        
        return report
    
    def consolidate_results(self) -> Dict:
        """
        Consolidate results from all tests into a single dataset dynamically.
        Collects ALL unique participants across ALL tests — no one is dropped
        for missing from one particular test.
        
        Returns:
            Dict: Consolidated data {email: {name, test_N_score, ...}}
        """
        if not self.test_data:
            logger.warning("No test data loaded")
            return {}
        
        available_tests = sorted(self.test_data.keys())
        if not available_tests:
            logger.error("No test data available for consolidation")
            return {}
        
        logger.info(f"Consolidating {len(available_tests)} tests: {available_tests}")
        for test_num in available_tests:
            logger.info(f"  Test {test_num}: {len(self.test_data[test_num])} participants")
        
        # --- KEY FIX ---
        # Step 1: Create a mapping of canonical names to real emails
        # This helps merge pseudo-emails (like shuaibu@no-email.local) with their real email from another test
        name_to_real_email = {}
        for test_num in available_tests:
            for email, data in self.test_data[test_num].items():
                if not email.endswith('@no-email.local'):
                    name_key = clean_name(data['name']).lower()
                    # Only register if we haven't seen this name yet, or keep the first valid email
                    if name_key not in name_to_real_email:
                        name_to_real_email[name_key] = email
        
        # Step 2: Build aligned participant data
        merged_test_data = {t: {} for t in available_tests}
        all_participants = {}  # {final_email: name}
        
        for test_num in available_tests:
            for email, data in self.test_data[test_num].items():
                name = data['name']
                name_key = clean_name(name).lower()
                
                # Resolve email: if pseudo-email, try to map to real email via name
                if email.endswith('@no-email.local') and name_key in name_to_real_email:
                    final_email = name_to_real_email[name_key]
                else:
                    final_email = email
                
                if final_email not in all_participants:
                    all_participants[final_email] = name
                
                merged_test_data[test_num][final_email] = data
        
        logger.info(f"Total unique participants across all tests: {len(all_participants)}")
        
        # Step 3: Build consolidated record for EVERY participant.
        # Score is None if participant was absent for that test.
        consolidated = {}
        for email, name in all_participants.items():
            record = {'name': name}
            for test_num in available_tests:
                if email in merged_test_data[test_num]:
                    record[f'test_{test_num}_score'] = merged_test_data[test_num][email]['score']
                else:
                    record[f'test_{test_num}_score'] = None
            consolidated[email] = record
        
        # Sort by name
        consolidated = dict(sorted(consolidated.items(),
                                   key=lambda x: x[1]['name'].lower()))
        
        logger.info(f"Consolidated: {len(consolidated)} unique participants across {len(available_tests)} tests")
        return consolidated
    
    def generate_preview_image(self, consolidated_data: Dict, max_rows: int = 12) -> Optional[Path]:
        """
        Generate a visual preview image showing consolidation summary and data table
        PIL is optional - returns None if not available
        
        Args:
            consolidated_data (Dict): Consolidated results
            max_rows (int): Maximum rows to show in preview
            
        Returns:
            Path: Path to generated image file, or None if failed or PIL not available
        """
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Get test numbers and stats
            test_nums = set()
            for data in consolidated_data.values():
                for key in data.keys():
                    if key.startswith('test_') and key.endswith('_score'):
                        test_nums.add(int(key.split('_')[1]))
            test_nums = sorted(test_nums)
            
            total_participants = len(consolidated_data)
            rows_to_show = min(max_rows, total_participants)
            
            # Image dimensions
            col_width = 150
            row_height = 30
            header_height = 100
            
            # Calculate image size
            num_cols = 2 + len(test_nums)  # Name + Email + Test scores
            img_width = col_width * num_cols + 20
            img_height = header_height + (rows_to_show + 1) * row_height + 80
            
            # Create image
            img = Image.new('RGB', (img_width, img_height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Use default font (PIL will use a basic font)
            try:
                title_font = ImageFont.truetype("arial.ttf", 16)
                header_font = ImageFont.truetype("arial.ttf", 12)
                data_font = ImageFont.truetype("arial.ttf", 10)
            except:
                # Fallback to default font
                title_font = ImageFont.load_default()
                header_font = ImageFont.load_default()
                data_font = ImageFont.load_default()
            
            # Draw header
            draw.text((10, 5), "📊 CONSOLIDATION PREVIEW", fill='black', font=title_font)
            draw.text((10, 30), f"Participants: {total_participants} | Tests: {', '.join(f'T{t}' for t in test_nums)}", 
                     fill='#333333', font=data_font)
            
            # Draw column headers
            y = header_height
            x = 10
            headers = ['Name', 'Email'] + [f'Test {t}' for t in test_nums]
            
            for col_idx, header in enumerate(headers):
                # Alternate header background
                if col_idx % 2 == 0:
                    draw.rectangle([(x, y), (x + col_width, y + row_height)], fill='#E8E8E8')
                else:
                    draw.rectangle([(x, y), (x + col_width, y + row_height)], fill='#F5F5F5')
                
                draw.rectangle([(x, y), (x + col_width, y + row_height)], outline='#CCCCCC')
                draw.text((x + 5, y + 8), header[:15], fill='black', font=header_font)
                x += col_width
            
            y += row_height
            
            # Draw data rows
            for row_idx, (email, data) in enumerate(consolidated_data.items()):
                if row_idx >= rows_to_show:
                    break
                
                x = 10
                name = data['name'][:20]  # Truncate long names
                
                # Alternate row colors
                row_color = '#FFFFFF' if row_idx % 2 == 0 else '#F9F9F9'
                
                # Draw Name
                draw.rectangle([(x, y), (x + col_width, y + row_height)], fill=row_color)
                draw.rectangle([(x, y), (x + col_width, y + row_height)], outline='#DDDDDD')
                draw.text((x + 5, y + 8), name, fill='black', font=data_font)
                x += col_width
                
                # Draw Email
                draw.rectangle([(x, y), (x + col_width, y + row_height)], fill=row_color)
                draw.rectangle([(x, y), (x + col_width, y + row_height)], outline='#DDDDDD')
                email_display = email[:18] + '..' if len(email) > 18 else email
                draw.text((x + 5, y + 8), email_display, fill='#666666', font=data_font)
                x += col_width
                
                # Draw scores with color coding
                for test_num in test_nums:
                    score = data.get(f'test_{test_num}_score')
                    score_text = str(int(score)) if score is not None else '—'
                    
                    # Get test color
                    if test_num in TEST_COLORS:
                        color_hex = TEST_COLORS[test_num]['rgb']
                        # Convert hex to RGB
                        color_rgb = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
                    else:
                        color_rgb = (200, 200, 200)
                    
                    # Lighten color for background
                    bg_color = tuple(min(255, c + 100) for c in color_rgb)
                    
                    draw.rectangle([(x, y), (x + col_width, y + row_height)], fill=bg_color)
                    draw.rectangle([(x, y), (x + col_width, y + row_height)], outline='#DDDDDD')
                    draw.text((x + col_width//2 - 15, y + 8), score_text, fill='black', font=data_font)
                    x += col_width
                
                y += row_height
            
            # Draw footer
            if total_participants > rows_to_show:
                draw.text((10, y + 10), f"... and {total_participants - rows_to_show} more participants", 
                         fill='#666666', font=data_font)
            
            draw.text((10, y + 40), "[OK] Scroll down to see validation alerts and confirm", 
                     fill='#228B22', font=data_font)
            
            # Save image
            output_path = Path(self.output_dir) / 'preview.png'
            img.save(output_path)
            logger.info(f"Generated preview image: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating preview image: {str(e)}")
            return None
    
    def save_consolidated_file(self, consolidated_data: Dict, output_filename: str = "Consolidated_Results.xlsx") -> bool:
        """
        Save consolidated results to Excel file with color coding (dynamic columns)
        Includes Grade 6 participation bonus and final average
        
        Args:
            consolidated_data (Dict): Consolidated results
            output_filename (str): Output filename
            
        Returns:
            bool: True if successful
        """
        try:
            # Apply participation bonuses if not already applied
            if consolidated_data:
                first_record = next(iter(consolidated_data.values()))
                if 'Grade_6_bonus' not in first_record:
                    logger.info("Applying participation bonuses...")
                    test_nums = []
                    for key in first_record:
                        if key.startswith('test_') and key.endswith('_score'):
                            test_num = int(key.split('_')[1])
                            test_nums.append(test_num)
                    test_nums = sorted(test_nums)
                    
                    calculator = ParticipationBonusCalculator()
                    consolidated_data = calculator.apply_bonuses_to_consolidated(
                        consolidated_data, test_nums
                    )
            
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Results"
            
            # Get number of tests from data keys
            test_nums = []
            if consolidated_data:
                first_record = next(iter(consolidated_data.values()))
                for key in first_record:
                    if key.startswith('test_') and key.endswith('_score'):
                        test_num = int(key.split('_')[1])
                        test_nums.append(test_num)
                test_nums = sorted(test_nums)
            
            # Create headers dynamically: Name, Email, Tests..., Assignment Score, Final Average, Status
            headers = (
                ['Full Name', 'Email'] + 
                [f'Test {num} Score' for num in test_nums] +
                ['Assignment Score', 'Final Average (%)', 'Status']
            )
            ws.append(headers)
            
            # Format header row
            for col_idx, header in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = openpyxl.styles.PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
                cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Add data rows
            for email, data in consolidated_data.items():
                row = [
                    data['name'], 
                    email
                ] + [
                    data.get(f'test_{num}_score') for num in test_nums
                ] + [
                    data.get('Grade_6_bonus'),
                    data.get('final_average'),
                    data.get('status', 'N/A')
                ]
                ws.append(row)
            
            # Apply color coding to test score columns
            for row_idx in range(2, len(consolidated_data) + 2):
                # Color test score columns
                for col_offset, test_num in enumerate(test_nums):
                    col_idx = col_offset + 3  # Column C onwards (A=name, B=email)
                    cell = ws.cell(row=row_idx, column=col_idx)
                    cell.fill = get_fill_for_test(test_num)
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                
                # Color Assignment Score column (light green)
                bonus_col = len(test_nums) + 3
                bonus_cell = ws.cell(row=row_idx, column=bonus_col)
                bonus_score = consolidated_data[list(consolidated_data.keys())[row_idx - 2]].get('Grade_6_bonus')
                if bonus_score is not None:
                    bonus_cell.fill = openpyxl.styles.PatternFill(
                        start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"
                    )
                bonus_cell.alignment = Alignment(horizontal='center', vertical='center')
                
                # Color Final Average column (yellow for >50%, red for <50%)
                avg_col = bonus_col + 1
                avg_cell = ws.cell(row=row_idx, column=avg_col)
                final_avg = consolidated_data[list(consolidated_data.keys())[row_idx - 2]].get('final_average', 0)
                if final_avg >= 50:
                    avg_cell.fill = openpyxl.styles.PatternFill(
                        start_color="FFF2CC", end_color="FFF2CC", fill_type="solid"
                    )
                else:
                    avg_cell.fill = openpyxl.styles.PatternFill(
                        start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"
                    )
                avg_cell.alignment = Alignment(horizontal='center', vertical='center')
                
                # Status column (green for PASS, red for FAIL)
                status_col = avg_col + 1
                status_cell = ws.cell(row=row_idx, column=status_col)
                status = consolidated_data[list(consolidated_data.keys())[row_idx - 2]].get('status', 'N/A')
                if status == 'PASS':
                    status_cell.fill = openpyxl.styles.PatternFill(
                        start_color="70AD47", end_color="70AD47", fill_type="solid"
                    )
                    status_cell.font = Font(bold=True, color="FFFFFF")
                elif status == 'FAIL':
                    status_cell.fill = openpyxl.styles.PatternFill(
                        start_color="E74C3C", end_color="E74C3C", fill_type="solid"
                    )
                    status_cell.font = Font(bold=True, color="FFFFFF")
                status_cell.alignment = Alignment(horizontal='center', vertical='center')
            
            # Adjust column widths
            ws.column_dimensions['A'].width = 25
            ws.column_dimensions['B'].width = 30
            for col_offset in range(len(test_nums)):
                col_letter = get_column_letter(col_offset + 3)
                ws.column_dimensions[col_letter].width = 15
            
            # Set widths for new columns
            grade6_col = get_column_letter(len(test_nums) + 3)
            avg_col = get_column_letter(len(test_nums) + 4)
            status_col = get_column_letter(len(test_nums) + 5)
            
            ws.column_dimensions[grade6_col].width = 18
            ws.column_dimensions[avg_col].width = 18
            ws.column_dimensions[status_col].width = 12
            
            output_path = self.output_dir / output_filename
            wb.save(output_path)
            logger.info(f"Saved consolidated results to {output_path}")
            logger.info(f"  - {len(test_nums)} test scores")
            logger.info(f"  - Grade 6 participation bonus")
            logger.info(f"  - Final average per participant")
            logger.info(f"  - Pass/Fail status (50% pass mark)")
            return True
            
        except Exception as e:
            logger.error(f"Error saving consolidated file: {str(e)}")
            return False
    
    def save_as_pdf(self, consolidated_data: Dict, output_filename: str = "Consolidated_Results.pdf") -> bool:
        """
        Stub for PDF export. 
        Note: Currently disabled due to missing reportlab dependency.
        """
        logger.warning("PDF export is currently disabled. Add 'reportlab' to requirements.txt to enable.")
        return False

    def save_as_docx(self, consolidated_data: Dict, output_filename: str = "Consolidated_Results.docx") -> bool:
        """
        Stub for DOCX export.
        Note: Currently disabled due to missing python-docx dependency.
        """
        logger.warning("DOCX export is currently disabled. Add 'python-docx' to requirements.txt to enable.")
        return False
