import json
import os
from datetime import datetime
import numpy as np

class LabelGenerator:
    def __init__(self, save_dir="data/labels", img_width=256, img_height=192):
        self.save_dir = save_dir
        self.img_width = img_width
        self.img_height = img_height
        os.makedirs(save_dir, exist_ok=True)
        
    def normalize_coordinates(self, x, y, width, height):
        """
        좌표값을 이미지 크기에 맞게 정규화합니다.
        
        Args:
            x (float): 중심 x 좌표
            y (float): 중심 y 좌표
            width (float): 바운딩 박스 너비
            height (float): 바운딩 박스 높이
            
        Returns:
            tuple: 정규화된 좌표값 (x_center, y_center, width, height)
        """
        x_center = x / self.img_width
        y_center = y / self.img_height
        norm_width = width / self.img_width
        norm_height = height / self.img_height
        return x_center, y_center, norm_width, norm_height
        
    def to_center(self, x, y, width, height, pos_type="center"):
        """
        좌상단 좌표 또는 중심좌표를 중심좌표로 변환
        Args:
            x, y: 좌표
            width, height: 크기
            pos_type: "center" or "topleft"
        Returns:
            (center_x, center_y, width, height)
        """
        if pos_type == "topleft":
            center_x = x + width / 2
            center_y = y + height / 2
            return center_x, center_y, width, height
        else:
            return x, y, width, height

    def generate_label(self, frame_id, player_pos, player_bbox, enemy_pos, enemy_bbox, pos_type="center"):
        """
        플레이어와 적의 위치 및 바운딩 박스 정보를 포함한 YOLO 형식의 라벨을 생성합니다.
        
        Args:
            frame_id (int): 프레임 ID
            player_pos (tuple): 플레이어 위치 (x, y)
            player_bbox (tuple): 플레이어 바운딩 박스 (width, height)
            enemy_pos (tuple): 적 위치 (x, y)
            enemy_bbox (tuple): 적 바운딩 박스 (width, height)
            pos_type (str): "center" or "topleft"
            
        Returns:
            list: YOLO 형식의 라벨 데이터 리스트
        """
        labels = []
        
        # 플레이어
        px, py, pw, ph = self.to_center(*player_pos, *player_bbox, pos_type=pos_type)
        player_norm = self.normalize_coordinates(px, py, pw, ph)
        labels.append(f"0 {player_norm[0]:.6f} {player_norm[1]:.6f} {player_norm[2]:.6f} {player_norm[3]:.6f}")
        
        # 적
        ex, ey, ew, eh = self.to_center(*enemy_pos, *enemy_bbox, pos_type=pos_type)
        enemy_norm = self.normalize_coordinates(ex, ey, ew, eh)
        labels.append(f"1 {enemy_norm[0]:.6f} {enemy_norm[1]:.6f} {enemy_norm[2]:.6f} {enemy_norm[3]:.6f}")
        
        return labels
    
    def save_label(self, labels, filename=None):
        """
        YOLO 형식의 라벨을 .txt 파일로 저장합니다.
        
        Args:
            labels (list): YOLO 형식의 라벨 데이터 리스트
            filename (str, optional): 저장할 파일 이름. 기본값은 timestamp를 사용
            
        Returns:
            str: 저장된 파일 경로
        """
        if filename is None:
            filename = f"label_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        elif not filename.endswith('.txt'):
            filename = f"{filename}.txt"
            
        filepath = os.path.join(self.save_dir, filename)
        
        with open(filepath, 'w') as f:
            f.write('\n'.join(labels))
            
        return filepath 