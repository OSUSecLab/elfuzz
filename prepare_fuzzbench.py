import click
import os.path
import subprocess
import sys
import shutil
from util import *

class DirMap:
    def __init__(self, project_dir: str, entry_file: str):
        self.project_dir = project_dir
        self.entry_file = entry_file

def get_dirmap() -> DirMap:
    global ELMFUZZ_RUNDIR
    with open(os.path.join(ELMFUZZ_RUNDIR, 'dirmap')) as dirmap_f:
        keyvalue = dict()
        for l in dirmap_f:
            k, v = l.strip().split('=')
            keyvalue[k.strip()] = v.strip()
        return DirMap(keyvalue['project_dir'], keyvalue['entry_file'])

def make_build_dir(fuzzbench_dir: str, patch_info: tuple[str, str, str] | None = None, oss_fuzz: bool = False) -> str:
    global ELMFUZZ_RUNDIR
    print(f"DEBUG: {ELMFUZZ_RUNDIR=}")
    if oss_fuzz:
        fuzzbench_project = get_config('oss_fuzz_project')
    else:
        fuzzbench_project = get_config('fuzzbench_project')
    assert isinstance(fuzzbench_project, str)
    if oss_fuzz:
        project_dir = os.path.join(fuzzbench_dir, 'projects', fuzzbench_project)
    else:
        project_dir = os.path.join(fuzzbench_dir, 'benchmarks', fuzzbench_project)
    project_name = get_config('project_name')
    dirmap = get_dirmap()
    with open(f'./fuzzbench/{project_name}/template.Dockerfile') as template_file, \
         open(os.path.join(project_dir, 'Dockerfile')) as original_dockerfile:
        template = template_file.read().replace('FROM ghcr.io/cychen2021/placeholder', '')
        original = original_dockerfile.read()
        template = template.replace('#$include_dockerfile$', original)
        template = template.replace('$__PROJECT_DIR', dirmap.project_dir)
        template = template.replace('$__ENTRY_FILE', dirmap.entry_file)
        
        if ON_GLADE and patch_info is not None:
            template = template.replace(f'#$ON_GLADE$', '')
            if patch_info[0]:
                to_insert = [
                    f'COPY ./{patch_info[0]} /src/',
                    f'COPY ./glade_patch.sh /src/',
                    f'RUN chmod 777 /src/glade_patch.sh'
                ]
                template = template.replace('#$ON_GLADE:INSERT$', '\n'.join(to_insert))

        lines = template.split('\n')
        
        new_lines = []
        for i in range(len(lines)):
            l = lines[i]
            new_lines.append(l)
            if l.startswith('#$if_project$'):
                cond = l.removeprefix('#$if_project$').strip()
                if cond == project_name:
                    next_line = lines[i+1]
                    assert next_line.startswith('#$then$')
                    new_next_line = next_line.removeprefix('#$then$').strip()
                    new_lines.append(new_next_line)
        if ON_GLADE and patch_info is not None and patch_info[0]:
            GLADE_DIR = os.path.join('evaluation', 'glade')
            shutil.copy(os.path.join(GLADE_DIR, patch_info[0]), project_dir)
        project = os.path.basename(project_dir.removesuffix('/'))
        if ON_GLADE and patch_info is not None:
            if project == 're2_fuzzer' or project == 'librsvg':
                pass
            else:
                with open('glade_patch.sh') as sh_template_file:
                    sh_template = sh_template_file.read()
                    sh_template = sh_template.replace('$PROJECT_DIR', f'/src/{dirmap.project_dir}')
                    sh_template = sh_template.replace('$PATCH_FILE', f'/src/{patch_info[0]}')
                with open(os.path.join(project_dir, 'glade_patch.sh'), 'w') as sh_file:
                    sh_file.write(sh_template)
        
        template = '\n'.join(new_lines)
    dockerfile_path = os.path.join(project_dir, 'elm.Dockerfile')
    if os.path.exists(f'./{ELMFUZZ_RUNDIR}/elm_main.cc'):
        shutil.copy(f'./{ELMFUZZ_RUNDIR}/elm_main.cc', project_dir)
    if os.path.exists(f'./{ELMFUZZ_RUNDIR}/elm_main.c'):
        shutil.copy(f'./{ELMFUZZ_RUNDIR}/elm_main.c', project_dir)
    if os.path.exists(f'./{ELMFUZZ_RUNDIR}/elm_main.rs'):
        shutil.copy(f'./{ELMFUZZ_RUNDIR}/elm_main.rs', project_dir)
    if os.path.exists(f'./{ELMFUZZ_RUNDIR}/elm_main.py'):
        shutil.copy(f'./{ELMFUZZ_RUNDIR}/elm_main.py', project_dir)
    
    if ON_GLADE and patch_info is not None and patch_info[0]:
        original_main = os.path.abspath(os.path.join(project_dir, patch_info[2]))
        patch_main = os.path.abspath(os.path.join(GLADE_DIR, patch_info[1]))

        patch_cmd = ['patch', '-i', patch_main, original_main]
        subprocess.run(patch_cmd, check=True, stdout=sys.stdout, stderr=sys.stderr, cwd=project_dir)

        if project == 're2_fuzzer':
            original_target_cc = os.path.abspath('/home/appuser/fuzzbench/benchmarks/re2_fuzzer/target.cc')
            backup_cmd = ['cp', original_target_cc, original_target_cc + '.bak']
            subprocess.run(backup_cmd, check=True, stdout=sys.stdout, stderr=sys.stderr, cwd=project_dir)
            patch_target_cc = os.path.abspath(os.path.join(GLADE_DIR, patch_info[0]))
            patch_cmd = ['patch', '-i', patch_target_cc, original_target_cc]
            subprocess.run(patch_cmd, check=True, stdout=sys.stdout, stderr=sys.stderr, cwd=project_dir)

    for p, ds, fs in os.walk(f'./fuzzbench/{project_name}/'):
        for f in fs:
            if f.startswith('template'):
                continue
            shutil.copy(os.path.join(p, f), project_dir)
        assert not ds
    with open(dockerfile_path, 'w') as dockerfile:
        dockerfile.write(template)
    return project_dir

