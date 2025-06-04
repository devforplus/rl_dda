#!/usr/bin/env python3
"""
YOLO Dataset Creator

Extracts images and YOLO labels from payload logs to create training datasets.
Automatically splits data into train/validation/test sets.

---

YOLO 데이터셋 생성기

payload 로그에서 이미지와 YOLO 라벨을 추출하여 학습용 데이터셋을 생성합니다.
자동으로 train/validation/test 세트로 데이터를 분할합니다.
"""

import json
import re
import ast
import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import random
import logging
from datetime import datetime


@dataclass
class YOLOSample:
    """YOLO training sample dataclass

    ---

    YOLO 학습 샘플 dataclass
    """

    timestamp: str
    image_data: bytes  # PNG image data
    image_shape: Tuple[int, int, int]  # (height, width, channels)
    yolo_labels: List[str]  # YOLO format labels
    filename_base: str  # Base filename without extension


@dataclass
class DatasetSplit:
    """Dataset split configuration

    ---

    데이터셋 분할 설정
    """

    train_ratio: float = 0.7
    val_ratio: float = 0.2
    test_ratio: float = 0.1

    def __post_init__(self):
        total = self.train_ratio + self.val_ratio + self.test_ratio
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Split ratios must sum to 1.0, got {total}")


class PayloadLogParser:
    """Parser for payload log files

    ---

    payload 로그 파일 파서
    """

    def __init__(self):
        # Pattern to match payload lines
        self.payload_pattern = re.compile(
            r"^\[([^\]]+)\] \[ServerClient\] Payload: (\{.+\})$"
        )

    def parse_log_file(self, log_file: Path) -> List[YOLOSample]:
        """Parse payload log file and extract YOLO samples

        Args:
            log_file: Path to payload log file

        Returns:
            List of YOLOSample objects

        ---

        payload 로그 파일을 파싱하여 YOLO 샘플 추출

        Args:
            log_file: payload 로그 파일 경로

        Returns:
            YOLOSample 객체 리스트
        """
        samples = []

        with open(log_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                match = self.payload_pattern.match(line)
                if match:
                    timestamp = match.group(1)
                    payload_str = match.group(2)

                    try:
                        # Parse Python dictionary
                        payload_data = ast.literal_eval(payload_str)

                        # Extract required fields
                        if self._validate_payload(payload_data):
                            sample = self._create_yolo_sample(
                                timestamp, payload_data, line_num
                            )
                            samples.append(sample)

                    except (ValueError, SyntaxError) as e:
                        logging.warning(
                            f"Failed to parse payload at line {line_num}: {e}"
                        )
                        continue

        logging.info(f"Extracted {len(samples)} valid YOLO samples")
        return samples

    def _validate_payload(self, payload: Dict) -> bool:
        """Validate payload contains required fields for YOLO dataset

        ---

        YOLO 데이터셋에 필요한 필드가 payload에 있는지 검증
        """
        required_fields = [
            "timestamp",
            "image_original_shape",
            "image_png_base64",
            "yolo_labels",
        ]

        for field in required_fields:
            if field not in payload:
                return False

        # Check yolo_labels format
        yolo_labels = payload["yolo_labels"]
        if not isinstance(yolo_labels, list) or len(yolo_labels) == 0:
            return False

        # First element should be header (accept both "class_id" and "entity_num" formats)
        header = yolo_labels[0]
        if not (header.startswith("class_id") or header.startswith("entity_num")):
            return False

        return True

    def _create_yolo_sample(
        self, timestamp: str, payload: Dict, line_num: int
    ) -> YOLOSample:
        """Create YOLOSample from payload data

        ---

        payload 데이터로부터 YOLOSample 생성
        """
        # Decode base64 image
        image_base64 = payload["image_png_base64"]
        image_data = base64.b64decode(image_base64)

        # Extract image shape
        image_shape = tuple(payload["image_original_shape"])

        # Process YOLO labels (skip header)
        yolo_labels = payload["yolo_labels"][1:]  # Skip header line

        # Generate filename base
        timestamp_clean = timestamp.replace(":", "-").replace(".", "-")
        filename_base = f"sample_{timestamp_clean}_{line_num}"

        return YOLOSample(
            timestamp=timestamp,
            image_data=image_data,
            image_shape=image_shape,
            yolo_labels=yolo_labels,
            filename_base=filename_base,
        )


class YOLODatasetCreator:
    """YOLO dataset creator with train/val/test splitting

    ---

    train/val/test 분할 기능이 있는 YOLO 데이터셋 생성기
    """

    def __init__(self, output_dir: Path, split_config: Optional[DatasetSplit] = None):
        self.output_dir = Path(output_dir)
        self.split_config = split_config or DatasetSplit()
        self.parser = PayloadLogParser()

        # Create directory structure
        self._create_directory_structure()

    def _create_directory_structure(self):
        """Create YOLO dataset directory structure

        ---

        YOLO 데이터셋 디렉토리 구조 생성
        """
        splits = ["train", "val", "test"]

        for split in splits:
            (self.output_dir / split / "images").mkdir(parents=True, exist_ok=True)
            (self.output_dir / split / "labels").mkdir(parents=True, exist_ok=True)

    def create_dataset(
        self, payload_log_file: Path, shuffle: bool = True
    ) -> Dict[str, int]:
        """Create YOLO dataset from payload log file

        Args:
            payload_log_file: Path to payload log file
            shuffle: Whether to shuffle samples before splitting

        Returns:
            Dictionary with count of samples per split

        ---

        payload 로그 파일로부터 YOLO 데이터셋 생성

        Args:
            payload_log_file: payload 로그 파일 경로
            shuffle: 분할 전 샘플 셔플 여부

        Returns:
            분할별 샘플 수 딕셔너리
        """
        # Parse payload log
        logging.info(f"Parsing payload log: {payload_log_file}")
        samples = self.parser.parse_log_file(payload_log_file)

        if not samples:
            raise ValueError("No valid samples found in payload log")

        # Analyze class information from samples
        class_info = self._analyze_classes(samples)
        logging.info(
            f"Found {class_info['num_classes']} classes: {class_info['class_names']}"
        )

        # Shuffle samples if requested
        if shuffle:
            random.shuffle(samples)
            logging.info("Shuffled samples for random distribution")

        # Split samples
        splits = self._split_samples(samples)

        # Save samples to appropriate directories
        counts = {}
        for split_name, split_samples in splits.items():
            count = self._save_split_samples(split_name, split_samples)
            counts[split_name] = count
            logging.info(f"Saved {count} samples to {split_name} split")

        # Create dataset configuration files with actual class info
        self._create_dataset_config(counts, class_info)

        return counts

    def _analyze_classes(self, samples: List[YOLOSample]) -> Dict:
        """Analyze class information from YOLO samples

        ---

        YOLO 샘플에서 클래스 정보 분석
        """
        class_ids = set()
        class_counts = {}

        for sample in samples:
            for label in sample.yolo_labels:
                if label.strip():  # Skip empty labels
                    parts = label.strip().split()
                    if len(parts) >= 5:  # Valid YOLO format: class_id x y w h
                        try:
                            class_id = int(parts[0])
                            class_ids.add(class_id)
                            class_counts[class_id] = class_counts.get(class_id, 0) + 1
                        except ValueError:
                            continue

        # Create class mapping based on game entities
        # Based on your description: player, player_shot, enemy_a-p, enemy_shot
        class_names = self._create_class_names(sorted(class_ids))

        return {
            "num_classes": len(class_ids),
            "class_ids": sorted(class_ids),
            "class_names": class_names,
            "class_counts": class_counts,
        }

    def _create_class_names(self, class_ids: List[int]) -> List[str]:
        """Create meaningful class names based on class IDs

        ---

        클래스 ID를 기반으로 의미있는 클래스 이름 생성
        """
        # Mapping based on typical game entity structure
        # You can customize this mapping based on your actual game entities
        class_name_mapping = {
            0: "player",
            1: "player_shot",
            2: "enemy_a",
            3: "enemy_b",
            4: "enemy_c",
            5: "enemy_d",
            6: "enemy_e",
            7: "enemy_f",
            8: "enemy_g",
            9: "enemy_h",
            10: "enemy_i",
            11: "enemy_j",
            12: "enemy_k",
            13: "enemy_l",
            14: "enemy_m",
            15: "enemy_n",
            16: "enemy_o",
            17: "enemy_p",
            18: "enemy_shot",
        }

        class_names = []
        for class_id in class_ids:
            if class_id in class_name_mapping:
                class_names.append(class_name_mapping[class_id])
            else:
                class_names.append(f"class_{class_id}")

        return class_names

    def _split_samples(self, samples: List[YOLOSample]) -> Dict[str, List[YOLOSample]]:
        """Split samples into train/val/test sets

        ---

        샘플을 train/val/test 세트로 분할
        """
        total_samples = len(samples)

        train_end = int(total_samples * self.split_config.train_ratio)
        val_end = train_end + int(total_samples * self.split_config.val_ratio)

        return {
            "train": samples[:train_end],
            "val": samples[train_end:val_end],
            "test": samples[val_end:],
        }

    def _save_split_samples(self, split_name: str, samples: List[YOLOSample]) -> int:
        """Save samples for a specific split

        ---

        특정 분할에 대한 샘플 저장
        """
        images_dir = self.output_dir / split_name / "images"
        labels_dir = self.output_dir / split_name / "labels"

        saved_count = 0

        for sample in samples:
            try:
                # Save image
                image_path = images_dir / f"{sample.filename_base}.png"
                with open(image_path, "wb") as f:
                    f.write(sample.image_data)

                # Save YOLO labels
                label_path = labels_dir / f"{sample.filename_base}.txt"
                with open(label_path, "w", encoding="utf-8") as f:
                    for label in sample.yolo_labels:
                        f.write(f"{label}\n")

                saved_count += 1

            except Exception as e:
                logging.error(f"Failed to save sample {sample.filename_base}: {e}")
                continue

        return saved_count

    def _create_dataset_config(self, counts: Dict[str, int], class_info: Dict):
        """Create YOLO dataset configuration files

        ---

        YOLO 데이터셋 설정 파일 생성
        """
        # Create data.yaml for YOLO with actual class information
        data_yaml = {
            "path": str(self.output_dir.absolute()),
            "train": "train/images",
            "val": "val/images",
            "test": "test/images",
            "nc": class_info["num_classes"],
            "names": class_info["class_names"],
        }

        yaml_path = self.output_dir / "data.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            # Simple YAML writing
            f.write(f"path: {data_yaml['path']}\n")
            f.write(f"train: {data_yaml['train']}\n")
            f.write(f"val: {data_yaml['val']}\n")
            f.write(f"test: {data_yaml['test']}\n")
            f.write(f"nc: {data_yaml['nc']}\n")
            f.write("names:\n")
            for name in data_yaml["names"]:
                f.write(f"  - {name}\n")

        # Create dataset statistics with class information
        stats = {
            "dataset_name": "RL_DDA_YOLO_Dataset",
            "creation_timestamp": datetime.now().isoformat(),
            "split_configuration": {
                "train_ratio": self.split_config.train_ratio,
                "val_ratio": self.split_config.val_ratio,
                "test_ratio": self.split_config.test_ratio,
            },
            "sample_counts": counts,
            "total_samples": sum(counts.values()),
            "class_information": {
                "num_classes": class_info["num_classes"],
                "class_ids": class_info["class_ids"],
                "class_names": class_info["class_names"],
                "class_distribution": class_info["class_counts"],
            },
        }

        stats_path = self.output_dir / "dataset_stats.json"
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

        logging.info(f"Created dataset configuration: {yaml_path}")
        logging.info(f"Created dataset statistics: {stats_path}")
        logging.info(f"Class distribution: {class_info['class_counts']}")


def create_yolo_dataset(
    payload_log_file: str,
    output_dir: str,
    train_ratio: float = 0.7,
    val_ratio: float = 0.2,
    test_ratio: float = 0.1,
    shuffle: bool = True,
) -> Dict[str, int]:
    """Convenience function to create YOLO dataset

    Args:
        payload_log_file: Path to payload log file
        output_dir: Output directory for dataset
        train_ratio: Ratio for training set
        val_ratio: Ratio for validation set
        test_ratio: Ratio for test set
        shuffle: Whether to shuffle samples

    Returns:
        Dictionary with sample counts per split

    ---

    YOLO 데이터셋 생성을 위한 편의 함수

    Args:
        payload_log_file: payload 로그 파일 경로
        output_dir: 데이터셋 출력 디렉토리
        train_ratio: 훈련 세트 비율
        val_ratio: 검증 세트 비율
        test_ratio: 테스트 세트 비율
        shuffle: 샘플 셔플 여부

    Returns:
        분할별 샘플 수 딕셔너리
    """
    split_config = DatasetSplit(train_ratio, val_ratio, test_ratio)
    creator = YOLODatasetCreator(Path(output_dir), split_config)

    return creator.create_dataset(Path(payload_log_file), shuffle)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Create YOLO dataset from payload logs"
    )
    parser.add_argument("payload_log", help="Path to payload log file")
    parser.add_argument(
        "--output-dir", "-o", required=True, help="Output directory for dataset"
    )
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.7,
        help="Training set ratio (default: 0.7)",
    )
    parser.add_argument(
        "--val-ratio",
        type=float,
        default=0.2,
        help="Validation set ratio (default: 0.2)",
    )
    parser.add_argument(
        "--test-ratio", type=float, default=0.1, help="Test set ratio (default: 0.1)"
    )
    parser.add_argument(
        "--no-shuffle",
        action="store_true",
        help="Don't shuffle samples before splitting",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    try:
        counts = create_yolo_dataset(
            args.payload_log,
            args.output_dir,
            args.train_ratio,
            args.val_ratio,
            args.test_ratio,
            not args.no_shuffle,
        )

        print("✅ YOLO dataset creation completed!")
        print(f"\n📁 Dataset created in: {args.output_dir}")
        print(f"\n📊 Sample distribution:")
        total = sum(counts.values())
        for split, count in counts.items():
            percentage = (count / total * 100) if total > 0 else 0
            print(f"  {split}: {count} samples ({percentage:.1f}%)")
        print(f"  total: {total} samples")

    except Exception as e:
        print(f"❌ Error: {e}")
        exit(1)
