import json
from pathlib import Path
from typing import Dict, Any, List

class ProjectIntelligenceService:
    @staticmethod
    def analyze_workspace(workspace_dir: Path) -> Dict[str, Any]:
        """
        Inspects directory structure, configuration files, and manifests to identify:
        - Primary language
        - Frameworks
        - Test and lint configurations
        - Dependency files
        - Potential security/hygiene risks
        """
        profile = {
            "detected_language": "Unknown",
            "detected_framework": "None",
            "dependency_files": [],
            "test_commands": [],
            "lint_commands": [],
            "file_count": 0,
            "total_size_bytes": 0,
            "risks_identified": [],
            "health_status": "healthy"
        }

        package_json_path = workspace_dir / "package.json"
        requirements_path = workspace_dir / "requirements.txt"
        pyproject_path = workspace_dir / "pyproject.toml"

        # Check Python
        if pyproject_path.exists() or requirements_path.exists() or any(workspace_dir.glob("*.py")):
            profile["detected_language"] = "Python"
            if requirements_path.exists():
                profile["dependency_files"].append("requirements.txt")
            if pyproject_path.exists():
                profile["dependency_files"].append("pyproject.toml")

            # Check test commands
            if (workspace_dir / "tests").is_dir() or any(workspace_dir.glob("test_*.py")):
                profile["test_commands"].append("pytest")
            
            # Framework detection
            frameworks = []
            req_content = ""
            if requirements_path.exists():
                req_content += requirements_path.read_text(encoding="utf-8", errors="ignore").lower()
            if pyproject_path.exists():
                req_content += pyproject_path.read_text(encoding="utf-8", errors="ignore").lower()

            if "fastapi" in req_content:
                frameworks.append("FastAPI")
            if "flask" in req_content:
                frameworks.append("Flask")
            if "django" in req_content:
                frameworks.append("Django")
            if frameworks:
                profile["detected_framework"] = ", ".join(frameworks)

        # Check Node.js / TypeScript
        if package_json_path.exists():
            profile["dependency_files"].append("package.json")
            try:
                pkg_data = json.loads(package_json_path.read_text(encoding="utf-8", errors="ignore"))
                scripts = pkg_data.get("scripts", {})
                if "test" in scripts:
                    profile["test_commands"].append("npm test")
                if "lint" in scripts:
                    profile["lint_commands"].append("npm run lint")

                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                if "typescript" in deps or (workspace_dir / "tsconfig.json").exists():
                    profile["detected_language"] = "TypeScript"
                elif profile["detected_language"] == "Unknown":
                    profile["detected_language"] = "JavaScript"

                js_frameworks = []
                if "react" in deps:
                    js_frameworks.append("React")
                if "next" in deps:
                    js_frameworks.append("Next.js")
                if "express" in deps:
                    js_frameworks.append("Express")
                if "vue" in deps:
                    js_frameworks.append("Vue")
                if js_frameworks:
                    profile["detected_framework"] = ", ".join(js_frameworks)
            except Exception:
                profile["risks_identified"].append("Failed to parse package.json syntax.")

        # Hygiene & Risk checks
        if not profile["test_commands"]:
            profile["risks_identified"].append("No automated test suite detected. Repairs cannot be automatically verified.")
            profile["health_status"] = "degraded"

        if (workspace_dir / ".env").exists():
            profile["risks_identified"].append("Unencrypted .env file found in project root.")
            profile["health_status"] = "degraded"

        return profile
