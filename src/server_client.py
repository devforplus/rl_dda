import requests
import json
import os
import base64
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import cv2
import numpy as np


class GameDataServerClient:
    """게임 데이터 서버와 통신하기 위한 클라이언트 클래스"""

    def __init__(self, server_url: str = "http://127.0.0.1:8787"):
        """
        서버 클라이언트 초기화

        Args:
            server_url: 서버 URL (기본값: http://127.0.0.1:8787)
        """
        self.server_url = server_url.rstrip("/")
        self.session = requests.Session()

    def check_server_status(self) -> bool:
        """
        서버 상태 확인

        Returns:
            bool: 서버가 정상 동작하면 True, 아니면 False
        """
        try:
            response = self.session.get(f"{self.server_url}/")
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def upload_game_data(
        self, image_path: str, label_path: str, metadata: Optional[Dict] = None
    ) -> Optional[str]:
        """
        게임 화면과 라벨 데이터를 서버에 업로드

        Args:
            image_path: 이미지 파일 경로
            label_path: 라벨 파일 경로
            metadata: 추가 메타데이터 (선택사항)

        Returns:
            str: 업로드 성공 시 데이터 ID, 실패 시 None
        """
        try:
            # 이미지 파일을 base64로 인코딩
            with open(image_path, "rb") as img_file:
                image_data = base64.b64encode(img_file.read()).decode("utf-8")

            # 라벨 파일 읽기
            with open(label_path, "r", encoding="utf-8") as label_file:
                label_data = label_file.read()

            # 업로드할 데이터 구성
            upload_data = {
                "timestamp": datetime.now().isoformat(),
                "image": {
                    "filename": os.path.basename(image_path),
                    "data": image_data,
                    "format": os.path.splitext(image_path)[1][1:],  # 확장자 (점 제거)
                },
                "label": {
                    "filename": os.path.basename(label_path),
                    "data": label_data,
                    "format": "yolo",
                },
                "metadata": metadata or {},
            }

            # 서버에 POST 요청
            response = self.session.post(
                f"{self.server_url}/api/upload",
                json=upload_data,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("id")
            else:
                print(f"업로드 실패: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"업로드 중 오류 발생: {e}")
            return None

    def upload_game_data_from_memory(
        self,
        image_array: np.ndarray,
        label_content: str,
        filename_prefix: str = "frame",
        metadata: Optional[Dict] = None,
    ) -> Optional[str]:
        """
        메모리에 있는 게임 화면과 라벨 데이터를 서버에 업로드

        Args:
            image_array: OpenCV 이미지 배열 (BGR 형식)
            label_content: YOLO 형식의 라벨 내용
            filename_prefix: 파일명 접두사
            metadata: 추가 메타데이터

        Returns:
            str: 업로드 성공 시 데이터 ID, 실패 시 None
        """
        try:
            # 이미지를 PNG 형식으로 인코딩
            _, img_encoded = cv2.imencode(".png", image_array)
            image_data = base64.b64encode(img_encoded.tobytes()).decode("utf-8")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

            # 업로드할 데이터 구성
            upload_data = {
                "timestamp": datetime.now().isoformat(),
                "image": {
                    "filename": f"{filename_prefix}_{timestamp}.png",
                    "data": image_data,
                    "format": "png",
                },
                "label": {
                    "filename": f"{filename_prefix}_{timestamp}.txt",
                    "data": label_content,
                    "format": "yolo",
                },
                "metadata": metadata or {},
            }

            # 서버에 POST 요청
            response = self.session.post(
                f"{self.server_url}/api/upload",
                json=upload_data,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("id")
            else:
                print(f"업로드 실패: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"업로드 중 오류 발생: {e}")
            return None

    def download_game_data(
        self, data_id: str, save_dir: str = "downloads"
    ) -> Optional[Tuple[str, str]]:
        """
        서버에서 게임 데이터 다운로드

        Args:
            data_id: 다운로드할 데이터 ID
            save_dir: 저장할 디렉토리

        Returns:
            Tuple[str, str]: (이미지 파일 경로, 라벨 파일 경로) 또는 None
        """
        try:
            response = self.session.get(f"{self.server_url}/api/download/{data_id}")

            if response.status_code == 200:
                data = response.json()

                # 저장 디렉토리 생성
                os.makedirs(save_dir, exist_ok=True)

                # 이미지 저장
                image_data = base64.b64decode(data["image"]["data"])
                image_filename = data["image"]["filename"]
                image_path = os.path.join(save_dir, image_filename)

                with open(image_path, "wb") as img_file:
                    img_file.write(image_data)

                # 라벨 저장
                label_content = data["label"]["data"]
                label_filename = data["label"]["filename"]
                label_path = os.path.join(save_dir, label_filename)

                with open(label_path, "w", encoding="utf-8") as label_file:
                    label_file.write(label_content)

                return image_path, label_path
            else:
                print(f"다운로드 실패: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"다운로드 중 오류 발생: {e}")
            return None

    def list_data(self) -> Optional[List[Dict]]:
        """
        서버에 저장된 데이터 목록 조회

        Returns:
            List[Dict]: 데이터 목록 또는 None
        """
        try:
            response = self.session.get(f"{self.server_url}/api/list")

            if response.status_code == 200:
                return response.json()
            else:
                print(f"목록 조회 실패: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"목록 조회 중 오류 발생: {e}")
            return None

    def delete_data(self, data_id: str) -> bool:
        """
        서버에서 데이터 삭제

        Args:
            data_id: 삭제할 데이터 ID

        Returns:
            bool: 삭제 성공 시 True, 실패 시 False
        """
        try:
            response = self.session.delete(f"{self.server_url}/api/delete/{data_id}")

            if response.status_code == 200:
                return True
            else:
                print(f"삭제 실패: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"삭제 중 오류 발생: {e}")
            return False

    def batch_upload_directory(
        self, images_dir: str, labels_dir: str, metadata: Optional[Dict] = None
    ) -> List[str]:
        """
        디렉토리의 모든 이미지와 라벨을 일괄 업로드

        Args:
            images_dir: 이미지 디렉토리 경로
            labels_dir: 라벨 디렉토리 경로
            metadata: 추가 메타데이터

        Returns:
            List[str]: 업로드된 데이터 ID 목록
        """
        uploaded_ids = []

        # 이미지 파일 목록 가져오기
        image_files = [
            f
            for f in os.listdir(images_dir)
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]

        for image_file in image_files:
            # 대응하는 라벨 파일 찾기
            base_name = os.path.splitext(image_file)[0]
            label_file = f"{base_name}.txt"

            image_path = os.path.join(images_dir, image_file)
            label_path = os.path.join(labels_dir, label_file)

            if os.path.exists(label_path):
                data_id = self.upload_game_data(image_path, label_path, metadata)
                if data_id:
                    uploaded_ids.append(data_id)
                    print(f"업로드 완료: {image_file} -> {data_id}")
                else:
                    print(f"업로드 실패: {image_file}")
            else:
                print(f"라벨 파일 없음: {label_file}")

        return uploaded_ids
