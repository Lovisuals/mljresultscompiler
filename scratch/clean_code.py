import tokenize
import io
import os
from pathlib import Path

def remove_comments_and_docstrings(source):
    io_obj = io.StringIO(source)
    out = ""
    prev_toktype = tokenize.INDENT
    last_lineno = -1
    last_col = 0

    tokens = tokenize.generate_tokens(io_obj.readline)
    for tok in tokens:
        token_type = tok.type
        token_string = tok.string
        start_line, start_col = tok.start
        end_line, end_col = tok.end

        if start_line > last_lineno:
            last_col = 0
        if start_col > last_col:
            out += (" " * (start_col - last_col))

        if token_type == tokenize.COMMENT:
            pass
        elif token_type == tokenize.STRING:
            if prev_toktype == tokenize.INDENT or prev_toktype == tokenize.NEWLINE or prev_toktype == tokenize.NL:
                pass
            else:
                out += token_string
        else:
            out += token_string

        prev_toktype = token_type
        last_lineno = end_line
        last_col = end_col

    return out

def process_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    clean_content = remove_comments_and_docstrings(content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(clean_content)

def main():
    root = Path('.')
    for py_file in root.rglob('*.py'):
        if 'venv' in str(py_file) or '.gemini' in str(py_file):
            continue
        print(f"Cleaning {py_file}...")
        try:
            process_file(py_file)
        except Exception as e:
            print(f"Error cleaning {py_file}: {e}")

if __name__ == "__main__":
    main()
