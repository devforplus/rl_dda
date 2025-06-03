#!/usr/bin/env python3
"""
Log Separator Utility

Separates mixed log files into event logs and payload logs based on log patterns.
Supports dataclass-based log entry processing and structured output.

---

로그 분리 유틸리티

혼재된 로그 파일을 이벤트 로그와 payload 로그로 분리합니다.
dataclass 기반 로그 엔트리 처리와 구조화된 출력을 지원합니다.
"""

import json
import re
import ast
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import logging


@dataclass
class LogEntry:
    """Generic log entry dataclass

    ---

    일반적인 로그 엔트리 dataclass
    """

    timestamp: str
    raw_content: str
    log_type: str  # 'event', 'payload', 'server_client', 'unknown'
    source: Optional[str] = None
    data: Optional[Dict] = None


@dataclass
class EventLogEntry(LogEntry):
    """Event-specific log entry

    ---

    이벤트 전용 로그 엔트리
    """

    event_type: Optional[str] = None
    event_name: Optional[str] = None

    def __post_init__(self):
        self.log_type = "event"


@dataclass
class PayloadLogEntry(LogEntry):
    """Payload-specific log entry

    ---

    Payload 전용 로그 엔트리
    """

    payload_size: Optional[int] = None
    payload_keys: Optional[List[str]] = None

    def __post_init__(self):
        self.log_type = "payload"


@dataclass
class ServerClientLogEntry(LogEntry):
    """ServerClient-specific log entry

    ---

    ServerClient 전용 로그 엔트리
    """

    action: Optional[str] = None  # 'sending', 'entry_keys', 'payload', etc.

    def __post_init__(self):
        self.log_type = "server_client"


class LogPatternMatcher:
    """Pattern matcher for different log types

    ---

    다양한 로그 타입에 대한 패턴 매처
    """

    def __init__(self):
        # Timestamp pattern: [2025-06-02 19:00:50.682]
        self.timestamp_pattern = re.compile(
            r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\]"
        )

        # ServerClient patterns
        self.server_client_pattern = re.compile(r"^\[.*\] \[ServerClient\] (.+)$")

        # Payload pattern: [ServerClient] Payload: {'key': value, ...}
        self.payload_pattern = re.compile(
            r"^\[.*\] \[ServerClient\] Payload: (\{.+\})$"
        )

        # Entry keys pattern: [ServerClient] Entry keys: [...]
        self.entry_keys_pattern = re.compile(
            r"^\[.*\] \[ServerClient\] Entry keys: (\[.+\])$"
        )

        # JSON event pattern: {"type": "event", ...}
        self.json_event_pattern = re.compile(r'^\[.*\] (\{"type":\s*"event".+\})$')

        # JSON entity pattern: {"type": "entity", ...}
        self.json_entity_pattern = re.compile(r'^\[.*\] (\{"type":\s*"entity".+\})$')

        # General JSON pattern: starts with {"
        self.json_pattern = re.compile(r"^\[.*\] (\{.+\})$")

    def extract_timestamp(self, line: str) -> Optional[str]:
        """Extract timestamp from log line

        ---

        로그 라인에서 타임스탬프 추출
        """
        match = self.timestamp_pattern.match(line)
        return match.group(1) if match else None

    def classify_log_line(self, line: str) -> Tuple[str, Optional[Dict]]:
        """Classify log line and extract relevant data

        Returns:
            Tuple of (log_type, extracted_data)

        ---

        로그 라인을 분류하고 관련 데이터 추출

        반환값:
            (log_type, extracted_data) 튜플
        """
        line = line.strip()

        # Check for payload data first: [ServerClient] Payload: {'key': value, ...}
        payload_match = self.payload_pattern.match(line)
        if payload_match:
            try:
                # Use ast.literal_eval for Python dictionary parsing
                payload_data = ast.literal_eval(payload_match.group(1))
                payload_size = len(payload_match.group(1))
                payload_keys = (
                    list(payload_data.keys()) if isinstance(payload_data, dict) else []
                )

                return "payload", {
                    "payload_data": payload_data,
                    "payload_size": payload_size,
                    "payload_keys": payload_keys,
                    "content_type": "python_dict",
                }
            except (ValueError, SyntaxError) as e:
                return "payload", {
                    "payload_data": payload_match.group(1),
                    "error": str(e),
                    "content_type": "raw_string",
                }

        # Check for entry keys: [ServerClient] Entry keys: [...]
        entry_keys_match = self.entry_keys_pattern.match(line)
        if entry_keys_match:
            try:
                entry_keys = ast.literal_eval(entry_keys_match.group(1))
                return "server_client", {
                    "entry_keys": entry_keys,
                    "content_type": "entry_keys",
                }
            except (ValueError, SyntaxError):
                return "server_client", {
                    "entry_keys": entry_keys_match.group(1),
                    "content_type": "raw_string",
                }

        # Check for general JSON data first, then classify by type
        json_match = self.json_pattern.match(line)
        if json_match:
            try:
                json_data = json.loads(json_match.group(1))
                data_type = json_data.get("type")

                # Both "event" and "entity" types should be classified as events
                if data_type in ["event", "entity"]:
                    event_name = json_data.get(
                        "event", json_data.get("event_name", json_data.get("name"))
                    )

                    return "event", {
                        "json_data": json_data,
                        "event_type": data_type,
                        "event_name": event_name,
                    }
                else:
                    # Other JSON data types
                    return "json", {"json_data": json_data, "data_type": data_type}
            except json.JSONDecodeError:
                return "unknown", {"raw_data": json_match.group(1)}

        # Check for general ServerClient messages
        server_client_match = self.server_client_pattern.match(line)
        if server_client_match:
            return "server_client", {
                "message": server_client_match.group(1),
                "content_type": "general",
            }

        return "unknown", None


