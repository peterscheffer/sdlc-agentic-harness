"""Unit tests for coding.py's ARCH.md target-file parsing and LLM-output file
writing — regressions found by running the harness against a real LLM
(gemma4:12b-mlx via Ollama), whose output style the mock fixtures never
exercised: backtick-wrapped table cells, variable-length separator rows, and
sequential unlabeled code fences with no per-file headers.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / ".scripts"))

from nodes.coding import _parse_target_files, _write_generated_files

ARCH_WITH_BACKTICKS = """# ARCH.md

## Target Files

| File | Action | Description |
|-------|--------|-------------|
| `app/main.py` | Create | Entry point |
| `app/routes.py` | Create | Routes |

## Design Decisions
"""


class TestParseTargetFiles:
    def test_strips_backticks_from_filenames(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        Path("ARCH.md").write_text(ARCH_WITH_BACKTICKS)
        files = _parse_target_files("ARCH.md")
        assert files == ["app/main.py", "app/routes.py"]

    def test_variable_length_separator_row_excluded(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        Path("ARCH.md").write_text(ARCH_WITH_BACKTICKS)
        files = _parse_target_files("ARCH.md")
        assert "-------" not in files
        assert not any(set(f) <= {"-"} for f in files)


class TestWriteGeneratedFiles:
    def test_dotted_code_inside_file_does_not_truncate_match(self, tmp_path, monkeypatch):
        # Regression: found on a real Ollama run. The header-matching regex
        # used to accept a bare "word.word" line (no "### " prefix) as an
        # implicit file boundary, so ordinary code containing an attribute
        # access or method call (e.g. "app.include_router(...)") truncated
        # the file's captured content right there, losing everything after
        # it — including the closing fence, so the raw "```" landed as
        # trailing garbage or a subsequent file inherited the rest.
        monkeypatch.chdir(tmp_path)
        targets = ["app/main.py", "app/routes.py"]
        llm_content = (
            "### app/main.py\n```python\n"
            "from fastapi import FastAPI\n"
            "from .routes import router as task_router\n\n"
            "app = FastAPI()\n\n"
            "app.include_router(task_router)\n"
            "```\n\n"
            "### app/routes.py\n```python\nx = 1\n```\n"
        )
        _write_generated_files(targets, llm_content)
        content = Path("app/main.py").read_text()
        assert "app.include_router(task_router)" in content
        assert "```" not in content
        assert Path("app/routes.py").read_text().strip() == "x = 1"

    def test_unclosed_fence_with_trailing_narration_is_stripped(self, tmp_path, monkeypatch):
        # Regression: found on a real Ollama run. A model closed a file's
        # fence, then appended trailing narration ("*(Note: ... was removed
        # as requested)*") OUTSIDE the fence but still inside this file's
        # captured segment (before the next "### " header). The opening
        # "```python" marker must be stripped even when the closing marker
        # isn't the very last line of the captured content, and the
        # trailing narration after the close marker must be discarded too.
        monkeypatch.chdir(tmp_path)
        targets = ["app/main.py"]
        llm_content = (
            "### app/main.py\n"
            "```python\n"
            "import requests\n\n"
            "def handler():\n"
            "    return requests.get('/')\n"
            "```\n"
            "*(Note: removed an unused import as requested)*\n"
        )
        _write_generated_files(targets, llm_content)
        content = Path("app/main.py").read_text()
        assert content.strip() == "import requests\n\ndef handler():\n    return requests.get('/')"
        assert "```" not in content
        assert "Note" not in content

    def test_headered_content_matches_exactly(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        targets = ["app/main.py", "app/routes.py"]
        llm_content = (
            "### app/main.py\n```python\nprint('main')\n```\n"
            "### app/routes.py\n```python\nprint('routes')\n```\n"
        )
        _write_generated_files(targets, llm_content)
        assert Path("app/main.py").read_text().strip() == "print('main')"
        assert Path("app/routes.py").read_text().strip() == "print('routes')"

    def test_sequential_unlabeled_fences_assigned_in_order(self, tmp_path, monkeypatch):
        # Regression: a real model (gemma4:12b-mlx) emitted target files as
        # sequential fenced blocks with NO "### filename" headers at all, in
        # the same order as the architecture's Target Files table.
        monkeypatch.chdir(tmp_path)
        targets = ["config/config.json", "requirements.txt", "app/store.py"]
        llm_content = (
            "```json\n{\"port\": 8000}\n```\n\n"
            "```text\nfastapi==0.109.0\n```\n\n"
            "```python\nclass TaskStore:\n    pass\n```\n"
        )
        _write_generated_files(targets, llm_content)
        assert Path("config/config.json").read_text().strip() == '{"port": 8000}'
        assert Path("requirements.txt").read_text().strip() == "fastapi==0.109.0"
        assert Path("app/store.py").read_text().strip() == "class TaskStore:\n    pass"

    def test_no_headers_no_matching_fence_count_leaves_files_missing(self, tmp_path, monkeypatch):
        # Regression: previously this case dumped the ENTIRE raw response
        # (including narration text and every other file's code) into every
        # unmatched target file, guaranteeing syntax errors everywhere. It
        # must now leave ambiguous files missing instead of corrupting them.
        monkeypatch.chdir(tmp_path)
        targets = ["app/main.py", "app/routes.py", "app/store.py"]
        llm_content = (
            "I fixed the issue by removing stray CSS.\n\n"
            "```python\nprint('only one block for three files')\n```\n"
        )
        _write_generated_files(targets, llm_content)
        assert not os.path.exists("app/main.py")
        assert not os.path.exists("app/routes.py")
        assert not os.path.exists("app/store.py")

    def test_single_target_file_still_gets_raw_content(self, tmp_path, monkeypatch):
        # Backward-compat: with exactly one target file and no headers/fences,
        # the whole response unambiguously belongs to that one file (this is
        # the shape the mock LLM fixture produces).
        monkeypatch.chdir(tmp_path)
        targets = ["src/feature.py"]
        llm_content = "# Generated code\ndef hello():\n    return 'Hello, World!'\n"
        _write_generated_files(targets, llm_content)
        assert Path("src/feature.py").read_text().strip() == llm_content.strip()

    def test_backtick_wrapped_header_still_matches(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        targets = ["app/main.py"]
        llm_content = "### `app/main.py`\n```python\nprint('x')\n```\n"
        _write_generated_files(targets, llm_content)
        assert Path("app/main.py").read_text().strip() == "print('x')"

    def test_single_target_file_with_narration_and_fence_extracts_fence(self, tmp_path, monkeypatch):
        # Regression: found on a real Ollama run — a retry-iteration response
        # with a single target file left to fix contained narration text
        # ("I fixed the syntax error by...") plus one fenced code block, no
        # "### filename" header. The single-remaining-file fallback used to
        # write the raw response verbatim (fence markers and narration
        # included), landing "```python" as literal line 1 and reintroducing
        # the exact SyntaxError it was supposed to fix.
        monkeypatch.chdir(tmp_path)
        targets = ["app/main.py"]
        llm_content = (
            "I fixed the syntax error by removing stray CSS.\n\n"
            "```python\nprint('main')\n```\n"
        )
        _write_generated_files(targets, llm_content)
        content = Path("app/main.py").read_text()
        assert content.strip() == "print('main')"
        assert "```" not in content
        assert "I fixed" not in content
