#!/usr/bin/env python3
"""
게임 데이터 서버 업로드 스크립트

이 스크립트는 게임 화면과 라벨 데이터를 서버에 업로드하는 기능을 제공합니다.
실시간 수집과 기존 데이터 업로드 두 가지 모드를 지원합니다.
"""

import argparse
import time
import os
import sys
from typing import Dict, Optional

# 상대 경로 import를 위한 경로 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dataset_collector import DatasetCollector
from server_client import GameDataServerClient


def create_sample_detections():
    """테스트용 샘플 detection 데이터 생성"""
    # 예시: 플레이어(class 0)와 적(class 1) 위치
    return [
        (0, 120, 150, 140, 170),  # 플레이어: 중앙 하단
        (1, 50, 30, 70, 50),  # 적1: 좌상단
        (1, 180, 40, 200, 60),  # 적2: 우상단
    ]


def real_time_collection_mode(server_url: str, duration: int = 60):
    """
    실시간 데이터 수집 및 서버 업로드 모드

    Args:
        server_url: 서버 URL
        duration: 수집 시간 (초)
    """
    print(f"실시간 데이터 수집 시작 (서버: {server_url})")
    print(f"수집 시간: {duration}초")
    print("게임을 시작하고 Enter를 눌러주세요...")
    input()

    # 서버 업로드 활성화된 데이터 수집기 생성
    collector = DatasetCollector(
        image_dir="datasets/images",
        label_dir="datasets/labels",
        app_width=256,
        app_height=192,
        server_url=server_url,
        enable_server_upload=True,
    )

    # 수집 시작
    collector.start_collection()

    start_time = time.time()
    frame_count = 0

    try:
        while time.time() - start_time < duration:
            # 실제 게임에서는 게임 엔진에서 detection 데이터를 가져와야 합니다
            # 여기서는 테스트용 샘플 데이터를 사용합니다
            detections = create_sample_detections()

            # 메타데이터 추가
            metadata = {
                "mode": "real_time",
                "frame_number": frame_count,
                "game_state": "playing",
                "player_score": frame_count * 10,
            }

            # 데이터 수집 및 서버 업로드
            collector.update(detections, metadata)
            frame_count += 1

            # 진행 상황 출력
            if frame_count % 10 == 0:
                elapsed = time.time() - start_time
                print(f"수집된 프레임: {frame_count}, 경과 시간: {elapsed:.1f}초")

            # 프레임 레이트 제한 (10 FPS)
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n사용자에 의해 수집이 중단되었습니다.")
    finally:
        collector.stop_collection()
        print(f"총 {frame_count}개 프레임이 수집되었습니다.")


def batch_upload_mode(server_url: str, images_dir: str, labels_dir: str):
    """
    기존 데이터 일괄 업로드 모드

    Args:
        server_url: 서버 URL
        images_dir: 이미지 디렉토리 경로
        labels_dir: 라벨 디렉토리 경로
    """
    print(f"기존 데이터 일괄 업로드 시작 (서버: {server_url})")
    print(f"이미지 디렉토리: {images_dir}")
    print(f"라벨 디렉토리: {labels_dir}")

    # 디렉토리 존재 확인
    if not os.path.exists(images_dir):
        print(f"오류: 이미지 디렉토리가 존재하지 않습니다: {images_dir}")
        return

    if not os.path.exists(labels_dir):
        print(f"오류: 라벨 디렉토리가 존재하지 않습니다: {labels_dir}")
        return

    # 서버 클라이언트 생성
    client = GameDataServerClient(server_url)

    # 서버 연결 확인
    if not client.check_server_status():
        print(f"오류: 서버 {server_url}에 연결할 수 없습니다.")
        return

    # 메타데이터 설정
    metadata = {
        "upload_mode": "batch",
        "source": "local_dataset",
        "upload_timestamp": time.time(),
    }

    # 일괄 업로드 실행
    uploaded_ids = client.batch_upload_directory(images_dir, labels_dir, metadata)

    print(f"업로드 완료: {len(uploaded_ids)}개 파일")
    if uploaded_ids:
        print("업로드된 데이터 ID 목록:")
        for i, data_id in enumerate(uploaded_ids[:5]):  # 처음 5개만 표시
            print(f"  {i + 1}. {data_id}")
        if len(uploaded_ids) > 5:
            print(f"  ... 및 {len(uploaded_ids) - 5}개 더")


