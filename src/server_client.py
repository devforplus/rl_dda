import asyncio
import base64
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

# 웹 환경 감지 (Pyodide)
IS_WEB = False
try:
    import pyodide  # type: ignore

    IS_WEB = True
except ImportError:
    pass

if IS_WEB:
    import pyodide.http  # type: ignore

    class PyodideHttpClient:
        async def request(
            self,
            method: str,
            url: str,
            json: Optional[Dict[str, Any]] = None,
            data: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            timeout: int = 10,
        ) -> Dict[str, Any]:
            try:
                kwargs: Dict[str, Any] = {"method": method}

                # JSON 데이터 처리
                if json:
                    # JSON을 문자열로 직렬화
                    json_str = json_module.dumps(json)
                    print(
                        f"[PyodideHttpClient] JSON payload size: {len(json_str)} chars"
                    )

                    kwargs["body"] = json_str

                    # Content-Type 헤더 설정
                    if not headers:
                        headers = {}
                    headers["Content-Type"] = "application/json"
                elif data:
                    # Pyodide는 data를 직접 지원하지 않으므로, 일반적인 form data로 변환 시도
                    # 파일 업로드의 경우 특별한 처리가 필요할 수 있음
                    kwargs["data"] = data

                if headers:
                    kwargs["headers"] = headers

                print(f"[PyodideHttpClient] Request: {method} {url}")
                print(f"[PyodideHttpClient] Headers: {headers}")

                response = await pyodide.http.pyfetch(url, **kwargs)
                response_text = await response.string()
                status_code = response.status

                print(f"[PyodideHttpClient] Response: {status_code}")
                print(f"[PyodideHttpClient] Response text: {response_text[:200]}...")

                try:
                    response_json = json_module.loads(response_text)
                except json_module.JSONDecodeError:
                    response_json = {}

                return {
                    "status_code": status_code,
                    "text": response_text,
                    "json": response_json,
                }
            except Exception as e:
                print(f"[HttpClient] Pyodide request failed: {e}")
                return {"status_code": -1, "text": str(e), "json": {}}

    HttpClient = PyodideHttpClient
    json_module = json
else:
    import httpx  # type: ignore

    class HttpxClient:
        async def request(
            self,
            method: str,
            url: str,
            json: Optional[Dict[str, Any]] = None,
            data: Optional[Dict[str, Any]] = None,  # httpx는 data와 files를 구분
            files: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            timeout: int = 10,
        ) -> Dict[str, Any]:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method,
                        url,
                        json=json,
                        data=data,
                        files=files,
                        headers=headers,
                        timeout=timeout,
                    )
                    response_text = response.text
                    status_code = response.status_code
                    try:
                        response_json = response.json()
                    except httpx.JSONDecodeError:  # httpx의 경우 httpx.JSONDecodeError
                        response_json = {}
                    except getattr(
                        json, "JSONDecodeError", ValueError
                    ):  # json 모듈의 경우 json.JSONDecodeError
                        response_json = {}

                return {
                    "status_code": status_code,
                    "text": response_text,
                    "json": response_json,
                }
            except httpx.RequestError as e:
                print(f"[HttpClient] Httpx request failed: {e}")
                return {"status_code": -1, "text": str(e), "json": {}}
            except Exception as e:  # 기타 예외 처리
                print(f"[HttpClient] General request failed: {e}")
                return {"status_code": -1, "text": str(e), "json": {}}

    HttpClient = HttpxClient  # type: ignore
    json_module = json


# PIL import (웹에서는 없을 수 있음)
PILImage = None
if not IS_WEB:
    try:
        from PIL import Image as PILImageImport

        PILImage = PILImageImport
    except ImportError:
        print(
            "[ServerClient] PIL (Pillow) not found. Image processing features will be limited."
        )


class NewServerClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url
        self.http_client = HttpClient()
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["X-API-KEY"] = self.api_key

    async def _request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
        params: Optional[Dict[str, Any]] = None,  # GET 요청용 파라미터
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        if (
            params
        ):  # GET 요청 시 URL에 파라미터 추가 (httpx/pyfetch는 params 인자를 지원)
            # 간단한 구현을 위해 URL에 직접 추가 (실제 사용시에는 라이브러리 기능 활용)
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{query_string}"

        # 디버깅: 전송할 데이터 로그
        if payload:
            print(f"[ServerClient] {method} {url}")
            if isinstance(payload, list) and payload:
                print(f"[ServerClient] Payload: {len(payload)} items")
                first_item = payload[0]
                print(f"[ServerClient] First item keys: {list(first_item.keys())}")
                # 이미지 데이터는 너무 크므로 길이만 출력
                for key, value in first_item.items():
                    if key == "image_png_base64":
                        print(f"[ServerClient] {key}: {len(str(value))} chars")
                    elif key == "yolo_labels":
                        print(
                            f"[ServerClient] {key}: {len(value) if isinstance(value, list) else 'not list'} items"
                        )
                    else:
                        print(f"[ServerClient] {key}: {value}")
            else:
                print(f"[ServerClient] Payload: {payload}")
        else:
            print(f"[ServerClient] {method} {url} - No payload")

        # PyodideHttpClient는 json 인자만 받으므로, payload를 그대로 전달
        # HttpxClient도 json 인자를 받으므로 payload를 그대로 전달
        return await self.http_client.request(
            method, url, json=payload, headers=self.headers
        )

    async def create_data(self, dataset_entries: List[Dict[str, Any]]) -> Optional[str]:
        """
        새로운 RL 데이터를 D1에 저장합니다. (POST /data)
        """
        if not isinstance(dataset_entries, list) or not dataset_entries:
            print(
                "[ServerClient] Invalid data format for create_data. Expected non-empty list of dicts."
            )
            return None

        # 서버는 단일 객체만 처리하므로 첫 번째 항목만 전송
        entry = dataset_entries[0]

        if not isinstance(entry, dict):
            print(
                "[ServerClient] Invalid data format for create_data. Entry must be a dict."
            )
            return None

        print(f"[ServerClient] Sending single entry to server")
        print(f"[ServerClient] Entry keys: {list(entry.keys())}")

        # 필수 필드 검증
        required_fields = [
            "timestamp",
            "image_original_shape",
            "image_png_base64",
            "yolo_labels",
        ]
        missing_fields = [
            field
            for field in required_fields
            if field not in entry or entry[field] is None
        ]
        if missing_fields:
            print(f"[ServerClient] Entry missing fields: {missing_fields}")
            return None

        # 타임스탬프 값 구체적으로 확인
        timestamp_value = entry.get("timestamp")
        print(
            f"[ServerClient] Entry timestamp: {timestamp_value} (type: {type(timestamp_value)})"
        )

        # 이미지 데이터 크기 확인
        image_data = entry.get("image_png_base64", "")
        print(f"[ServerClient] Entry image_png_base64 length: {len(str(image_data))}")

        # YOLO 라벨 수 확인
        yolo_labels = entry.get("yolo_labels", [])
        print(
            f"[ServerClient] Entry yolo_labels count: {len(yolo_labels) if isinstance(yolo_labels, list) else 'not list'}"
        )

        # 서버가 기대하는 형식: 단일 객체 (dataset 래핑 없음)
        payload = entry
        print(f"[ServerClient] Final payload structure: {list(payload.keys())}")

        result = await self._request("POST", "/data", payload=payload)

        if result["status_code"] == 201 and "json" in result:
            response_data = result["json"]
            # 서버 응답에서 생성된 데이터의 ID를 반환
            if isinstance(response_data, dict) and response_data.get("id"):
                return str(response_data.get("id"))
            elif isinstance(response_data, dict) and response_data.get("data", {}).get(
                "id"
            ):
                return str(response_data.get("data", {}).get("id"))
            print(
                f"[ServerClient] create_data: Received 201 but ID not found in response: {response_data}"
            )
            return "unknown_id_on_201"  # ID를 못찾았지만 성공한 경우
        else:
            print(
                f"[ServerClient] create_data failed: {result['status_code']} - {result.get('text')}"
            )
            return None

    async def get_all_data(self) -> Optional[List[Dict[str, Any]]]:
        """
        D1에 저장된 모든 RL 데이터를 조회합니다. (GET /data)
        """
        result = await self._request("GET", "/data")
        if result["status_code"] == 200 and "json" in result:
            # 서버가 RL 데이터 배열을 반환한다고 가정
            response_data = result["json"]
            if isinstance(response_data, list):
                return response_data
            else:
                print(
                    f"[ServerClient] get_all_data: Expected list, got {type(response_data)}"
                )
                return None
        else:
            print(
                f"[ServerClient] get_all_data failed: {result['status_code']} - {result.get('text')}"
            )
            return None

    async def get_data_by_id(self, data_id: str) -> Optional[Dict[str, Any]]:
        """
        특정 ID에 해당하는 RL 데이터를 조회합니다. (GET /data/:id)
        """
        if not data_id:
            print("[ServerClient] data_id is required for get_data_by_id.")
            return None
        result = await self._request("GET", f"/data/{data_id}")
        if result["status_code"] == 200 and "json" in result:
            # 서버가 단일 RL 데이터 객체를 반환한다고 가정
            response_data = result["json"]
            if isinstance(response_data, dict):
                return response_data
            else:
                print(
                    f"[ServerClient] get_data_by_id: Expected dict, got {type(response_data)}"
                )
                return None
        elif result["status_code"] == 404:
            print(f"[ServerClient] get_data_by_id: Data with id {data_id} not found.")
            return None
        else:
            print(
                f"[ServerClient] get_data_by_id failed for id {data_id}: {result['status_code']} - {result.get('text')}"
            )
            return None

    async def update_data(self, data_id: str, data_update: Dict[str, Any]) -> bool:
        """
        특정 ID에 해당하는 RL 데이터를 수정합니다. (PUT /data/:id)
        """
        if not data_id:
            print("[ServerClient] data_id is required for update_data.")
            return False
        if not isinstance(data_update, dict):
            print("[ServerClient] data_update must be a dictionary for update_data.")
            return False

        result = await self._request("PUT", f"/data/{data_id}", payload=data_update)
        if result["status_code"] == 200:  # 성공 시 200 OK를 반환한다고 가정
            return True
        else:
            print(
                f"[ServerClient] update_data failed for id {data_id}: {result['status_code']} - {result.get('text')}"
            )
            return False

    async def delete_data(self, data_id: str) -> bool:
        """
        특정 ID에 해당하는 RL 데이터를 삭제합니다. (DELETE /data/:id)
        """
        if not data_id:
            print("[ServerClient] data_id is required for delete_data.")
            return False

        result = await self._request("DELETE", f"/data/{data_id}")
        if (
            result["status_code"] == 200 or result["status_code"] == 204
        ):  # 성공 시 200 OK 또는 204 No Content
            return True
        else:
            print(
                f"[ServerClient] delete_data failed for id {data_id}: {result['status_code']} - {result.get('text')}"
            )
            return False


