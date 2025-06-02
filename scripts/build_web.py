#!/usr/bin/env python3
"""
Pyxel 웹 애플리케이션 빌드 스크립트

mustache 템플릿을 사용하여 다양한 설정으로 HTML 파일을 생성합니다.
"""

import json
import shutil
import argparse
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


def build_html(template_path: Path, config: Dict[str, Any], output_path: Path) -> None:
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


def copy_assets(
    src_dir: Path, dest_dir: Path, exclude_patterns: Optional[List[str]] = None
) -> None:
    """에셋 파일들을 복사합니다."""
    if exclude_patterns is None:
        exclude_patterns = ["*.mustache", "*.json", "__pycache__"]

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


def main():
    parser = argparse.ArgumentParser(description="Pyxel 웹 앱 빌드")
    parser.add_argument(
        "preset", help="사용할 프리셋 (manual_game, agent_game, development)"
    )
    parser.add_argument("output_dir", help="출력 디렉토리")
    parser.add_argument(
        "--template",
        default="pyxel_web_lib/index.html.mustache",
        help="템플릿 파일 경로",
    )
    parser.add_argument(
        "--config", default="pyxel_web_lib/build_config.json", help="설정 파일 경로"
    )
    parser.add_argument(
        "--copy-assets", action="store_true", help="에셋 파일들을 출력 디렉토리로 복사"
    )

    args = parser.parse_args()

    # 경로 설정
    template_path = Path(args.template)
    config_path = Path(args.config)
    output_dir = Path(args.output_dir)

    # 설정 로드
    try:
        config_data = load_config(config_path)
    except FileNotFoundError:
        print(f"❌ 설정 파일을 찾을 수 없습니다: {config_path}")
        return 1
    except json.JSONDecodeError as e:
        print(f"❌ 설정 파일 파싱 오류: {e}")
        return 1

    # 프리셋 확인
    if args.preset not in config_data["presets"]:
        print(f"❌ 알 수 없는 프리셋: {args.preset}")
        print(f"사용 가능한 프리셋: {', '.join(config_data['presets'].keys())}")
        return 1

    # 설정 병합
    merged_config = merge_config(
        config_data["defaults"], config_data["presets"][args.preset]
    )

    # HTML 빌드
    output_html = output_dir / "index.html"
    try:
        build_html(template_path, merged_config, output_html)
    except FileNotFoundError:
        print(f"❌ 템플릿 파일을 찾을 수 없습니다: {template_path}")
        return 1

    # 에셋 복사
    if args.copy_assets:
        src_dir = template_path.parent
        copy_assets(src_dir, output_dir)

    print(f"🎉 빌드 완료: {args.preset} -> {output_dir}")
    return 0


if __name__ == "__main__":
    exit(main())
