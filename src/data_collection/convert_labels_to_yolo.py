import os
import json
from glob import glob
from PIL import Image

# 클래스 매핑 (player + enemy 종류 자동)
def get_class_map(label_dir):
    class_set = set()
    for label_file in glob(os.path.join(label_dir, "*.json")):
        with open(label_file, "r") as f:
            label = json.load(f)
            class_set.add("player")
            for enemy in label.get("enemies", []):
                class_set.add(f'enemy_{enemy["type"].lower()}')
    class_list = sorted(list(class_set))
    return {cls: idx for idx, cls in enumerate(class_list)}, class_list

def convert_label(label_path, img_path, class_map):
    with open(label_path, "r") as f:
        label = json.load(f)
    img = Image.open(img_path)
    w, h = img.size

    lines = []
    # 플레이어
    player = label["player"]
    px, py = player["position"]
    pw, ph = player["bbox"]
    # 중심좌표, 크기 정규화
    x_center = (px + pw / 2) / w
    y_center = (py + ph / 2) / h
    width = pw / w
    height = ph / h
    lines.append(f"{class_map['player']} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")

    # 적들
    for enemy in label.get("enemies", []):
        ex, ey = enemy["position"]
        ew, eh = enemy["bbox"]
        x_center = (ex + ew / 2) / w
        y_center = (ey + eh / 2) / h
        width = ew / w
        height = eh / h
        class_name = f'enemy_{enemy["type"].lower()}'
        lines.append(f"{class_map[class_name]} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")

    return lines

def main():
    label_dir = "data/labels"
    image_dir = "data/images"
    yolo_label_dir = "data/yolo_labels"
    os.makedirs(yolo_label_dir, exist_ok=True)

    class_map, class_list = get_class_map(label_dir)
    with open("data/classes.txt", "w") as f:
        for cls in class_list:
            f.write(f"{cls}\n")

    for label_file in glob(os.path.join(label_dir, "*.json")):
        base = os.path.splitext(os.path.basename(label_file))[0]
        img_file = os.path.join(image_dir, base.replace("label_", "frame_") + ".png")
        if not os.path.exists(img_file):
            continue
        yolo_lines = convert_label(label_file, img_file, class_map)
        with open(os.path.join(yolo_label_dir, base + ".txt"), "w") as f:
            f.write("\n".join(yolo_lines))

if __name__ == "__main__":
    main() 