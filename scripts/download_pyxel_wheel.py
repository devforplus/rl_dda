#!/usr/bin/env python3

"""
Pyxel Wheel Download Script

This script downloads the latest or specified version of Pyxel wheel file
from PyPI or GitHub WASM directory and automatically updates the pyxel.js configuration.

---

Pyxel Wheel 다운로드 스크립트

PyPI 또는 GitHub WASM 디렉토리에서 최신 또는 지정된 버전의 Pyxel wheel 파일을 다운로드하고
pyxel.js 설정을 자동으로 업데이트합니다.
"""

import argparse
import json
import re
import requests
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def get_github_wasm_wheels() -> List[Tuple[str, str]]:
    """Get wheel files from GitHub WASM directory

    Returns:
        List of (filename, download_url) tuples

    ---

    GitHub WASM 디렉토리에서 wheel 파일들을 가져옵니다.

    Returns:
        (파일명, 다운로드_URL) 튜플들의 리스트
    """
    try:
        # GitHub API to get files in wasm directory
        # ---
        # GitHub API를 사용하여 wasm 디렉토리의 파일들을 가져옵니다.
        api_url = "https://api.github.com/repos/kitao/pyxel/contents/wasm"
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()

        files = response.json()
        wheel_files = []

        for file_info in files:
            if file_info["name"].endswith(".whl"):
                filename = file_info["name"]
                # Use raw.githubusercontent.com for direct download
                # ---
                # 직접 다운로드를 위해 raw.githubusercontent.com을 사용합니다.
                download_url = f"https://raw.githubusercontent.com/kitao/pyxel/main/wasm/{filename}"
                wheel_files.append((filename, download_url))

        return wheel_files
    except Exception as e:
        print(f"Error fetching GitHub WASM wheels: {e}")
        return []


def get_latest_github_wheel() -> Optional[Tuple[str, str]]:
    """Get the latest wheel file from GitHub WASM directory

    Returns:
        Tuple of (filename, download_url) or None

    ---

    GitHub WASM 디렉토리에서 최신 wheel 파일을 가져옵니다.

    Returns:
        (파일명, 다운로드_URL) 튜플 또는 None
    """
    wheels = get_github_wasm_wheels()
    if not wheels:
        return None

    # Sort by filename to get the latest version
    # ---
    # 파일명으로 정렬하여 최신 버전을 가져옵니다.
    wheels.sort(key=lambda x: x[0], reverse=True)
    return wheels[0]


def get_latest_pyxel_version() -> Optional[str]:
    """Get the latest Pyxel version from PyPI

    ---

    PyPI에서 최신 Pyxel 버전을 가져옵니다.
    """
    try:
        response = requests.get("https://pypi.org/pypi/pyxel/json", timeout=10)
        response.raise_for_status()
        data = response.json()
        return data["info"]["version"]
    except Exception as e:
        print(f"Error fetching latest version: {e}")
        return None


def get_available_versions() -> List[str]:
    """Get all available Pyxel versions from PyPI

    ---

    PyPI에서 사용 가능한 모든 Pyxel 버전을 가져옵니다.
    """
    try:
        response = requests.get("https://pypi.org/pypi/pyxel/json", timeout=10)
        response.raise_for_status()
        data = response.json()
        return list(data["releases"].keys())
    except Exception as e:
        print(f"Error fetching versions: {e}")
        return []


def find_wheel_urls(version: str) -> Dict[str, Tuple[str, str]]:
    """Find wheel download URLs for a specific version

    ---

    특정 버전의 wheel 다운로드 URL을 찾습니다.
    """
    try:
        response = requests.get(
            f"https://pypi.org/pypi/pyxel/{version}/json", timeout=10
        )
        response.raise_for_status()
        data = response.json()

        wheel_urls = {}
        for file_info in data["urls"]:
            if file_info["filename"].endswith(".whl"):
                filename = file_info["filename"]
                url = file_info["url"]

                # Prioritize WASM/emscripten builds
                # ---
                # WASM/emscripten 빌드를 우선시합니다.
                if "emscripten" in filename:
                    wheel_urls["emscripten"] = (filename, url)
                elif "wasm" in filename:
                    wheel_urls["wasm"] = (filename, url)
                elif "py3" in filename and "none" in filename and "any" in filename:
                    wheel_urls["universal"] = (filename, url)
                elif "manylinux" in filename:
                    wheel_urls["linux"] = (filename, url)

        return wheel_urls
    except Exception as e:
        print(f"Error fetching wheel URLs for version {version}: {e}")
        return {}


