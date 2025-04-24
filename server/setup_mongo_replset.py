import os
import subprocess
import sys
import time
import json
import tempfile


def run_command(command, print_output=True):
    """명령을 실행하고 결과를 반환합니다."""
    print(f"명령 실행: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        if print_output and result.stdout:
            print(result.stdout)
        return True, result.stdout
    else:
        print(f"실패: {result.stderr}")
        return False, result.stderr


def check_mongo_installed():
    """MongoDB가 설치되어 있는지 확인합니다."""
    # 일반적인 명령어 경로 확인
    success, output = run_command("mongod --version", print_output=False)
    if success:
        return True

    # Windows의 기본 설치 경로에서 확인
    mongo_paths = [
        r"C:\Program Files\MongoDB\Server\8.0\bin\mongod.exe",
        r"C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe",
        r"C:\Program Files\MongoDB\Server\6.0\bin\mongod.exe",
        r"C:\Program Files\MongoDB\Server\5.0\bin\mongod.exe",
        r"C:\Program Files\MongoDB\Server\4.4\bin\mongod.exe",
    ]

    for path in mongo_paths:
        if os.path.exists(path):
            print(f"MongoDB 발견: {path}")
            return True

    return False


def find_mongod_path():
    """MongoDB 실행 파일 경로를 찾습니다."""
    # 일반적인 명령어 경로 확인
    success, output = run_command("where mongod", print_output=False)
    if success and output.strip():
        return output.strip().split("\n")[0]

    # Windows의 기본 설치 경로에서 확인
    mongo_paths = [
        r"C:\Program Files\MongoDB\Server\8.0\bin\mongod.exe",
        r"C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe",
        r"C:\Program Files\MongoDB\Server\6.0\bin\mongod.exe",
        r"C:\Program Files\MongoDB\Server\5.0\bin\mongod.exe",
        r"C:\Program Files\MongoDB\Server\4.4\bin\mongod.exe",
    ]

    for path in mongo_paths:
        if os.path.exists(path):
            return path

    return "mongod"  # 기본값으로 그냥 mongod 명령어 반환


def check_mongo_running():
    """MongoDB가 실행 중인지 확인합니다."""
    try:
        # pymongo를 먼저 설치
        try:
            import pymongo
        except ImportError:
            print("pymongo 패키지를 설치합니다...")
            success, _ = run_command(f"{sys.executable} -m pip install pymongo")
            if not success:
                print("pymongo 설치 실패.")
                return False
            import pymongo

        client = pymongo.MongoClient(
            "mongodb://localhost:27017", serverSelectionTimeoutMS=2000
        )
        client.admin.command("ping")
        return True
    except Exception as e:
        print(f"MongoDB 연결 실패: {str(e)}")
        return False


def create_config_file():
    """복제셋 설정을 위한 MongoDB 설정 파일을 생성합니다."""
    config = """
# MongoDB 설정 파일
storage:
  dbPath: ./data/db
  journal:
    enabled: true

# 네트워크 설정
net:
  port: 27017
  bindIp: 127.0.0.1

# 복제셋 설정
replication:
  replSetName: rs0
"""

    config_dir = os.path.join(os.getcwd(), "config")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    config_path = os.path.join(config_dir, "mongod.conf")
    with open(config_path, "w") as f:
        f.write(config)

    return config_path


def create_data_dir():
    """데이터 디렉토리를 생성합니다."""
    data_dir = os.path.join(os.getcwd(), "data", "db")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir


def start_mongo_with_replset(config_path):
    """복제셋 모드로 MongoDB를 시작합니다."""
    mongod_path = find_mongod_path()
    command = f'"{mongod_path}" --config "{config_path}"'

    # Windows에서는 새 프로세스로 MongoDB 시작
    if sys.platform == "win32":
        try:
            subprocess.Popen(
                command, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        except Exception as e:
            print(f"MongoDB 시작 실패: {str(e)}")
            print("직접 다음 명령어를 실행해보세요:")
            print(command)
    else:
        subprocess.Popen(command, shell=True)

    print("MongoDB 시작 중...")
    # MongoDB가 시작될 때까지 대기
    time.sleep(5)


def init_replset():
    """복제셋을 초기화합니다."""
    try:
        # pymongo가 설치되어 있는지 확인
        import pymongo
    except ImportError:
        print("pymongo 패키지를 설치합니다...")
        success, _ = run_command(f"{sys.executable} -m pip install pymongo")
        if not success:
            print("pymongo 설치 실패. 설정을 중단합니다.")
            return False
        import pymongo

    try:
        client = pymongo.MongoClient("mongodb://localhost:27017")

        # 이미 복제셋이 초기화되어 있는지 확인
        try:
            status = client.admin.command("replSetGetStatus")
            print("복제셋이 이미 초기화되어 있습니다.")
            return True
        except pymongo.errors.OperationFailure:
            # 복제셋이 아직 초기화되지 않음
            pass

        # 복제셋 초기화
        config = {"_id": "rs0", "members": [{"_id": 0, "host": "localhost:27017"}]}

        result = client.admin.command("replSetInitiate", config)
        print("복제셋 초기화 결과:", result)
        return True
    except Exception as e:
        print("복제셋 초기화 실패:", str(e))
        print("MongoDB가 실행 중인지 확인하고 다시 시도해주세요.")
        print("또는 mongosh를 실행하여 직접 다음 명령어를 실행해보세요:")
        print('rs.initiate({_id: "rs0", members: [{_id: 0, host: "localhost:27017"}]})')
        return False


def update_env_file():
    """환경 변수 파일을 업데이트합니다."""
    env_path = os.path.join(os.getcwd(), ".env")

    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()

        with open(env_path, "w") as f:
            for line in lines:
                if line.startswith("DATABASE_URL="):
                    f.write(
                        'DATABASE_URL="mongodb://localhost:27017/vortextion?replicaSet=rs0&directConnection=true"\n'
                    )
                else:
                    f.write(line)

        print(".env 파일에 복제셋 설정을 추가했습니다.")
    else:
        print(".env 파일을 찾을 수 없습니다.")


def main():
    """MongoDB 복제셋 설정을 수행합니다."""
    print("===== MongoDB 복제셋 설정 시작 =====")

    # 1. MongoDB 설치 확인
    if not check_mongo_installed():
        print("\nMongoDB가 설치되어 있지만 자동으로 감지되지 않았습니다.")
        print("다음 중 하나를 선택하세요:")
        print("1. MongoDB가 설치되어 있고 계속 진행하기")
        print("2. MongoDB가 설치되어 있지 않아 종료하기")
        choice = input("선택: ")

        if choice != "1":
            print("MongoDB를 설치한 후 다시 시도해주세요.")
            print(
                "https://www.mongodb.com/try/download/community 에서 다운로드할 수 있습니다."
            )
            return
    else:
        print("MongoDB 설치가 확인되었습니다.")

    # 2. MongoDB가 실행 중인지 확인
    if check_mongo_running():
        print("MongoDB가 이미 실행 중입니다. 중지 후 다시 시작합니다.")
        if sys.platform == "win32":
            run_command("net stop MongoDB")
        else:
            run_command("sudo systemctl stop mongod")

    # 3. 설정 파일 생성
    config_path = create_config_file()
    print(f"MongoDB 설정 파일 생성: {config_path}")

    # 4. 데이터 디렉토리 생성
    data_dir = create_data_dir()
    print(f"데이터 디렉토리 생성: {data_dir}")

    # 5. 복제셋 모드로 MongoDB 시작
    start_mongo_with_replset(config_path)

    # 6. MongoDB가 시작되었는지 확인
    for i in range(3):  # 최대 3번 시도
        if check_mongo_running():
            print("MongoDB가 성공적으로 시작되었습니다.")
            break
        else:
            print(f"MongoDB 연결 시도 중... ({i + 1}/3)")
            time.sleep(3)
    else:
        print("MongoDB 연결에 실패했습니다. 수동으로 MongoDB를 시작해주세요.")
        return

    # 7. 복제셋 초기화
    if init_replset():
        # 8. 환경 변수 파일 업데이트
        update_env_file()

        print("\n===== MongoDB 복제셋 설정 완료 =====")
        print("이제 애플리케이션을 실행하여 트랜잭션을 사용할 수 있습니다.")
        print("애플리케이션을 다시 시작하려면:")
        print("  python -m src.main")
    else:
        print("\n===== MongoDB 복제셋 설정 실패 =====")
        print("문제를 해결한 후 다시 시도해주세요.")


if __name__ == "__main__":
    main()