# --- 기존 ServerClient 코드 (참고용으로 남겨두거나 필요시 통합/삭제) ---
# class ServerClient:
#     ... (기존 코드 내용) ...
#
# class QuickAutoUploadServerClient:
#     ... (기존 코드 내용) ...


async def main_test():
    # 테스트용 (실제 사용 시에는 환경 변수 등에서 URL을 가져와야 함)
    # 예: WORKERS_URL = os.environ.get("WORKERS_URL", "https://rl-dda-server.ijihyeon164.workers.dev")
    # 실제 배포된 Cloudflare Workers 주소 사용
    test_base_url = (
        "https://rl-dda-server.ijihyeon164.workers.dev"  # 실제 배포된 Worker URL
    )

    client = NewServerClient(base_url=test_base_url)

    # 1. 데이터 생성 테스트
    print("\n--- Testing Create Data ---")
    sample_dataset_entry = [
        {
            "timestamp": datetime.now().timestamp(),  # 숫자형 타임스탬프
            "image_original_shape": [192, 256, 3],
            "image_png_base64": "dummy_base64_string_for_testing_create",
            "yolo_labels": ["header", "label1", "label2"],
        }
    ]
    created_id = await client.create_data(sample_dataset_entry)
    if created_id:
        print(f"Data created with ID: {created_id}")
    else:
        print("Failed to create data.")
        return  # 생성 실패 시 이후 테스트 중단

    # 2. 모든 데이터 읽기 테스트
    print("\n--- Testing Get All Data ---")
    all_data = await client.get_all_data()
    if all_data is not None:  # None일 수도 있으므로 명시적 비교
        print(f"Retrieved {len(all_data)} entries.")
        # for entry in all_data:
        #     print(entry.get("timestamp")) # 너무 많은 데이터 출력 방지
        if all_data:
            print(f"First entry timestamp: {all_data[0].get('timestamp')}")
    else:
        print("Failed to retrieve all data.")

    # 3. ID로 데이터 읽기 테스트
    print("\n--- Testing Get Data by ID ---")
    if created_id and created_id != "unknown_id_on_201":  # ID가 있는 경우에만 테스트
        retrieved_data = await client.get_data_by_id(created_id)
        if retrieved_data:
            print(
                f"Retrieved data for ID {created_id}: {retrieved_data.get('timestamp')}"
            )
        else:
            print(f"Failed to retrieve data for ID {created_id}.")
    else:
        print(
            f"Skipping Get Data by ID test as created_id is not available: {created_id}"
        )

    # 4. 데이터 업데이트 테스트
    print("\n--- Testing Update Data ---")
    if created_id and created_id != "unknown_id_on_201":
        update_payload = {"yolo_labels": ["header", "updated_label1", "updated_label2"]}
        update_success = await client.update_data(created_id, update_payload)
        if update_success:
            print(f"Data with ID {created_id} updated successfully.")
            # 업데이트 확인을 위해 다시 읽어오기
            updated_data = await client.get_data_by_id(created_id)
            if updated_data:
                print(f"Updated yolo_labels: {updated_data.get('yolo_labels')}")
        else:
            print(f"Failed to update data with ID {created_id}.")
    else:
        print(f"Skipping Update Data test as created_id is not available: {created_id}")

    # 5. 데이터 삭제 테스트
    print("\n--- Testing Delete Data ---")
    if created_id and created_id != "unknown_id_on_201":
        delete_success = await client.delete_data(created_id)
        if delete_success:
            print(f"Data with ID {created_id} deleted successfully.")
            # 삭제 확인
            deleted_check = await client.get_data_by_id(created_id)
            if deleted_check is None:  # 404 등으로 None이 반환되어야 함
                print(f"Data with ID {created_id} confirmed deleted (not found).")
            else:
                print(
                    f"Error: Data with ID {created_id} still exists after deletion attempt."
                )
        else:
            print(f"Failed to delete data with ID {created_id}.")
    else:
        print(f"Skipping Delete Data test as created_id is not available: {created_id}")


if __name__ == "__main__":
    # Pyodide 환경에서는 top-level await이 가능할 수 있으나,
    # 일반 Python 환경에서는 asyncio.run()을 사용해야 합니다.
    if IS_WEB:
        # Pyodide 환경에서는 main_test()를 직접 호출하거나,
        # pyodide.run_async() 등을 사용할 수 있습니다.
        # 여기서는 간단히 직접 호출 시도 (실제 웹앱에서는 다를 수 있음)
        # asyncio.ensure_future(main_test()) # 백그라운드 실행
        print("Web environment: Run main_test() manually or via pyodide specifics.")

        # 웹에서 바로 실행되도록 처리 (예시)
        async def run_async_main():
            await main_test()

        if hasattr(asyncio, "get_running_loop"):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(run_async_main())
            except RuntimeError:  # No running event loop
                asyncio.run(run_async_main())  # 새로운 루프에서 실행
        else:  # 古いPythonバージョン
            asyncio.run(run_async_main())

    else:  # 데스크톱 환경
        asyncio.run(main_test())
