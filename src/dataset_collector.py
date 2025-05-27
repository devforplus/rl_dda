import os
import pyautogui
import cv2
import numpy as np
from datetime import datetime
from typing import Optional, Dict
from server_client import GameDataServerClient


class DatasetCollector:
    def __init__(
        self,
        image_dir="datasets/images",
        label_dir="datasets/labels",
        app_width=256,
        app_height=192,
        server_url: Optional[str] = None,
        enable_server_upload: bool = False,
    ):
        self.image_dir = image_dir
        self.label_dir = label_dir
        self.app_width = app_width
        self.app_height = app_height
        self.is_collecting = False
        self.enable_server_upload = enable_server_upload

        # 서버 클라이언트 초기화
        if enable_server_upload and server_url:
            self.server_client = GameDataServerClient(server_url)
            # 서버 연결 확인
            if not self.server_client.check_server_status():
                print(
                    f"경고: 서버 {server_url}에 연결할 수 없습니다. 로컬 저장만 수행됩니다."
                )
                self.enable_server_upload = False
        else:
            self.server_client = None

        os.makedirs(self.image_dir, exist_ok=True)
        os.makedirs(self.label_dir, exist_ok=True)

    def start_collection(self):
        self.is_collecting = True

    def stop_collection(self):
        self.is_collecting = False

    def toggle_collection(self):
        self.is_collecting = not self.is_collecting

    def capture_screen(self):
        # Capture the region of the game window (top-left at (0,0), size app_width x app_height)
        img = pyautogui.screenshot(region=(0, 0, self.app_width, self.app_height))
        img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        return img

    def save_image(self, img, timestamp):
        img_name = f"frame_{timestamp}.png"
        img_path = os.path.join(self.image_dir, img_name)
        cv2.imwrite(img_path, img)
        return img_name

    def save_labels(self, detections, timestamp):
        # detections: list of (class_id, x_min, y_min, x_max, y_max)
        label_name = f"frame_{timestamp}.txt"
        label_path = os.path.join(self.label_dir, label_name)
        with open(label_path, "w") as f:
            for det in detections:
                class_id, x_min, y_min, x_max, y_max = det
                yolo_line = self.to_yolo_format(class_id, x_min, y_min, x_max, y_max)
                f.write(yolo_line + "\n")
        return label_name

    def to_yolo_format(self, class_id, x_min, y_min, x_max, y_max):
        # Convert to YOLO format: class cx cy w h (all normalized)
        cx = (x_min + x_max) / 2.0 / self.app_width
        cy = (y_min + y_max) / 2.0 / self.app_height
        w = (x_max - x_min) / self.app_width
        h = (y_max - y_min) / self.app_height
        return f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"

    def update(self, detections=None, metadata: Optional[Dict] = None):
        if not self.is_collecting or detections is None:
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        img = self.capture_screen()
        img_name = self.save_image(img, timestamp)
        label_name = self.save_labels(detections, timestamp)

        # 서버 업로드 (활성화된 경우)
        if self.enable_server_upload and self.server_client:
            self._upload_to_server(img, detections, timestamp, metadata)

    def _upload_to_server(
        self,
        img: np.ndarray,
        detections,
        timestamp: str,
        metadata: Optional[Dict] = None,
    ):
        """서버에 데이터 업로드"""
        try:
            # YOLO 형식 라벨 생성
            label_content = ""
            for det in detections:
                class_id, x_min, y_min, x_max, y_max = det
                yolo_line = self.to_yolo_format(class_id, x_min, y_min, x_max, y_max)
                label_content += yolo_line + "\n"

            # 메타데이터에 게임 정보 추가
            upload_metadata = metadata or {}
            upload_metadata.update(
                {
                    "app_width": self.app_width,
                    "app_height": self.app_height,
                    "detection_count": len(detections),
                    "timestamp": timestamp,
                }
            )

            # 서버에 업로드
            data_id = self.server_client.upload_game_data_from_memory(
                img, label_content.strip(), "frame", upload_metadata
            )

            if data_id:
                print(f"서버 업로드 성공: {data_id}")
            else:
                print("서버 업로드 실패")

        except Exception as e:
            print(f"서버 업로드 중 오류: {e}")

    def upload_existing_data(self, metadata: Optional[Dict] = None) -> int:
        """기존에 저장된 로컬 데이터를 서버에 일괄 업로드"""
        if not self.enable_server_upload or not self.server_client:
            print("서버 업로드가 비활성화되어 있습니다.")
            return 0

        uploaded_count = 0
        uploaded_ids = self.server_client.batch_upload_directory(
            self.image_dir, self.label_dir, metadata
        )
        uploaded_count = len(uploaded_ids)

        print(f"총 {uploaded_count}개 파일이 서버에 업로드되었습니다.")
        return uploaded_count
