# chat/views.py 전체 코드

import requests
import json
import ollama
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
import os

load_dotenv()

assembly_api_key = os.getenv("ASSEMBLY_API_KEY")

# ==========================================
# 1. 일반 AI 챗봇 화면 및 통신 API
# ==========================================
def chat_page(request):
    return render(request, 'chat/index.html')

@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_prompt = data.get('prompt', '')

            if not user_prompt:
                return JsonResponse({'error': '질문이 비어있습니다.'}, status=400)

            # 기본 챗봇 로컬 LLM 호출
            response = ollama.chat(
                model='gemma4:e4b',
                messages=[{'role': 'user', 'content': user_prompt}]
            )

            llm_reply = response['message']['content']
            return JsonResponse({'reply': llm_reply}, status=200)

        except Exception as e:
            return JsonResponse({'error': f'서버 내부 오류: {str(e)}'}, status=500)
            
    return JsonResponse({'error': 'POST 요청만 지원합니다.'}, status=405)

#
# ==========================================
# 2. 국회 법안 조회 화면 및 통신 API
# ==========================================
def bill_list_page(request):
    return render(request, 'chat/bills.html')

def fetch_recent_bills(request):
    # 주의: 발급받으신 실제 API 인증키로 교체해 주세요!
    api_key = '7ebbc9b78224446d89af859b2117e88e' 
    url = f'https://open.assembly.go.kr/portal/openapi/nzmimeepazxkubdpn?KEY={api_key}&Type=json&pIndex=1&pSize=10'
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        bill_data = data.get('nzmimeepazxkubdpn', [])
        if len(bill_data) > 1 and 'row' in bill_data[1]:
            raw_bills = bill_data[1]['row']
        else:
            raw_bills = []

        processed_bills = []
        for bill in raw_bills:
            processed_bills.append({
                'id': bill.get('BILL_NO', ''),
                'title': bill.get('BILL_NAME', '제목 없음'),
                'proposer': bill.get('PROPOSER', '발의자 정보 없음'),
                'date': bill.get('PROPOSE_DT', ''),
                'content': bill.get('PUBL_PROPOSER', '상세 제안 이유가 제공되지 않은 법안입니다.'),
                'detail_link': bill.get('DETAIL_LINK', '')
            })
            
        return JsonResponse({'bills': processed_bills}, status=200)

    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'API 호출 중 오류 발생: {str(e)}'}, status=500)


# ==========================================
# 3. 상세 법안 AI 3줄 요약 API
# ==========================================
@csrf_exempt
def summarize_bill_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            bill_content = data.get('content', '')

            if not bill_content or bill_content == '상세 제안 이유가 제공되지 않은 법안입니다.':
                return JsonResponse({'summary': '요약할 원문 데이터가 존재하지 않습니다.'}, status=200)

            system_prompt = (
                "당신은 어려운 법률 용어를 일반인의 눈높이에 맞춰 쉽게 설명해주는 AI 비서입니다. "
                "다음 규칙을 엄격히 지켜주세요:\n"
                "1. 주어진 법안의 제안 이유를 바탕으로, 일반 대중의 실생활에 미치는 영향을 중심으로 요약하세요.\n"
                "2. 반드시 숫자를 매긴 글머리 기호(1., 2., 3.)를 사용하여 딱 3문장으로만 출력하세요.\n"
                "3. 주어진 원문 텍스트에 없는 내용은 절대 지어내지 마세요."
            )

            # 요약용 로컬 LLM 호출
            response = ollama.chat(
                model='gemma4:e4b',
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': f"다음 법안 내용을 3줄로 요약해줘:\n\n{bill_content}"}
                ],
                options={
                    'temperature': 0.1, 
                    'top_p': 0.5
                }
            )
#
            summary = response['message']['content']
            return JsonResponse({'summary': summary}, status=200)

        except Exception as e:
            return JsonResponse({'error': f'요약 중 오류 발생: {str(e)}'}, status=500)
            
    return JsonResponse({'error': 'POST 요청만 지원합니다.'}, status=405)