#!/usr/bin/env python3
"""
웹 빌드 유틸리티 모듈

Mustache 템플릿 기반 HTML 생성을 위한 공통 함수들을 제공합니다.
"""

import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    import pystache  # type: ignore
except ImportError:
    print("pystache가 설치되지 않았습니다. 다음 명령어로 설치하세요:")
    print("rye add pystache")
    exit(1)


def load_config(config_path: Path) -> Dict[str, Any]:
    """빌드 설정 파일을 로드합니다."""
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_config(defaults: Dict[str, Any], preset: Dict[str, Any]) -> Dict[str, Any]:
    """기본 설정과 프리셋을 병합합니다."""
    merged = defaults.copy()
    merged.update(preset)
    return merged


def build_html_from_mustache(
    template_path: Path, config: Dict[str, Any], output_path: Path
) -> None:
    """mustache 템플릿을 사용하여 HTML 파일을 생성합니다."""
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    renderer = pystache.Renderer()
    html_content = renderer.render(template, config)

    # 출력 디렉토리 생성
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"✅ HTML 파일 생성: {output_path}")


def build_html_with_preset(
    preset_name: str,
    output_path: Path,
    template_path: Path = Path("pyxel_web_lib/index.html.mustache"),
    config_path: Path = Path("pyxel_web_lib/build_config.json"),
) -> None:
    """프리셋을 사용하여 HTML을 생성합니다."""

    # 설정 로드
    try:
        config_data = load_config(config_path)
    except FileNotFoundError:
        print(f"❌ 설정 파일을 찾을 수 없습니다: {config_path}")
        raise
    except json.JSONDecodeError as e:
        print(f"❌ 설정 파일 파싱 오류: {e}")
        raise

    # 프리셋 확인
    if preset_name not in config_data["presets"]:
        available_presets = ", ".join(config_data["presets"].keys())
        raise ValueError(
            f"알 수 없는 프리셋: {preset_name}. 사용 가능한 프리셋: {available_presets}"
        )

    # 설정 병합
    merged_config = merge_config(
        config_data["defaults"], config_data["presets"][preset_name]
    )

    # HTML 빌드
    try:
        build_html_from_mustache(template_path, merged_config, output_path)
    except FileNotFoundError:
        print(f"❌ 템플릿 파일을 찾을 수 없습니다: {template_path}")
        raise

    print(f"🎉 빌드 완료: {preset_name} -> {output_path}")


def copy_assets(
    src_dir: Path, dest_dir: Path, exclude_patterns: Optional[List[str]] = None
) -> None:
    """에셋 파일들을 복사합니다."""
    if exclude_patterns is None:
        exclude_patterns = ["*.mustache", "*.json", "*.html", "__pycache__"]

    dest_dir.mkdir(parents=True, exist_ok=True)

    for item in src_dir.iterdir():
        if item.is_file():
            # 제외 패턴 확인
            skip = False
            for pattern in exclude_patterns:
                if item.match(pattern):
                    skip = True
                    break

            if not skip:
                shutil.copy2(item, dest_dir / item.name)
                print(f"📄 복사: {item.name}")
        elif item.is_dir() and item.name not in ["__pycache__"]:
            shutil.copytree(item, dest_dir / item.name, dirs_exist_ok=True)
            print(f"📁 디렉토리 복사: {item.name}")
