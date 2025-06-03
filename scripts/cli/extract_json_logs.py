#!/usr/bin/env python3
"""
JSON Log Extractor: Extract JSON-formatted logs from Simple Pyxel Collector output

🎯 Purpose (목적)
=================
Simple Pyxel Collector로 수집한 콘솔 로그 파일에서 JSON 형태의 이벤트/엔티티 로그만
추출하여 NDJSON (Newline Delimited JSON) 형태로 저장하는 도구입니다.

🔧 Features (기능)
==================
- **Log Parsing**: 타임스탬프가 포함된 로그 라인에서 JSON 데이터만 추출
- **JSON Validation**: 유효한 JSON 형태인지 검증 후 추출
- **NDJSON Output**: 각 JSON 객체를 한 라인씩 저장하는 NDJSON 형태로 출력
- **Statistics**: 추출된 JSON 객체 수와 전체 라인 수 통계 제공
- **Error Handling**: 잘못된 JSON이나 파일 오류 시 안전한 처리

📊 Input Format (입력 형식)
===========================
Simple Pyxel Collector의 로그 파일 형식:
```
[2025-01-27 12:34:56.789] 일반 텍스트 로그
[2025-01-27 12:34:57.123] {"type": "entity", "data": {...}}
[2025-01-27 12:34:57.456] {"event": "frame_data", "player": {...}}
```

📤 Output Format (출력 형식)
============================
NDJSON 형식:
```
{"type": "entity", "data": {...}}
{"event": "frame_data", "player": {...}}
```

🚀 Usage (사용법)
=================
```bash
python extract_json_logs.py --input events_info.log --output game_events.ndjson
python extract_json_logs.py -i logs/events_log.log -o extracted/entities.ndjson --verbose
```

---

Extract JSON-formatted event/entity logs from Simple Pyxel Collector output
Simple Pyxel Collector 출력에서 JSON 형태의 이벤트/엔티티 로그 추출
"""

import json
import re
import argparse
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime


def extract_timestamp_and_message(line: str) -> Tuple[str, str]:
    """Extract timestamp and message from log line

    Args:
        line: Log line with format '[YYYY-MM-DD HH:MM:SS.mmm] message'

    Returns:
        Tuple of (timestamp, message)

    ---

    로그 라인에서 타임스탬프와 메시지를 분리하여 추출합니다.
    """
    # 타임스탬프 패턴: [YYYY-MM-DD HH:MM:SS.mmm] 또는 [YYYY-MM-DD HH:MM:SS]
    timestamp_pattern = (
        r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:\.\d{3})?)\]\s*(.*)$"
    )
    match = re.match(timestamp_pattern, line)

    if match:
        return match.group(1), match.group(2)
    else:
        # 타임스탬프가 없는 경우 전체를 메시지로 처리
        return "", line.strip()


def is_valid_json(text: str) -> Tuple[bool, Dict[str, Any]]:
    """Check if text is valid JSON and return parsed object

    Args:
        text: Text to validate as JSON

    Returns:
        Tuple of (is_valid, parsed_json_or_empty_dict)

    ---

    텍스트가 유효한 JSON인지 확인하고 파싱된 객체를 반환합니다.
    """
    try:
        parsed = json.loads(text.strip())
        return True, parsed
    except (json.JSONDecodeError, ValueError):
        return False, {}


