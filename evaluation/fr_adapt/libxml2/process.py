with open('/src/elmbuild.sh') as bf:
    bf_lines = bf.readlines()
new_bf_lines = []
for i, line in enumerate(bf_lines):
    if i == 4:
        line.startswith('export')
        new_bf_lines.append(f'# {line}')
    else:
        new_bf_lines.append(line)
with open('/src/elmbuild.sh', 'w') as bf:
    bf.writelines(new_bf_lines)
    
with open('/src/libxml2/fuzz/genSeed.c') as tmpf:
    tmpf_text = tmpf.read()
with open('/src/libxml2/fuzz/genSeed.c', 'w') as tmpf:
    tmpf.write('\n'.join([
        '#ifdef FRCOV',
        '#define FIXREVERTER_SIZE 4815',
        'short FIXREVERTER[FIXREVERTER_SIZE];',
        '#endif'
    ])+'\n'+tmpf_text)