def download_wheel_file(filename: str, url: str, target_dir: Path) -> bool:
    """Download wheel file to target directory

    ---

    wheel 파일을 대상 디렉토리에 다운로드합니다.
    """
    try:
        print(f"Downloading {filename}...")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        target_file = target_dir / filename
        with open(target_file, "wb") as f:
            f.write(response.content)

        print(f"✅ Downloaded: {target_file}")
        return True
    except Exception as e:
        print(f"❌ Error downloading {filename}: {e}")
        return False


def download_with_pip(
    version: str, target_dir: Path, platform: Optional[str] = None
) -> Optional[str]:
    """Download wheel using pip as fallback method

    ---

    pip을 사용하여 wheel을 다운로드하는 fallback 방법입니다.
    """
    cmd = [
        "pip",
        "download",
        f"pyxel=={version}",
        "--no-deps",
        "--dest",
        str(target_dir),
    ]

    if platform:
        cmd.extend(["--platform", platform, "--only-binary=:all:"])

    try:
        print(f"Attempting pip download for pyxel=={version}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

        if result.returncode == 0:
            # Find downloaded file
            # ---
            # 다운로드된 파일을 찾습니다.
            for file in target_dir.glob("pyxel-*.whl"):
                if version in file.name:
                    print(f"✅ Downloaded via pip: {file}")
                    return file.name
        else:
            print(f"❌ pip download failed: {result.stderr}")

    except Exception as e:
        print(f"❌ pip download error: {e}")

    return None


def update_pyxel_js(wheel_filename: str, pyxel_js_path: Path) -> bool:
    """Update pyxel.js with new wheel filename

    ---

    새로운 wheel 파일명으로 pyxel.js를 업데이트합니다.
    """
    try:
        content = pyxel_js_path.read_text(encoding="utf-8")

        # Update PYXEL_WHEEL_PATH constant
        # ---
        # PYXEL_WHEEL_PATH 상수를 업데이트합니다.
        pattern = r'const PYXEL_WHEEL_PATH = ".*?";'
        replacement = f'const PYXEL_WHEEL_PATH = "{wheel_filename}";'

        updated_content = re.sub(pattern, replacement, content)

        if updated_content != content:
            pyxel_js_path.write_text(updated_content, encoding="utf-8")
            print(f"✅ Updated {pyxel_js_path} with wheel filename: {wheel_filename}")
            return True
        else:
            print(f"⚠️  No changes needed in {pyxel_js_path}")
            return True

    except Exception as e:
        print(f"❌ Error updating {pyxel_js_path}: {e}")
        return False


def clean_old_wheels(target_dir: Path, keep_filename: str) -> None:
    """Remove old wheel files except the one we want to keep

    ---

    보관할 파일을 제외한 기존 wheel 파일들을 제거합니다.
    """
    try:
        for wheel_file in target_dir.glob("pyxel-*.whl"):
            if wheel_file.name != keep_filename:
                wheel_file.unlink()
                print(f"🗑️  Removed old wheel: {wheel_file.name}")
    except Exception as e:
        print(f"⚠️  Warning: Could not clean old wheels: {e}")


def download_pyxel_wheel(
    version: Optional[str] = None,
    prefer_platform: str = "emscripten",
    update_js: bool = True,
    use_github: bool = True,
) -> Tuple[bool, Optional[str]]:
    """Main function to download Pyxel wheel

    Args:
        version: Specific version to download, or None for latest
        prefer_platform: Preferred platform (emscripten, wasm, universal, linux)
        update_js: Whether to update pyxel.js file
        use_github: Whether to try GitHub WASM directory first

    Returns:
        Tuple of (success, downloaded_filename)

    ---

    Pyxel wheel을 다운로드하는 메인 함수

    Args:
        version: 다운로드할 특정 버전, 또는 최신 버전의 경우 None
        prefer_platform: 선호 플랫폼 (emscripten, wasm, universal, linux)
        update_js: pyxel.js 파일 업데이트 여부
        use_github: GitHub WASM 디렉토리를 먼저 시도할지 여부

    Returns:
        (성공 여부, 다운로드된 파일명) 튜플
    """
    project_root = Path(__file__).parent.parent
    pyxel_web_lib = project_root / "pyxel_web_lib"
    pyxel_js_path = pyxel_web_lib / "pyxel.js"

    # Ensure pyxel_web_lib directory exists
    # ---
    # pyxel_web_lib 디렉토리가 존재하는지 확인합니다.
    pyxel_web_lib.mkdir(exist_ok=True)

    # Try GitHub WASM directory first if requested and no specific version
    # ---
    # 요청되고 특정 버전이 없는 경우 GitHub WASM 디렉토리를 먼저 시도합니다.
    if use_github and version is None:
        print("🎯 Trying GitHub WASM directory...")
        wheel_info = get_latest_github_wheel()
        if wheel_info:
            filename, url = wheel_info
            print(f"📦 Found GitHub wheel: {filename}")
            if download_wheel_file(filename, url, pyxel_web_lib):
                clean_old_wheels(pyxel_web_lib, filename)

                if update_js and update_pyxel_js(filename, pyxel_js_path):
                    print(
                        f"✅ Successfully downloaded and configured Pyxel from GitHub"
                    )
                    return True, filename
                elif not update_js:
                    print(f"✅ Successfully downloaded Pyxel from GitHub")
                    return True, filename
        else:
            print("⚠️  No wheels found in GitHub WASM directory, trying PyPI...")

    # Get target version for PyPI
    # ---
    # PyPI용 대상 버전을 가져옵니다.
    if version is None:
        version = get_latest_pyxel_version()
        if not version:
            print("❌ Could not determine latest version")
            return False, None
        print(f"🎯 Using latest PyPI version: {version}")
    else:
        print(f"🎯 Using specified version: {version}")

    # Try to download from PyPI directly
    # ---
    # PyPI에서 직접 다운로드를 시도합니다.
    wheel_urls = find_wheel_urls(version)

    if wheel_urls:
        # Priority order for platforms
        # ---
        # 플랫폼 우선순위
        platform_priority = [
            prefer_platform,
            "emscripten",
            "wasm",
            "universal",
            "linux",
        ]

        for platform in platform_priority:
            if platform in wheel_urls:
                filename, url = wheel_urls[platform]
                if download_wheel_file(filename, url, pyxel_web_lib):
                    clean_old_wheels(pyxel_web_lib, filename)

                    if update_js and update_pyxel_js(filename, pyxel_js_path):
                        print(
                            f"✅ Successfully downloaded and configured Pyxel {version}"
                        )
                        return True, filename
                    elif not update_js:
                        print(f"✅ Successfully downloaded Pyxel {version}")
                        return True, filename

    # Fallback to pip download
    # ---
    # pip 다운로드로 fallback합니다.
    print("🔄 Trying pip download as fallback...")

    # Try different platforms with pip
    # ---
    # pip으로 다른 플랫폼들을 시도합니다.
    platforms_to_try = [
        "emscripten_3_1_58_wasm32",
        None,
    ]  # None means no platform specification

    for platform in platforms_to_try:
        filename = download_with_pip(version, pyxel_web_lib, platform)
        if filename:
            clean_old_wheels(pyxel_web_lib, filename)

            if update_js and update_pyxel_js(filename, pyxel_js_path):
                print(f"✅ Successfully downloaded and configured Pyxel {version}")
                return True, filename
            elif not update_js:
                print(f"✅ Successfully downloaded Pyxel {version}")
                return True, filename

    print(f"❌ Failed to download Pyxel {version}")
    return False, None


def main():
    """Command line interface for the download script

    ---

    다운로드 스크립트의 명령줄 인터페이스
    """
    parser = argparse.ArgumentParser(
        description="Download Pyxel wheel files from GitHub WASM or PyPI and update configuration"
    )
    parser.add_argument(
        "--version", "-v", help="Specific Pyxel version to download (default: latest)"
    )
    parser.add_argument(
        "--platform",
        "-p",
        choices=["emscripten", "wasm", "universal", "linux"],
        default="emscripten",
        help="Preferred platform (default: emscripten)",
    )
    parser.add_argument(
        "--no-update-js", action="store_true", help="Don't update pyxel.js file"
    )
    parser.add_argument(
        "--no-github", action="store_true", help="Don't try GitHub WASM directory"
    )
    parser.add_argument(
        "--list-versions", action="store_true", help="List available versions and exit"
    )
    parser.add_argument(
        "--list-github", action="store_true", help="List GitHub WASM wheels and exit"
    )

    args = parser.parse_args()

    if args.list_versions:
        print("Available Pyxel versions:")
        versions = get_available_versions()
        if versions:
            for version in sorted(versions, reverse=True)[
                :20
            ]:  # Show latest 20 versions
                print(f"  {version}")
        else:
            print("❌ Could not fetch versions")
        return

    if args.list_github:
        print("Available GitHub WASM wheels:")
        wheels = get_github_wasm_wheels()
        if wheels:
            for filename, url in wheels:
                print(f"  {filename}")
        else:
            print("❌ Could not fetch GitHub wheels")
        return

    success, filename = download_pyxel_wheel(
        version=args.version,
        prefer_platform=args.platform,
        update_js=not args.no_update_js,
        use_github=not args.no_github,
    )

    if success:
        print(f"\n🎉 Download completed: {filename}")
        print("💡 Run 'python scripts/update_web_files.py' to sync to web directories")
    else:
        print("\n❌ Download failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
