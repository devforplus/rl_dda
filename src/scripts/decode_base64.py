import base64
from PIL import Image
import io
import json # JSON 파일에서 데이터를 읽기 위해 추가

def decode_base64_to_image_file(base64_string, output_filename="decoded_image.png"):
    """
    Base64 인코딩된 PNG 이미지 문자열을 디코딩하여 이미지 파일로 저장합니다.
    """
    try:
        # Base64 문자열 앞뒤 공백 제거
        cleaned_base64_string = base64_string.strip()
        
        # Base64 디코딩
        image_bytes = base64.b64decode(cleaned_base64_string)
        
        # 바이트 데이터를 이미지로 로드
        image = Image.open(io.BytesIO(image_bytes))
        
        # 이미지 파일로 저장 (원본이 PNG였으므로 PNG로 저장)
        image.save(output_filename, "PNG")
        print(f"이미지가 성공적으로 '{output_filename}' 파일로 저장되었습니다.")
        print(f"정보: 형식={image.format}, 크기={image.size}, 모드={image.mode}")

        # 이미지를 화면에 표시 (선택 사항, GUI 환경에서 작동)
        # image.show()
        
    except base64.binascii.Error as e:
        print(f"Base64 디코딩 오류: {e}")
        print("입력된 문자열이 올바른 Base64 형식이 아니거나 손상되었을 수 있습니다.")
        print("문자열 전체를 정확히 복사했는지 확인해주세요.")
    except IOError as e:
        print(f"이미지 데이터 오류: {e}")
        print("Base64 디코딩은 성공했으나, 유효한 이미지 데이터가 아닐 수 있습니다 (예: PNG 형식이 아님).")
    except Exception as e:
        print(f"알 수 없는 오류 발생: {e}")

# --- 스크립트 사용 방법 ---
if __name__ == "__main__":
    # 1. JSON 파일 경로 설정
    json_file_path = "src/collected_rl_dataset (2).json" # 실제 JSON 파일 경로로 수정하세요.
    
    base64_image_data_from_file = None

    # 2. JSON 파일에서 image_png_base64 데이터 읽기
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data_list = json.load(f) # 데이터가 리스트 형태라고 가정
            if data_list and isinstance(data_list, list) and len(data_list) > 0:
                # 첫 번째 항목의 이미지 데이터를 사용한다고 가정
                first_item = data_list[0]
                if isinstance(first_item, dict) and "image_png_base64" in first_item:
                    base64_image_data_from_file = first_item["image_png_base64"]
                else:
                    print(f"JSON 파일의 첫 번째 항목에 'image_png_base64' 키가 없거나 형식이 잘못되었습니다.")
            else:
                print(f"JSON 파일 '{json_file_path}'이 비어있거나 예상한 데이터 구조가 아닙니다.")
    except FileNotFoundError:
        print(f"오류: JSON 파일 '{json_file_path}'을(를) 찾을 수 없습니다.")
    except json.JSONDecodeError:
        print(f"오류: JSON 파일 '{json_file_path}'의 형식이 잘못되었습니다.")
    except Exception as e:
        print(f"JSON 파일 처리 중 오류 발생: {e}")

    # 3. 읽어온 Base64 데이터로 이미지 변환 함수 호출
    if base64_image_data_from_file:
        print(f"JSON에서 읽어온 Base64 데이터로 변환 시도 (일부만 표시):")
        print(f"시작: {base64_image_data_from_file[:50]}...")
        print(f"끝: ...{base64_image_data_from_file[-50:]}")
        decode_base64_to_image_file(base64_image_data_from_file, "output_image_from_json.png")
    else:
        print("\nJSON 파일에서 Base64 데이터를 가져오지 못했습니다.")
        # 테스트용으로 직접 Base64 문자열을 입력하여 사용할 수도 있습니다:
        # example_base64_string = "여기에_매우_긴_base64_문자열_붙여넣기"
        # if example_base64_string != "여기에_매우_긴_base64_문자열_붙여넣기":
        #     print("예시 Base64 문자열로 변환 시도:")
        #     decode_base64_to_image_file(example_base64_string, "example_output_image.png")
