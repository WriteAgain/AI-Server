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
        {"role": "user", "content": f"새롭게 작성하려는 제목: {new_post['title']}"}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=messages
    )

    return response["choices"][0]["message"]["content"]

# AI 서버 엔드포인트: OpenAI를 호출하여 새 글 응답 생성
@app.get("/{userId}/generate")
async def generate_text(userId: str):
    pdf_path = "prompt.pdf"
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="프롬프트 PDF 파일을 찾을 수 없음")

    # PDF에서 프롬프트 읽기
    prompt_text = read_prompt_from_pdf(pdf_path)

    # 백엔드에서 이전 글 가져오기
    latest_posts_url = f"{BACKEND_SERVER}/{userId}/user/article"
    latest_posts_response = requests.get(latest_posts_url)

    if latest_posts_response.status_code != 200:
        raise HTTPException(status_code=500, detail="이전 글 데이터를 가져오는 중 오류 발생")

    latest_posts = latest_posts_response.json()

    # 백엔드에서 새 글 데이터 가져오기
    new_post_url = f"{BACKEND_SERVER}/{userId}/articles"
    new_post_response = requests.get(new_post_url)

    if new_post_response.status_code != 200:
        raise HTTPException(status_code=500, detail="새 글 데이터를 가져오는 중 오류 발생")

    new_post = new_post_response.json()

    # OpenAI에 요청하여 응답 생성
    response_text = generate_response(latest_posts, new_post, prompt_text)

    # 생성된 응답을 백엔드에 저장 (제목, 응답)
    save_response_url = f"{BACKEND_SERVER}/{userId}/articles"
    save_payload = {
        "title": new_post["title"],
        "generated_response": response_text
    }
    save_response = requests.post(save_response_url, json=save_payload)

    if save_response.status_code != 200:
        raise HTTPException(status_code=500, detail="생성된 응답을 저장하는 중 오류 발생")

    return {"response": response_text}
