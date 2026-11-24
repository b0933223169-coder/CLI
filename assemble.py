"""把 core.cpp + 各 slots 部分組裝成完整的 backend.cpp。"""
from pathlib import Path

HERE = Path(__file__).parent
core = (HERE / 'core.cpp').read_text(encoding='utf-8').rstrip()
parts = []
for name in ['slots_part1.cpp','slots_part2.cpp','slots_part3.cpp','slots_part4.cpp','helper_add.cpp']:
    p = (HERE / name).read_text(encoding='utf-8').rstrip()
    parts.append(p)

full = core + '\n\n' + '\n\n'.join(parts) + '\n'
(HERE / 'backend.cpp').write_text(full, encoding='utf-8')
print('backend.cpp assembled:', len(full.splitlines()), 'lines')