def build_image(project_dir: str):
    project_name = get_config('project_name')
    cmd = [
        'docker',
        'build',
        '--progress', 'plain',
        '-f', './elm.Dockerfile',
        '-t', f'elmfuzz/{project_name}{"_glade" if ON_GLADE else ""}',
        '.'
    ]
    subprocess.run(cmd, check=True, stdout=sys.stdout, stderr=sys.stderr, cwd=project_dir)
    project = os.path.basename(project_dir.removesuffix('/'))
    if project == 're2_fuzzer' and ON_GLADE:
        recover_cmd = ['cp', os.path.join(project_dir, 'target.cc.bak'), os.path.join(project_dir, 'target.cc')]
        subprocess.run(recover_cmd, check=True, stdout=sys.stdout, stderr=sys.stderr, cwd=project_dir)

PATCHES = {
    'jsoncpp': (
        'jsoncpp_glade.patch',
        'jsoncpp_elfmain_glade.diff',
        'elm_main.cc'
    ),
    'libxml2': (
        'libxml2_glade.patch',
        'libxml2_elfmain_glade.diff',
        'elm_main.c'
    ),
    're2': (
        're2_glade.diff',
        're2_elfmain_glade.diff',
        'elm_main.cc'
    ),
    'librsvg': (
        '',
        '',
        ''
    )
}

ON_GLADE = False

@click.command()
@click.option('--fuzzbench-dir', '-d', 'fuzzbench_dir', type=str, default='/home/appuser/fuzzbench')
@click.option('--preset-type', '-t', 'preset_type', type=str, default='fuzzbench')
@click.option('--glade', '-g', 'glade', is_flag=True, default=False)
def main(fuzzbench_dir: str, preset_type: str, glade: bool):
    global ELMFUZZ_RUNDIR
    global ON_GLADE
    ON_GLADE = glade
    project = ELMFUZZ_RUNDIR.removesuffix('/').split('/')[-1]
    match preset_type:
        case 'fuzzbench':
            project_dir = make_build_dir(fuzzbench_dir, patch_info=PATCHES[project] if project in PATCHES else None)
            build_image(project_dir)
        case 'oss-fuzz':
            project_dir = make_build_dir(fuzzbench_dir, patch_info=PATCHES[project] if project in PATCHES else None, oss_fuzz=True)
            build_image(project_dir)
        case 'docker':
            build_image(ELMFUZZ_RUNDIR)

if __name__ == '__main__':
    ELMFUZZ_RUNDIR = os.environ.get('ELMFUZZ_RUNDIR', 'preset/jsoncpp')
    main()