class LogSeparator:
    """Main log separation utility

    ---

    메인 로그 분리 유틸리티
    """

    def __init__(self, output_dir: Optional[str] = None):
        self.matcher = LogPatternMatcher()
        self.output_dir = (
            Path(output_dir) if output_dir else Path("data/separated_logs")
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Statistics
        self.stats = {
            "total_lines": 0,
            "event_logs": 0,
            "payload_logs": 0,
            "server_client_logs": 0,
            "unknown_logs": 0,
        }

    def separate_log_file(self, input_file: Union[str, Path]) -> Dict[str, str]:
        """Separate a log file into different categories

        Args:
            input_file: Path to input log file

        Returns:
            Dictionary with output file paths

        ---

        로그 파일을 다양한 카테고리로 분리

        Args:
            input_file: 입력 로그 파일 경로

        Returns:
            출력 파일 경로 딕셔너리
        """
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")

        # Prepare output files
        base_name = input_path.stem
        output_files = {
            "event": self.output_dir / f"{base_name}_events.log",
            "payload": self.output_dir / f"{base_name}_payloads.log",
            "server_client": self.output_dir / f"{base_name}_server_client.log",
            "unknown": self.output_dir / f"{base_name}_unknown.log",
            "event_json": self.output_dir / f"{base_name}_events.json",
            "payload_json": self.output_dir / f"{base_name}_payloads.json",
        }

        # Storage for structured data
        event_entries = []
        payload_entries = []

        # Open all output files
        with open(output_files["event"], "w", encoding="utf-8") as event_file, open(
            output_files["payload"], "w", encoding="utf-8"
        ) as payload_file, open(
            output_files["server_client"], "w", encoding="utf-8"
        ) as server_client_file, open(
            output_files["unknown"], "w", encoding="utf-8"
        ) as unknown_file:
            # Process input file
            with open(input_path, "r", encoding="utf-8") as infile:
                for line_num, line in enumerate(infile, 1):
                    self.stats["total_lines"] += 1

                    # Extract timestamp
                    timestamp = self.matcher.extract_timestamp(line)

                    # Classify line
                    log_type, extracted_data = self.matcher.classify_log_line(line)

                    # Create appropriate log entry
                    log_entry = self._create_log_entry(
                        timestamp or f"line_{line_num}",
                        line.strip(),
                        log_type,
                        extracted_data,
                    )

                    # Write to appropriate files
                    if log_type == "event":
                        event_file.write(line)
                        event_entries.append(log_entry)
                        self.stats["event_logs"] += 1

                    elif log_type == "payload":
                        payload_file.write(line)
                        payload_entries.append(log_entry)
                        self.stats["payload_logs"] += 1

                    elif log_type == "server_client":
                        server_client_file.write(line)
                        self.stats["server_client_logs"] += 1

                    else:
                        unknown_file.write(line)
                        self.stats["unknown_logs"] += 1

        # Save structured JSON data
        self._save_json_data(output_files["event_json"], event_entries)
        self._save_json_data(output_files["payload_json"], payload_entries)

        # Save statistics
        self._save_statistics(base_name)

        return {k: str(v) for k, v in output_files.items()}

    def _create_log_entry(
        self,
        timestamp: str,
        raw_content: str,
        log_type: str,
        extracted_data: Optional[Dict],
    ) -> LogEntry:
        """Create appropriate log entry dataclass instance

        ---

        적절한 로그 엔트리 dataclass 인스턴스 생성
        """
        if log_type == "event":
            return EventLogEntry(
                timestamp=timestamp,
                raw_content=raw_content,
                log_type=log_type,
                data=extracted_data.get("json_data") if extracted_data else None,
                event_type=extracted_data.get("event_type") if extracted_data else None,
                event_name=extracted_data.get("event_name") if extracted_data else None,
            )

        elif log_type == "payload":
            return PayloadLogEntry(
                timestamp=timestamp,
                raw_content=raw_content,
                log_type=log_type,
                data=extracted_data.get("payload_data") if extracted_data else None,
                payload_size=extracted_data.get("payload_size")
                if extracted_data
                else None,
                payload_keys=extracted_data.get("payload_keys")
                if extracted_data
                else None,
            )

        elif log_type == "server_client":
            return ServerClientLogEntry(
                timestamp=timestamp,
                raw_content=raw_content,
                log_type=log_type,
                action=extracted_data.get("action") if extracted_data else None,
            )

        elif log_type == "json_data":
            # Treat other JSON data as generic log entry
            return LogEntry(
                timestamp=timestamp,
                raw_content=raw_content,
                log_type=log_type,
                data=extracted_data.get("json_data") if extracted_data else None,
            )

        else:
            return LogEntry(
                timestamp=timestamp, raw_content=raw_content, log_type=log_type
            )

    def _save_json_data(self, output_file: Path, entries: List[LogEntry]) -> None:
        """Save log entries as structured JSON

        ---

        로그 엔트리를 구조화된 JSON으로 저장
        """
        from dataclasses import asdict

        json_data = []
        for entry in entries:
            try:
                entry_dict = asdict(entry)
                json_data.append(entry_dict)
            except Exception as e:
                logging.warning(f"Failed to convert log entry to dict: {e}")

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

    def _save_statistics(self, base_name: str) -> None:
        """Save separation statistics

        ---

        분리 통계 저장
        """
        stats_file = self.output_dir / f"{base_name}_separation_stats.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)

    def get_statistics(self) -> Dict[str, int]:
        """Get current separation statistics

        ---

        현재 분리 통계 반환
        """
        return self.stats.copy()


def separate_logs(input_file: str, output_dir: Optional[str] = None) -> Dict[str, str]:
    """Convenience function to separate logs

    Args:
        input_file: Path to input log file
        output_dir: Output directory (optional)

    Returns:
        Dictionary with output file paths

    ---

    로그 분리를 위한 편의 함수

    Args:
        input_file: 입력 로그 파일 경로
        output_dir: 출력 디렉토리 (선택사항)

    Returns:
        출력 파일 경로 딕셔너리
    """
    separator = LogSeparator(output_dir)
    return separator.separate_log_file(input_file)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Separate mixed log files into categories"
    )
    parser.add_argument("input_file", help="Input log file path")
    parser.add_argument("--output-dir", "-o", help="Output directory")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    try:
        result = separate_logs(args.input_file, args.output_dir)
        print("✅ Log separation completed!")
        print("\n📁 Output files:")
        for category, filepath in result.items():
            print(f"  {category}: {filepath}")

        # Show statistics
        separator = LogSeparator(args.output_dir)
        separator.separate_log_file(args.input_file)  # This populates stats
        stats = separator.get_statistics()
        print(f"\n📊 Statistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)
