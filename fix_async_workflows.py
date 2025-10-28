#!/usr/bin/env python3
"""Fix async/sync issues in Wave 2 workflow files."""

import re
from pathlib import Path

WORKFLOW_FILES = [
    "tesseract_flow/workflows/lore_expansion.py",
    "tesseract_flow/workflows/multi_task_benchmark.py",
    "tesseract_flow/workflows/character_profile.py",
    "tesseract_flow/workflows/multi_domain.py",
]

def fix_workflow_file(filepath: Path) -> None:
    """Fix async/sync issues in a workflow file."""
    content = filepath.read_text()
    original = content

    # 1. Change "async def _" to "def _" for node functions
    content = re.sub(r'async def (_\w+)\(self, state:', r'def \1(self, state:', content)

    # 2. Change "await strategy.generate(" to use asyncio.run pattern
    # Find all await strategy.generate calls and wrap them
    def replace_await_generate(match):
        indent = match.group(1)
        varname = match.group(2)
        rest_of_line = match.group(3)

        # Build the replacement with asyncio.run
        return (
            f"{indent}import asyncio\n"
            f"{indent}try:\n"
            f"{indent}    {varname} = asyncio.run(strategy.generate({rest_of_line}\n"
            f"{indent}except RuntimeError:\n"
            f"{indent}    loop = asyncio.new_event_loop()\n"
            f"{indent}    try:\n"
            f"{indent}        {varname} = loop.run_until_complete(strategy.generate({rest_of_line}\n"
            f"{indent}    finally:\n"
            f"{indent}        loop.close()\n"
        )

    # Simpler approach: Just replace "await" with asyncio.run wrapper
    content = re.sub(
        r'(\s+)(\w+) = await strategy\.generate\(',
        r'\1\2 = asyncio.run(strategy.generate(',
        content
    )

    # 3. Add asyncio import at top if not present
    if 'import asyncio' not in content and 'asyncio.run' in content:
        # Find the imports section and add asyncio
        import_section = re.search(r'(from __future__ import annotations\n)', content)
        if import_section:
            content = content.replace(
                'from __future__ import annotations\n',
                'from __future__ import annotations\n\nimport asyncio\n'
            )

    if content != original:
        print(f"Fixed {filepath}")
        filepath.write_text(content)
    else:
        print(f"No changes needed for {filepath}")

def main():
    """Fix all workflow files."""
    base = Path(__file__).parent

    for filepath_str in WORKFLOW_FILES:
        filepath = base / filepath_str
        if filepath.exists():
            fix_workflow_file(filepath)
        else:
            print(f"WARNING: {filepath} not found")

if __name__ == "__main__":
    main()
