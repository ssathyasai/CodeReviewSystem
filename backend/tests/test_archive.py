import io
import zipfile
import pytest
from pathlib import Path

from backend.app.services.archive_service import ArchiveService, ArchiveSecurityError

def test_safe_zip_extraction(tmp_path):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("main.py", "print('hello world')")
        zf.writestr("utils/helper.py", "def add(a, b): return a + b")

    zip_file = tmp_path / "test.zip"
    zip_file.write_bytes(zip_buffer.getvalue())

    target_dir = tmp_path / "extracted"
    success, msg, meta = ArchiveService.validate_and_extract_zip(zip_file, target_dir)

    assert success is True
    assert (target_dir / "main.py").exists()
    assert (target_dir / "utils" / "helper.py").exists()


def test_path_traversal_zip_blocked(tmp_path):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("../../etc/passwd", "root:x:0:0:")

    zip_file = tmp_path / "evil.zip"
    zip_file.write_bytes(zip_buffer.getvalue())

    target_dir = tmp_path / "extracted"
    with pytest.raises(ArchiveSecurityError) as exc_info:
        ArchiveService.validate_and_extract_zip(zip_file, target_dir)
    
    assert "Suspicious path" in str(exc_info.value) or "Path traversal" in str(exc_info.value)
