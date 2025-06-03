import os.path
import tempfile
import click as clk
import subprocess
import sys

ISLEARN_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(ISLEARN_DIR, '..', '..'))
GRAMMAR_DIRS = {
    'jsoncpp': 'json/isla',
    'libxml2': 'xml/isla',
    'php': 'php/isla_patched',
    're2': 're2/isla',
    'sqlite3': 'sqlite/isla',
    'cvc5': 'smtlib2/isla',
    'librsvg': 'xml/isla',
    'cpython3': 'python3/isla_patched'
}

def replace(text: str, target) -> str:
    return text \
            .replace('__PROJECT_DIR', target) \
            .replace('__GRAMMAR_DIR', GRAMMAR_DIRS[target]) \
            .replace('__ISLA_TARGET', target)
    
@clk.command()
@clk.argument('target', type=clk.Choice(['jsoncpp', 'libxml2', 'php', 're2', 'sqlite3', 'cvc5', 'librsvg', 'cpython3']), required=True)
@clk.option('--no-cache', is_flag=True, default=False, required=False)
def main(target, no_cache):
    with open(os.path.join(ISLEARN_DIR, 'islearn.Dockerfile')) as template:
        template_lines = template.readlines()
    df_lines = []
    for i, line in enumerate(template_lines):
        if line.strip() == '#$import_base$':
            df_lines.append(f'FROM elmfuzz/{target}\n')
        elif i >= 1 and template_lines[i-1].strip() == '#$import_base$':
            pass
        elif line.strip() in ['#$cond_positive$', '#$cond_negative$', '#$cond_post$', '#$cond_build$']:
            pass
        elif i > 0 and template_lines[i-1].strip() == '#$cond_positive$':
            if os.path.exists(os.path.join(ISLEARN_DIR, 'oracles', target, 'positive_seeds.tar.xz')):
                df_lines.append(replace(line, target))
        elif i > 0 and template_lines[i-1].strip() == '#$cond_negative$':
            if os.path.exists(os.path.join(ISLEARN_DIR, 'oracles', target, 'negative_seeds.tar.xz')):
                df_lines.append(replace(line, target))
        elif i > 0 and template_lines[i-1].strip() == '#$cond_post$':
            if os.path.exists(os.path.join(ISLEARN_DIR, 'oracles', target, 'postprocess.py')):
                df_lines.append(replace(line, target))
        elif i > 0 and template_lines[i-1].strip() == '#$cond_build$':
            if os.path.exists(os.path.join(ISLEARN_DIR, 'oracles', target, 'elmbuild.sh')):
                df_lines.append(replace(line, target))
        else:
            df_lines.append(replace(line, target))
        
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as df:
        df.writelines(df_lines)
        
    cmd = ['docker', 'build', 
           '-t', f'elmfuzz/{target}_islearn', 
           '-f', df.name,
           '--progress', 'plain' ] + (['--no-cache'] if no_cache else []) + ['.']
    
    subprocess.check_call(cmd, cwd=PROJECT_ROOT, stdout=sys.stdout, stderr=sys.stderr)

    os.remove(df.name)

if __name__ == '__main__':
    main()
    
