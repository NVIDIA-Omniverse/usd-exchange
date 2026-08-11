import re
from pathlib import Path

DOC = Path('.agents/skills/getting-started/SKILL.md')

def test_deep_copy_preserves_links_and_copies_contents():
    text = DOC.read_text(encoding='utf-8')
    section_match = re.search(
        r'The output goes to `_install/`\. Deep-copy it.*?(?=## |$)',
        text,
        re.DOTALL,
    )
    assert section_match, 'deep-copy section not found'
    section = section_match.group(0)

    linux = re.search(r'- Linux:\s*`([^`]+)`', section)
    windows = re.search(r'- Windows:\s*`([^`]+)`', section)
    assert linux and windows, 'copy commands not found'

    linux_cmd = linux.group(1)
    assert '-L' not in linux_cmd, 'Linux cp must not use -L (follows symlinks)'
    assert 'usdex/' in linux_cmd, 'destination should be the project usdex folder'
    assert '_install/.' in linux_cmd or '_install/*' in linux_cmd, (
        'Linux cp should copy _install contents, not the _install directory itself'
    )

    win_cmd = windows.group(1)
    assert '/E' in win_cmd, 'Windows robocopy should use /E to include empty dirs'

if __name__ == '__main__':
    test_deep_copy_preserves_links_and_copies_contents()
