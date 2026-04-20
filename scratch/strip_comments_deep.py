import tokenize
import io
import os

def strip_python(source):
    io_obj = io.StringIO(source)
    out = ""
    last_lineno = -1
    last_col = 0
    
    try:
        tokens = list(tokenize.generate_tokens(io_obj.readline))
    except Exception:
        return source

    # Identify docstrings: triple-quoted strings that appear as statements
    docstring_indices = []
    for i, tok in enumerate(tokens):
        if tok.type == tokenize.STRING:
            # Check if it's a docstring (triple-quoted and not part of an expression)
            if tok.string.startswith(('"""', "'''")):
                # Check preceding tokens
                idx = i - 1
                is_statement = True
                while idx >= 0:
                    prev = tokens[idx]
                    if prev.type in (tokenize.NL, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
                        break
                    if prev.type == tokenize.OP and prev.string == ':': # following a dev/class/etc.
                        break
                    if prev.type != tokenize.COMMENT:
                        is_statement = False
                        break
                    idx -= 1
                
                # Check following tokens
                if is_statement:
                    idx = i + 1
                    while idx < len(tokens):
                        nxt = tokens[idx]
                        if nxt.type in (tokenize.NL, tokenize.NEWLINE, tokenize.DEDENT):
                            break
                        if nxt.type != tokenize.COMMENT:
                            is_statement = False
                            break
                        idx += 1
                
                if is_statement:
                    docstring_indices.append(i)

    for i, tok in enumerate(tokens):
        if tok.type == tokenize.COMMENT:
            continue
        if i in docstring_indices:
            continue
            
        if tok.start[0] > last_lineno:
            last_col = 0
        if tok.start[1] > last_col:
            out += " " * (tok.start[1] - last_col)
            
        out += tok.string
        last_lineno = tok.end[0]
        last_col = tok.end[1]
        
    return out

def process_file(filepath):
    print(f"Deep stripping {filepath}...")
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    if filepath.endswith('.py'):
        stripped = strip_python(content)
        # Final cleanup of excessive whitespace
        lines = [line.rstrip() for line in stripped.split('\n')]
        final_lines = []
        for line in lines:
            if line.strip() or (final_lines and final_lines[-1].strip()):
                final_lines.append(line)
        stripped = '\n'.join(final_lines)
    else:
        stripped = content

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(stripped)

def main():
    targets = [
        'test_collation_automation.py',
        'data_validator.py',
        'master_automation.py',
        'telegram_bot.py',
        'config.py'
    ]
    for root, dirs, files in os.walk('src'):
        for f in files:
            if f.endswith('.py'):
                targets.append(os.path.join(root, f))
    for f in targets:
        if os.path.exists(f):
            process_file(f)

if __name__ == "__main__":
    main()