def list_server_data(server_url: str):
    """서버에 저장된 데이터 목록 조회"""
    print(f"서버 데이터 목록 조회 (서버: {server_url})")

    client = GameDataServerClient(server_url)

    if not client.check_server_status():
        print(f"오류: 서버 {server_url}에 연결할 수 없습니다.")
        return

    data_list = client.list_data()

    if data_list is None:
        print("데이터 목록을 가져올 수 없습니다.")
        return

    if not data_list:
        print("서버에 저장된 데이터가 없습니다.")
        return

    # 서버 응답이 딕셔너리인 경우 처리
    if isinstance(data_list, dict):
        # 딕셔너리의 키들을 데이터 ID로 처리
        data_keys = list(data_list.keys())
        print(f"총 {len(data_keys)}개의 데이터가 저장되어 있습니다:")

        display_count = min(10, len(data_keys))
        for i in range(display_count):
            key = data_keys[i]
            data = data_list[key]
            print(f"  {i + 1}. ID: {key}")
            if isinstance(data, dict):
                print(f"     타임스탬프: {data.get('timestamp', 'N/A')}")
                print(f"     이미지: {data.get('image', {}).get('filename', 'N/A')}")
                print(f"     라벨: {data.get('label', {}).get('filename', 'N/A')}")
            print()

        if len(data_keys) > 10:
            print(f"... 및 {len(data_keys) - 10}개 더")
    elif isinstance(data_list, list):
        print(f"총 {len(data_list)}개의 데이터가 저장되어 있습니다:")
        display_count = min(10, len(data_list))
        for i in range(display_count):
            data = data_list[i]
            print(f"  {i + 1}. ID: {data.get('id', 'N/A')}")
            print(f"     타임스탬프: {data.get('timestamp', 'N/A')}")
            print(f"     이미지: {data.get('image', {}).get('filename', 'N/A')}")
            print(f"     라벨: {data.get('label', {}).get('filename', 'N/A')}")
            print()

        if len(data_list) > 10:
            print(f"... 및 {len(data_list) - 10}개 더")
    else:
        print(f"예상하지 못한 데이터 형식입니다: {type(data_list)}")
        print(f"데이터 내용: {data_list}")


def main():
    parser = argparse.ArgumentParser(description="게임 데이터 서버 업로드 도구")
    parser.add_argument(
        "--server-url",
        default="http://127.0.0.1:8787",
        help="서버 URL (기본값: http://127.0.0.1:8787)",
    )

    subparsers = parser.add_subparsers(dest="mode", help="실행 모드")

    # 실시간 수집 모드
    realtime_parser = subparsers.add_parser(
        "realtime", help="실시간 데이터 수집 및 업로드"
    )
    realtime_parser.add_argument(
        "--duration", type=int, default=60, help="수집 시간 (초, 기본값: 60)"
    )

    # 일괄 업로드 모드
    batch_parser = subparsers.add_parser("batch", help="기존 데이터 일괄 업로드")
    batch_parser.add_argument(
        "--images-dir", default="datasets/images", help="이미지 디렉토리 경로"
    )
    batch_parser.add_argument(
        "--labels-dir", default="datasets/labels", help="라벨 디렉토리 경로"
    )

    # 목록 조회 모드
    list_parser = subparsers.add_parser("list", help="서버 데이터 목록 조회")

    args = parser.parse_args()

    if args.mode == "realtime":
        real_time_collection_mode(args.server_url, args.duration)
    elif args.mode == "batch":
        batch_upload_mode(args.server_url, args.images_dir, args.labels_dir)
    elif args.mode == "list":
        list_server_data(args.server_url)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
