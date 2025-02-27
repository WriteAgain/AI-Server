import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수에서 값 가져오기
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BACKEND_SERVER = os.getenv("BACKEND_SERVER")

# 환경 변수 누락 시 예외 처리
if not OPENAI_API_KEY or not BACKEND_SERVER:
    raise ValueError("환경 변수 설정이 올바르지 않습니다. .env 파일을 확인하세요.")
