import os
import openai
import fitz  # PyMuPDF (PDF에서 프롬프트 읽기)
import requests
from fastapi import FastAPI, HTTPException
from config import OPENAI_API_KEY, BACKEND_SERVER  # 설정 파일에서 값 가져오기

# OpenAI API 키 설정
openai.api_key = OPENAI_API_KEY

# FastAPI 앱 초기화
app = FastAPI()

# PDF에서 프롬프트 읽기 함수
def read_prompt_from_pdf(pdf_path: str) -> str:
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        return text.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF 읽기 오류: {str(e)}")

# LLM 응답 생성 함수
def generate_response(latest_posts, new_post, prompt: str) -> str:
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"최근 작성된 글들: {latest_posts}"},
        {"role": "user", "content": f"새롭게 작성하려는 제목: {new_post['title']}, 메모: {new_post['memo']}"}
    ]
    client = openai.OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    return response.choices[0].message.content

# AI 서버 엔드포인트: OpenAI를 호출하여 새 글 응답 생성
@app.post("/{userId}/articles")
async def generate_text(userId: str):
    pdf_path = "prompt.pdf"
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="프롬프트 PDF 파일을 찾을 수 없음")

    # PDF에서 프롬프트 읽기
    prompt_text = read_prompt_from_pdf(pdf_path)

    # 백엔드에서 최신 블로그 글 가져오기 (POST 방식)
    latest_posts_url = f"{BACKEND_SERVER}/{userId}/users/articles"
    latest_posts_response = requests.post(latest_posts_url, json={"userId": userId})

    if latest_posts_response.status_code != 200:
        raise HTTPException(status_code=500, detail="최신 블로그 글 데이터를 가져오는 중 오류 발생")

    latest_posts = latest_posts_response.json()

    # 백엔드에서 새 글 데이터 가져오기 (POST 방식)
    new_post_url = f"{BACKEND_SERVER}/{userId}/articles"
    new_post_response = requests.post(new_post_url, json={"userId": userId})

    if new_post_response.status_code != 200:
        raise HTTPException(status_code=500, detail="새 글 데이터를 가져오는 중 오류 발생")

    new_post = new_post_response.json()

    # 🔹 데이터가 모두 존재하는지 확인 (하나라도 없으면 오류 반환)
    if not latest_posts or not new_post or "title" not in new_post or "memo" not in new_post:
        raise HTTPException(status_code=400, detail="필수 데이터가 부족하여 응답을 생성할 수 없습니다.")

    # OpenAI에 요청하여 응답 생성
    response_text = generate_response(latest_posts, new_post, prompt_text)

    # 제목과 생성된 응답을 백엔드에 저장 
    save_response_url = f"{BACKEND_SERVER}/{userId}/articles"
    save_payload = {
        "title": new_post["title"],
        "content": response_text
    }
    save_response = requests.post(save_response_url, json=save_payload)

    if save_response.status_code != 200:
        raise HTTPException(status_code=500, detail="생성된 응답을 저장하는 중 오류 발생")

    return {
        "title": new_post["title"],
        "content": response_text
    }


# 터미널 실행 -> FastAPI 서버 실행
# uvicorn main:app --host 0.0.0.0 --port 8000
# 관리자 모드로 실행
# fastapi dev main.py