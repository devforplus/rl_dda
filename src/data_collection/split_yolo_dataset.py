import os
import shutil
import random
from glob import glob

# 경로 설정
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../data'))
IMG_DIR = os.path.join(BASE_DIR, 'images')
LABEL_DIR = os.path.join(BASE_DIR, 'yolo_labels')
OUT_IMG_TRAIN = os.path.join(BASE_DIR, 'dataset/images/train')
OUT_IMG_VAL = os.path.join(BASE_DIR, 'dataset/images/val')
OUT_LABEL_TRAIN = os.path.join(BASE_DIR, 'dataset/labels/train')
OUT_LABEL_VAL = os.path.join(BASE_DIR, 'dataset/labels/val')

# 파라미터
VAL_RATIO = 0.2  # 검증 데이터 비율

# 폴더 생성
def ensure_dirs():
    for d in [OUT_IMG_TRAIN, OUT_IMG_VAL, OUT_LABEL_TRAIN, OUT_LABEL_VAL]:
        os.makedirs(d, exist_ok=True)

def split_dataset():
    images = sorted(glob(os.path.join(IMG_DIR, '*.png')))
    random.shuffle(images)
    n_val = int(len(images) * VAL_RATIO)
    val_images = set(images[:n_val])
    train_images = set(images[n_val:])
    return train_images, val_images

def copy_files(image_set, img_out_dir, label_out_dir):
    for img_path in image_set:
        base = os.path.splitext(os.path.basename(img_path))[0]
        label_path = os.path.join(LABEL_DIR, base + '.txt')
        if not os.path.exists(label_path):
            continue
        shutil.copy2(img_path, os.path.join(img_out_dir, os.path.basename(img_path)))
        shutil.copy2(label_path, os.path.join(label_out_dir, os.path.basename(label_path)))

def write_yaml():
    yaml_path = os.path.join(BASE_DIR, 'dataset/data.yaml')
    class_list = [
        'player',
        'enemy_a', 'enemy_b', 'enemy_c', 'enemy_d', 'enemy_e', 'enemy_f', 'enemy_g', 'enemy_h',
        'enemy_i', 'enemy_j', 'enemy_k', 'enemy_l', 'enemy_m', 'enemy_n', 'enemy_o', 'enemy_p'
    ]
    train_path = OUT_IMG_TRAIN.replace("\\", "/")
    val_path = OUT_IMG_VAL.replace("\\", "/")
    with open(yaml_path, 'w') as f:
        f.write(f"train: {train_path}\n")
        f.write(f"val: {val_path}\n")
        f.write(f"\nnc: {len(class_list)}\n")
        f.write(f"names: {class_list}\n")

def main():
    ensure_dirs()
    train_images, val_images = split_dataset()
    copy_files(train_images, OUT_IMG_TRAIN, OUT_LABEL_TRAIN)
    copy_files(val_images, OUT_IMG_VAL, OUT_LABEL_VAL)
    write_yaml()
    print(f"Train: {len(train_images)} images, Val: {len(val_images)} images")
    print(f"data.yaml saved at: {os.path.join(BASE_DIR, 'dataset/data.yaml')}")

if __name__ == '__main__':
    main() 