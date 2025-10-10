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
import ast
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from datetime import datetime


def extract_timestamp_and_message(line: str) -> Tuple[Optional[str], str]:
    """Extract timestamp and message from log line

    타임스탬프와 메시지를 로그 라인에서 추출합니다.

    Supports multiple timestamp formats:
    - [YYYY-MM-DD HH:MM:SS.mmm] message
    - [HH:MM:SS.mmm] message
    - YYYY-MM-DD HH:MM:SS message
    - Or just return the whole line as message if no timestamp found
    """

    # Pattern 1: [YYYY-MM-DD HH:MM:SS.mmm] format
    pattern1 = r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\]\s*(.*)$"
    match = re.match(pattern1, line.strip())
    if match:
        return match.group(1), match.group(2)

    # Pattern 2: [HH:MM:SS.mmm] format
    pattern2 = r"^\[(\d{2}:\d{2}:\d{2}\.\d{3})\]\s*(.*)$"
    match = re.match(pattern2, line.strip())
    if match:
        return match.group(1), match.group(2)

    # Pattern 3: YYYY-MM-DD HH:MM:SS format (no brackets)
    pattern3 = r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\s+(.*)$"
    match = re.match(pattern3, line.strip())
    if match:
        return match.group(1), match.group(2)

    # No timestamp found, return whole line as message
    return None, line.strip()


def extract_json_from_message(message: str) -> Tuple[bool, Optional[str], Any]:
    """Extract JSON from various message patterns

    다양한 메시지 패턴에서 JSON을 추출합니다.

    Supported patterns:
    1. Direct JSON: {"key": "value"}
    2. ServerClient Payload: [ServerClient] Payload: {"key": "value"}
    3. Module prefix: [Module] JSON content
    4. Simple prefix: Some text: {"key": "value"}
    5. Mixed content with JSON somewhere in the line

    Returns:
        Tuple of (found_json, json_text, parsed_json)
    """

    if not message:
        return False, None, {}

    # Pattern 1: Direct JSON (starts with { or [)
    message_stripped = message.strip()
    if message_stripped.startswith(("{", "[")):
        is_valid, parsed = is_valid_json(message_stripped)
        if is_valid:
            return True, message_stripped, parsed

    # Pattern 2: ServerClient Payload pattern
    # [ServerClient] Payload: {"key": "value"}
    payload_pattern = r"\[.*?\]\s+Payload:\s*(.+)$"
    match = re.search(payload_pattern, message)
    if match:
        json_candidate = match.group(1).strip()
        is_valid, parsed = is_valid_json(json_candidate)
        if is_valid:
            return True, json_candidate, parsed

    # Pattern 3: Module prefix pattern
    # [Module] {"key": "value"} or [Module] Some text {"key": "value"}
    module_pattern = r"\[.*?\]\s*(.*)$"
    match = re.search(module_pattern, message)
    if match:
        content = match.group(1).strip()
        # Try direct JSON first
        if content.startswith(("{", "[")):
            is_valid, parsed = is_valid_json(content)
            if is_valid:
                return True, content, parsed

        # Look for JSON in the content
        json_in_content = extract_json_from_text(content)
        if json_in_content[0]:
            return json_in_content

    # Pattern 4: Colon-separated prefix
    # "Some text: {"key": "value"}"
    colon_pattern = r"^[^{]*?:\s*(.+)$"
    match = re.search(colon_pattern, message)
    if match:
        json_candidate = match.group(1).strip()
        is_valid, parsed = is_valid_json(json_candidate)
        if is_valid:
            return True, json_candidate, parsed

    # Pattern 5: Find JSON anywhere in the message
    return extract_json_from_text(message)


def extract_json_from_text(text: str) -> Tuple[bool, Optional[str], Any]:
    """Find and extract JSON from anywhere in the text

    텍스트 내 어디든 JSON이 있으면 추출합니다.
    """

    # Look for JSON objects starting with {
    brace_start = text.find("{")
    if brace_start != -1:
        # Find matching closing brace
        brace_count = 0
        for i, char in enumerate(text[brace_start:], brace_start):
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    json_candidate = text[brace_start : i + 1]
                    is_valid, parsed = is_valid_json(json_candidate)
                    if is_valid:
                        return True, json_candidate, parsed
                    break

    # Look for JSON arrays starting with [
    bracket_start = text.find("[")
    if bracket_start != -1:
        bracket_count = 0
        for i, char in enumerate(text[bracket_start:], bracket_start):
            if char == "[":
                bracket_count += 1
            elif char == "]":
                bracket_count -= 1
                if bracket_count == 0:
                    json_candidate = text[bracket_start : i + 1]
                    is_valid, parsed = is_valid_json(json_candidate)
                    if is_valid:
                        return True, json_candidate, parsed
                    break

    return False, None, {}


def is_valid_json(text: str) -> Tuple[bool, Any]:
    """Check if text is valid JSON and return parsed object

    Args:
        text: Text to validate as JSON

    Returns:
        Tuple of (is_valid, parsed_json_or_empty_dict)

    텍스트가 유효한 JSON인지 확인하고 파싱된 객체를 반환합니다.
    """
    try:
        parsed = json.loads(text.strip())
        return True, parsed
    except (json.JSONDecodeError, ValueError):
        return False, {}


