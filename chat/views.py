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
    # 수정: .env에서 불러온 api_key를 사용하도록 변경 (없으면 기존 하드코딩 키 사용)
    api_key = os.getenv("ASSEMBLY_API_KEY", "7ebbc9b78224446d89af859b2117e88e") 
    url = f'https://open.assembly.go.kr/portal/openapi/nzmimeepazxkubdpn?KEY={api_key}&Type=json&pIndex=1&pSize=10&AGE=22'    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # 디버깅용: 터미널에 국회 API 응답값을 출력해봅니다. (에러 원인 파악용)
        print("=== 국회 API 응답 데이터 ===")
        print(data) 
        
        bill_data = data.get('nzmimeepazxkubdpn', [])
        if len(bill_data) > 1 and 'row' in bill_data[1]:
            raw_bills = bill_data[1]['row']
        else:
            raw_bills = [] # 여기서 빈 배열이 처리되면서 화면에 안 떴을 확률이 높습니다.

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
# ==========================================
# 3. 상세 법안 제안이유 조회 및 AI 3줄 요약 API
# ==========================================
@csrf_exempt
def summarize_bill_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # 프론트엔드에서 넘겨준 의안번호(BILL_NO)를 받습니다.
            bill_id = data.get('bill_id', '')

            if not bill_id:
                return JsonResponse({'error': '의안번호가 전달되지 않았습니다.'}, status=400)

            # ---------------------------------------------------------
            # [1단계] 국회 '법률안 제안이유 및 주요내용' API 호출
            # ---------------------------------------------------------
            api_key = os.getenv("ASSEMBLY_API_KEY", "7ebbc9b78224446d89af859b2117e88e")
            
            # 🔥 [중요 수정 필요 1] 
            # 알려주신 API 페이지의 '기본호출 URL' 맨 마지막 영문 이름을 아래에 넣어주세요.
            # (예: https://open.assembly.go.kr/portal/openapi/abcd123 -> 'abcd123')
            endpoint = '여기에_API_영문_명칭_입력' 
            
            # 의안번호(BILL_NO)로 해당 법안만 콕 집어서 검색합니다.
            detail_url = f'https://open.assembly.go.kr/portal/openapi/{endpoint}?KEY={api_key}&Type=json&pIndex=1&pSize=1&BILL_NO={bill_id}'
            
            detail_response = requests.get(detail_url)
            detail_response.raise_for_status()
            detail_data = detail_response.json()
            
            # 상세 원문 데이터 추출
            bill_content = ""
            if endpoint in detail_data and 'row' in detail_data[endpoint][1]:
                row_data = detail_data[endpoint][1]['row'][0]
                
                # 🔥 [중요 수정 필요 2] 
                # API 문서의 '출력결과' 표를 보고 실제 데이터가 담긴 필드명으로 변경하세요.
                # (보통 'PROPOSE_REASON', 'DETAIL_CN', 'CN' 등의 이름으로 되어 있습니다.)
                reason = row_data.get('PROPOSER_REASON', '') # 제안이유 필드명 변경 필요
                main_content = row_data.get('MAIN_CONTENT', '') # 주요내용 필드명 변경 필요
                
                # 추출된 텍스트 합치기
                bill_content = f"제안이유: {reason}\n주요내용: {main_content}".strip()

            # API는 호출되었으나 아직 국회 측에서 원문을 등록하지 않은 경우
            if not bill_content or len(bill_content) < 15:
                return JsonResponse({'summary': '아직 국회 데이터베이스에 상세 제안 이유가 등록되지 않은 법안입니다.'}, status=200)

            # ---------------------------------------------------------
            # [2단계] 로컬 LLM(gemma4:e4b) 3줄 요약 요청
            # ---------------------------------------------------------
            system_prompt = (
                "당신은 어려운 법률 용어를 일반인의 눈높이에 맞춰 쉽게 설명해주는 AI 비서입니다. "
                "다음 규칙을 엄격히 지켜주세요:\n"
                "1. 주어진 법안의 제안 이유와 주요 내용을 바탕으로 일반 대중의 실생활에 미치는 영향을 중심으로 요약하세요.\n"
                "2. 반드시 숫자를 매긴 글머리 기호(1., 2., 3.)를 사용하여 딱 3문장으로만 출력하세요.\n"
                "3. 주어진 원문 텍스트에 없는 내용은 절대 지어내지 마세요."
            )

            response = ollama.chat(
                model='gemma4:e4b',
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': f"다음 법안 내용을 3줄로 요약해줘:\n\n{bill_content}"}
                ],
                options={'temperature': 0.1, 'top_p': 0.5}
            )

            summary = response['message']['content']
            return JsonResponse({'summary': summary}, status=200)

        except Exception as e:
            return JsonResponse({'error': f'상세조회/요약 중 오류 발생: {str(e)}'}, status=500)
            
    return JsonResponse({'error': 'POST 요청만 지원합니다.'}, status=405)