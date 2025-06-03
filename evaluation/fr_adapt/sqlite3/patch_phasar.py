import os
import sys
import os.path


HEADER_FILE = '/phasar/include/phasar/PhasarLLVM/Pointer/LLVMPointsToSet.h'
MAIN_FILE = '/phasar/lib/PhasarLLVM/Pointer/LLVMPointsToSet.cpp'

INIT_FILE1 = '/phasar/lib/PhasarLLVM/Pointer/LLVMPointsToSet.cpp'

if __name__ == '__main__':
    with open(MAIN_FILE, 'r') as f:
        lines = f.readlines()
    locate = lines.index('void LLVMPointsToSet::computeFunctionsPointsToSet(llvm::Function *F) {\n')
    with open('/src/funcs_fallback_to_steens.txt', 'r') as f:
        conds = [l.strip() for l in f.readlines()]
    if not conds:
        conds = ['false']
    new_lines = lines[:locate]
    new_lines.extend([
        'bool fallbackToSimplePTA(llvm::Function *F) {\n',
        '    return ' + ' || '.join(conds) + ';\n',
        '}\n',
    ])
    new_lines.extend(
        '  llvm::AAResults &AA = fallbackToSimplePTA(F) ? *SimplePTA.getAAResults(F) : *PTA.getAAResults(F);\n'
        if l == '  llvm::AAResults &AA = *PTA.getAAResults(F);\n'
        else l
        for l in lines[locate:]
    )
    with open(MAIN_FILE, 'w') as f:
        f.writelines(new_lines)

    with open(HEADER_FILE, 'r') as f:
        lines = f.readlines()
    lines.insert(45, 'LLVMBasedPointsToAnalysis SimplePTA;\n')
    
    with open(HEADER_FILE, 'w') as f:
        f.writelines(lines)
    
    with open(INIT_FILE1, 'r') as f:
        lines = f.readlines()
    assert lines[52].strip() == ': PTA(IRDB, UseLazyEvaluation, PATy) {'
    lines[52] = ': PTA(IRDB, UseLazyEvaluation, PATy), SimplePTA(IRDB, UseLazyEvaluation, PointerAnalysisType::CFLSteens) {\n'
    with open(INIT_FILE1, 'w') as f:
        f.writelines(lines)