def extract_json_logs_from_file(
    input_file, output_file, include_metadata=False, verbose=False
):
    """Extract JSON logs from a file and save to NDJSON format."""
    stats = {"total_lines": 0, "json_lines": 0, "invalid_lines": 0, "empty_lines": 0}

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    with open(output_file, "w", encoding="utf-8") as out_f:
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            stats["total_lines"] += 1

            if not line:
                stats["empty_lines"] += 1
                i += 1
                continue

            # 타임스탬프 패턴 확인 (일반 JSON 로그)
            timestamp_match = re.match(
                r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\]", line
            )
            # ServerClient Payload 패턴 확인
            serverclient_match = re.match(
                r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\] \[ServerClient\] Payload:",
                line,
            )

            if timestamp_match or serverclient_match:
                if serverclient_match:
                    timestamp = serverclient_match.group(1)
                elif timestamp_match:
                    timestamp = timestamp_match.group(1)
                else:
                    # 이 경우는 발생하지 않아야 하지만 안전을 위해
                    stats["invalid_lines"] += 1
                    i += 1
                    continue

                if serverclient_match:
                    # ServerClient Payload 처리
                    # "Payload: " 이후의 내용부터 JSON 시작
                    payload_start = line.find("Payload: ") + len("Payload: ")
                    json_content = line[payload_start:]

                    # 다음 라인들을 수집하여 완전한 JSON 구성
                    j = i + 1
                    while j < len(lines):
                        next_line = lines[j].strip()
                        # 다음 타임스탬프 라인이 나오면 중단
                        if re.match(
                            r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\]",
                            next_line,
                        ):
                            break
                        json_content += next_line
                        j += 1

                    # JSON 유효성 검사 및 저장
                    try:
                        # ServerClient Payload는 Python 딕셔너리 형식이므로 ast.literal_eval 사용
                        parsed_json = ast.literal_eval(json_content)
                        stats["json_lines"] += 1

                        if include_metadata:
                            output_obj = {
                                "line_number": i + 1,
                                "timestamp": timestamp,
                                "source_type": "ServerClient_Payload",
                                "data": parsed_json,
                            }
                        else:
                            output_obj = parsed_json

                        out_f.write(json.dumps(output_obj, ensure_ascii=False) + "\n")

                        if verbose:
                            print(f"✓ ServerClient Payload extracted from line {i + 1}")
                    except (ValueError, SyntaxError) as e:
                        stats["invalid_lines"] += 1
                        if verbose:
                            print(
                                f"✗ Invalid ServerClient Payload at line {i + 1}: {e}"
                            )

                    i = j  # 다음 처리할 라인으로 이동

                else:
                    # 일반 JSON 로그 처리
                    # 첫 번째 '{' 찾기
                    json_start = line.find("{")
                    if json_start != -1:
                        json_content = line[json_start:]

                        # 다음 라인들을 수집하여 완전한 JSON 구성
                        j = i + 1
                        while j < len(lines):
                            next_line = lines[j].strip()
                            # 다음 타임스탬프 라인이 나오면 중단
                            if re.match(
                                r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\]",
                                next_line,
                            ):
                                break
                            json_content += next_line
                            j += 1

                        # JSON 유효성 검사 및 저장
                        try:
                            parsed_json = json.loads(json_content)
                            stats["json_lines"] += 1

                            if include_metadata:
                                output_obj = {
                                    "line_number": i + 1,
                                    "timestamp": timestamp,
                                    "source_type": "JSON_Log",
                                    "data": parsed_json,
                                }
                            else:
                                output_obj = parsed_json

                            out_f.write(
                                json.dumps(output_obj, ensure_ascii=False) + "\n"
                            )

                            if verbose:
                                print(f"✓ JSON extracted from line {i + 1}")
                        except json.JSONDecodeError as e:
                            stats["invalid_lines"] += 1
                            if verbose:
                                print(f"✗ Invalid JSON at line {i + 1}: {e}")

                        i = j  # 다음 처리할 라인으로 이동
                    else:
                        stats["invalid_lines"] += 1
                        if verbose:
                            print(f"✗ No JSON found at line {i + 1}")
                        i += 1
            else:
                stats["invalid_lines"] += 1
                if verbose:
                    print(f"✗ No timestamp found at line {i + 1}")
                i += 1

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
    input_file = args.input
    output_file = args.output

    # 입력 파일 존재 확인
    if not input_file or not output_file:
        print("❌ Error: Input and output file paths are required", file=sys.stderr)
        sys.exit(1)

    # 시작 메시지
    print("🚀 Starting JSON log extraction...")
    print(f"📁 Input:  {input_file}")
    print(f"📁 Output: {output_file}")

    if args.verbose:
        print("🔧 Verbose mode enabled")

    print("⏳ Processing...")

    # JSON 로그 추출 실행
    start_time = datetime.now()
    stats = extract_json_logs_from_file(
        input_file=input_file,
        output_file=output_file,
        verbose=args.verbose,
        include_metadata=not args.no_meta,
    )
    end_time = datetime.now()

    # 결과 요약 출력
    print_extraction_summary(stats, Path(input_file), Path(output_file))

    # 처리 시간 출력
    processing_time = (end_time - start_time).total_seconds()
    print(f"⏱️  Processing Time: {processing_time:.2f} seconds")

    # 성공/실패 판정
    if stats["json_lines"] > 0:
        print("🎉 Extraction completed successfully!")
        print(f"📝 {stats['json_lines']} JSON objects extracted to {output_file}")
        sys.exit(0)
    else:
        print("⚠️  No JSON logs found in input file")
        print("💡 Make sure the input file contains JSON-formatted console logs")
        sys.exit(1)


if __name__ == "__main__":
    main()
