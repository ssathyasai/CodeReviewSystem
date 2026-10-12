import os
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict

from backend.app.models.scan import LanguageStats

EXTENSION_LANGUAGE_MAP = {
    # Python
    ".py": "Python",
    ".pyw": "Python",
    ".ipynb": "Python (Notebook)",
    # JavaScript & TypeScript
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    # Java & JVM
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".scala": "Scala",
    # C / C++ / C#
    ".c": "C",
    ".h": "C/C++ Header",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++ Header",
    ".cs": "C#",
    # Go, PHP, Ruby, Swift
    ".go": "Go",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    # SQL & Database
    ".sql": "SQL",
    # Shell & Scripts
    ".sh": "Shell Script",
    ".bash": "Shell Script",
    ".zsh": "Shell Script",
    ".ps1": "PowerShell",
    # Web Markup & Styling
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "SASS",
    # Config / Manifests
    ".json": "JSON / Manifest",
    ".yaml": "YAML Config",
    ".yml": "YAML Config",
    ".toml": "TOML Config",
    ".xml": "XML Config",
}

IGNORED_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "vendor", "__pycache__",
    ".venv", "venv", "env", "dist", "build", "target", ".idea", ".vscode",
    ".next", ".nuxt", "coverage", ".pytest_cache"
}

class LanguageDetector:
    @classmethod
    def analyze_workspace(cls, workspace_path: Path) -> Tuple[List[LanguageStats], Dict[str, Any]]:
        """
        Inspects directory tree, counts lines of code, detects manifests,
        and computes percentage breakdown.
        """
        if not workspace_path.exists() or not workspace_path.is_dir():
            return [], {"total_files": 0, "total_lines": 0, "manifests": []}

        lang_files = defaultdict(int)
        lang_lines = defaultdict(int)
        detected_manifests = []
        unsupported_files = 0
        total_files = 0
        total_lines = 0

        # Scan for key manifests
        manifest_names = {
            "package.json": "npm/Node.js Manifest",
            "requirements.txt": "Python pip Requirements",
            "Pipfile": "Python Pipfile",
            "pyproject.toml": "Python PyProject",
            "pom.xml": "Maven Java Project",
            "build.gradle": "Gradle Java Project",
            "go.mod": "Go Modules",
            "composer.json": "PHP Composer",
            "Gemfile": "Ruby Gemfile",
            "Cargo.toml": "Rust Cargo",
            "Dockerfile": "Docker Container Spec",
            "docker-compose.yml": "Docker Compose Spec"
        }

        for root, dirs, files in os.walk(workspace_path):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

            for file in files:
                file_path = Path(root) / file
                
                # Check manifest
                if file in manifest_names:
                    detected_manifests.append({
                        "file": file,
                        "type": manifest_names[file],
                        "path": str(file_path.relative_to(workspace_path))
                    })

                ext = file_path.suffix.lower()
                lang = EXTENSION_LANGUAGE_MAP.get(ext)

                if not lang:
                    unsupported_files += 1
                    continue

                # Count lines
                line_count = 0
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        line_count = sum(1 for line in f if line.strip())
                except Exception:
                    line_count = 0

                lang_files[lang] += 1
                lang_lines[lang] += line_count
                total_files += 1
                total_lines += line_count

        stats_list: List[LanguageStats] = []
        for lang, count in lang_files.items():
            loc = lang_lines[lang]
            pct = round((loc / total_lines * 100), 1) if total_lines > 0 else round(100.0 / len(lang_files), 1)
            stats_list.append(LanguageStats(
                language=lang,
                files_count=count,
                lines_of_code=loc,
                percentage=pct
            ))

        stats_list.sort(key=lambda x: x.lines_of_code, reverse=True)

        metadata = {
            "total_analyzed_files": total_files,
            "total_lines_of_code": total_lines,
            "unsupported_files_count": unsupported_files,
            "manifests": detected_manifests,
            "primary_language": stats_list[0].language if stats_list else "Unknown"
        }

        return stats_list, metadata
