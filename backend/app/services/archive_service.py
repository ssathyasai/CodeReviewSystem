import os
import shutil
import zipfile
import uuid
from pathlib import Path
from typing import Tuple, List, Dict, Any

from backend.app.config import settings

class ArchiveSecurityError(Exception):
    pass

class ArchiveService:
    @staticmethod
    def validate_and_extract_zip(zip_path: Path, target_dir: Path) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Safely inspects and extracts a ZIP archive into target_dir.
        Enforces:
        - Valid ZIP structure
        - Max compressed file size
        - Max uncompressed total size (ZIP bomb protection)
        - Max total files limit
        - Path traversal / Directory breakout protection
        - Symlink attack protection
        """
        if not zip_path.exists():
            raise ArchiveSecurityError(f"Zip file not found: {zip_path}")

        compressed_size = zip_path.stat().st_size
        max_compressed = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if compressed_size > max_compressed:
            raise ArchiveSecurityError(f"Archive exceeds maximum compressed size of {settings.MAX_UPLOAD_SIZE_MB}MB")

        if not zipfile.is_zipfile(zip_path):
            raise ArchiveSecurityError("Uploaded file is not a valid ZIP archive.")

        target_dir.mkdir(parents=True, exist_ok=True)
        resolved_target = target_dir.resolve()

        total_uncompressed_size = 0
        total_files = 0
        extracted_files = []
        max_uncompressed = settings.MAX_EXTRACTED_SIZE_MB * 1024 * 1024

        with zipfile.ZipFile(zip_path, 'r') as zf:
            file_list = zf.infolist()
            
            if len(file_list) > settings.MAX_ARCHIVE_FILES:
                raise ArchiveSecurityError(f"Archive contains {len(file_list)} files, exceeding limit of {settings.MAX_ARCHIVE_FILES}")

            for member in file_list:
                # Check for path traversal (e.g. ../../etc/passwd)
                member_name = member.filename
                if ".." in member_name or member_name.startswith("/") or member_name.startswith("\\"):
                    raise ArchiveSecurityError(f"Suspicious path detected in archive: {member_name}")

                # Accumulate uncompressed size
                total_uncompressed_size += member.file_size
                if total_uncompressed_size > max_uncompressed:
                    raise ArchiveSecurityError(
                        f"Archive uncompressed size exceeds limit of {settings.MAX_EXTRACTED_SIZE_MB}MB (potential ZIP bomb)."
                    )

                # Prevent symlinks abuse
                # Unix mode 0o120000 is symbolic link
                mode = member.external_attr >> 16
                if mode & 0o120000 == 0o120000:
                    continue  # Skip symlinks for safety

                dest_path = (target_dir / member_name).resolve()
                if not str(dest_path).startswith(str(resolved_target)):
                    raise ArchiveSecurityError(f"Path traversal attempt blocked: {member_name}")

                total_files += 1

            # Perform safe extraction
            for member in file_list:
                mode = member.external_attr >> 16
                if mode & 0o120000 == 0o120000:
                    continue

                zf.extract(member, target_dir)
                dest_path = (target_dir / member.filename).resolve()
                if dest_path.is_file():
                    extracted_files.append(str(dest_path.relative_to(resolved_target)))

        # Clean up nested single root folder if created by ZIP
        extracted_entries = [p for p in target_dir.iterdir() if p.name not in ["__MACOSX", ".DS_Store"]]
        if len(extracted_entries) == 1 and extracted_entries[0].is_dir():
            # Flatten one level
            single_dir = extracted_entries[0]
            for child in single_dir.iterdir():
                shutil.move(str(child), str(target_dir))
            try:
                single_dir.rmdir()
            except Exception:
                pass

        meta = {
            "compressed_size_bytes": compressed_size,
            "uncompressed_size_bytes": total_uncompressed_size,
            "total_files": len(extracted_files),
            "files": extracted_files[:100]
        }
        return True, "Extraction successful", meta