def extract_json_logs_from_file(
    input_file: Path, output_file: Path, verbose: bool = False
) -> Dict[str, int]:
    """Extract JSON logs from input file and save as NDJSON

    Args:
        input_file: Path to input log file
        output_file: Path to output NDJSON file
        verbose: Enable verbose logging

    Returns:
        Dictionary with extraction statistics

    ---

    입력 로그 파일에서 JSON 로그를 추출하여 NDJSON으로 저장합니다.
    """
    stats = {"total_lines": 0, "json_lines": 0, "invalid_lines": 0, "empty_lines": 0}

    extracted_jsons: List[Dict[str, Any]] = []

    try:
        with open(input_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                stats["total_lines"] += 1
                line = line.strip()

                # 빈 라인 건너뛰기
                if not line or line.startswith("#"):
                    stats["empty_lines"] += 1
                    continue

                # 타임스탬프와 메시지 분리
                timestamp, message = extract_timestamp_and_message(line)

                if not message:
                    stats["empty_lines"] += 1
                    continue

                # JSON 유효성 검사
                is_json, parsed_json = is_valid_json(message)

                if is_json:
                    # 메타데이터 추가 (선택사항)
                    json_with_meta = {
                        "extracted_timestamp": timestamp if timestamp else None,
                        "line_number": line_num,
                        **parsed_json,
                    }

                    extracted_jsons.append(json_with_meta)
                    stats["json_lines"] += 1

                    if verbose:
                        print(
                            f"✓ Line {line_num}: JSON extracted ({len(str(parsed_json))} chars)"
                        )

                else:
                    stats["invalid_lines"] += 1
                    if verbose:
                        print(f"- Line {line_num}: Not JSON - {message[:50]}...")

    except FileNotFoundError:
        print(f"❌ Error: Input file not found: {input_file}", file=sys.stderr)
        return stats
    except Exception as e:
        print(f"❌ Error reading input file: {e}", file=sys.stderr)
        return stats

    # NDJSON 파일로 저장
    try:
        # 출력 디렉토리 생성
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            for json_obj in extracted_jsons:
                # 메타데이터 제거하고 원본 JSON만 저장하는 옵션
                # original_json = {k: v for k, v in json_obj.items()
                #                  if k not in ['extracted_timestamp', 'line_number']}
                # f.write(json.dumps(original_json, ensure_ascii=False) + '\n')

                # 메타데이터 포함해서 저장
                f.write(json.dumps(json_obj, ensure_ascii=False) + "\n")

        print(f"✅ NDJSON file saved: {output_file}")

    except Exception as e:
        print(f"❌ Error writing output file: {e}", file=sys.stderr)
        return stats

    return stats


def print_extraction_summary(
    stats: Dict[str, int], input_file: Path, output_file: Path
):
    """Print extraction summary statistics

    Args:
        stats: Extraction statistics dictionary
        input_file: Input file path
        output_file: Output file path

    ---

    추출 결과 요약 통계를 출력합니다.
    """
    print("\n" + "=" * 60)
    print("📊 JSON LOG EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"📁 Input File:  {input_file}")
    print(f"📁 Output File: {output_file}")
    print(f"📊 Total Lines: {stats['total_lines']:,}")
    print(f"✅ JSON Lines:  {stats['json_lines']:,}")
    print(f"❌ Invalid:     {stats['invalid_lines']:,}")
    print(f"⭕ Empty/Skip:  {stats['empty_lines']:,}")

    if stats["total_lines"] > 0:
        json_percentage = (stats["json_lines"] / stats["total_lines"]) * 100
        print(f"📈 JSON Ratio:  {json_percentage:.1f}%")

    if output_file.exists():
        file_size = output_file.stat().st_size
        print(f"💾 Output Size: {file_size:,} bytes")

    print("=" * 60)


def main():
    """Main function for CLI interface

    ---

    CLI 인터페이스를 위한 메인 함수입니다.
    """
    parser = argparse.ArgumentParser(
        description="Extract JSON logs from Simple Pyxel Collector output",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_json_logs.py -i events_info.log -o game_events.ndjson
  python extract_json_logs.py --input data/default/events_log.log --output extracted/entities.ndjson --verbose
  python extract_json_logs.py -i logs/events_info.log -o output.ndjson -v

Supported input formats:
  - Simple Pyxel Collector log files (events_*.log)
  - Any text file with timestamped JSON lines
  - Format: [YYYY-MM-DD HH:MM:SS.mmm] {"json": "data"}
        """,
    )

    parser.add_argument(
        "-i",
        "--input",
        type=str,
        required=True,
        help="Input log file path from Simple Pyxel Collector",
    )

    parser.add_argument(
        "-o", "--output", type=str, required=True, help="Output NDJSON file path"
    )

    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    parser.add_argument(
        "--no-meta",
        action="store_true",
        help="Don't include extraction metadata in output JSON",
    )

    args = parser.parse_args()

    # 파일 경로 처리
    input_file = Path(args.input)
    output_file = Path(args.output)

    # 입력 파일 존재 확인
    if not input_file.exists():
        print(f"❌ Error: Input file does not exist: {input_file}", file=sys.stderr)
        sys.exit(1)

    if not input_file.is_file():
        print(f"❌ Error: Input path is not a file: {input_file}", file=sys.stderr)
        sys.exit(1)

    # 시작 메시지
    print(f"🚀 Starting JSON log extraction...")
    print(f"📁 Input:  {input_file}")
    print(f"📁 Output: {output_file}")

    if args.verbose:
        print(f"🔧 Verbose mode enabled")

    print(f"⏳ Processing...")

    # JSON 로그 추출 실행
    start_time = datetime.now()
    stats = extract_json_logs_from_file(
        input_file=input_file, output_file=output_file, verbose=args.verbose
    )
    end_time = datetime.now()

    # 결과 요약 출력
    print_extraction_summary(stats, input_file, output_file)

    # 처리 시간 출력
    processing_time = (end_time - start_time).total_seconds()
    print(f"⏱️  Processing Time: {processing_time:.2f} seconds")

    # 성공/실패 판정
    if stats["json_lines"] > 0:
        print(f"🎉 Extraction completed successfully!")
        print(f"📝 {stats['json_lines']} JSON objects extracted to {output_file}")
        sys.exit(0)
    else:
        print(f"⚠️  No JSON logs found in input file")
        print(f"💡 Make sure the input file contains JSON-formatted console logs")
        sys.exit(1)


if __name__ == "__main__":
    main()
