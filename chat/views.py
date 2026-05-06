# chat/views.py 전체 코드

from django.http import StreamingHttpResponse, JsonResponse
from .models import BillSummaryCache 
import requests
import json
import ollama
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from dotenv import load_dotenv
import os
import re

load_dotenv()

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


# ==========================================
# 2. 국회 법안 조회 화면 및 통신 API
# ==========================================
def bill_list_page(request):
    return render(request, 'chat/bills.html')

def fetch_recent_bills(request):
    api_key = os.getenv("ASSEMBLY_API_KEY", "7ebbc9b78224446d89af859b2117e88e") 
    
    # 🔥 프론트엔드에서 보낸 page 번호를 받습니다. (기본값 1)
    page = request.GET.get('page', '1')
    
    # 🔥 pIndex={page} 로 변경하여 요청한 페이지의 데이터를 가져오도록 수정했습니다.
    url = f'https://open.assembly.go.kr/portal/openapi/nzmimeepazxkubdpn?KEY={api_key}&Type=json&pIndex={page}&pSize=10&AGE=22'    
    
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
                'detail_link': bill.get('DETAIL_LINK', '')
            })
            
        return JsonResponse({'bills': processed_bills}, status=200)

    except requests.exceptions.RequestException as e:
        return JsonResponse({'error': f'API 호출 중 오류 발생: {str(e)}'}, status=500)

# ==========================================
# 3. 상세 법안 제안이유 조회 및 AI 3줄 요약 API
# ==========================================
@csrf_exempt
def summarize_bill_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            bill_id = data.get('bill_id', '')

            if not bill_id:
                return JsonResponse({'error': '의안번호가 전달되지 않았습니다.'}, status=400)

# ---------------------------------------------------------
            # ⭐ [핵심 1] 데이터베이스(DB)에서 먼저 찾기!
            # ---------------------------------------------------------
            cached_data = BillSummaryCache.objects.filter(bill_id=bill_id).first()
            if cached_data:
                # DB에 있으면 LLM을 돌리지 않고 즉시(0.1초 컷) 응답합니다!
                return JsonResponse({
                    'cached': True, 
                    'tag1': cached_data.tag1,
                    'tag2': cached_data.tag2,
                    'summary': f"{cached_data.tag1} {cached_data.tag2}\n\n{cached_data.summary_text}"
                }, status=200)

            # ---------------------------------------------------------
            # [DB에 없을 경우] 기존처럼 국회 API 원문 호출
            # ---------------------------------------------------------
            api_key = os.getenv("ASSEMBLY_API_KEY", "7ebbc9b78224446d89af859b2117e88e")
            endpoint = 'BPMBILLSUMMARY'  
            detail_url = f'https://open.assembly.go.kr/portal/openapi/{endpoint}?KEY={api_key}&Type=json&pIndex=1&pSize=1&BILL_NO={bill_id}'
            
            detail_response = requests.get(detail_url)
            detail_data = detail_response.json()
            
            bill_content = ""
            if endpoint in detail_data and 'row' in detail_data[endpoint][1]:
                bill_content = detail_data[endpoint][1]['row'][0].get('SUMMARY', '').strip()

            if len(bill_content) < 15:
                return JsonResponse({'summary': '아직 국회 데이터베이스에 상세 제안 이유가 등록되지 않은 법안입니다.'}, status=200)

            # ---------------------------------------------------------
            # ⭐ [핵심 2] LLM 스트리밍 + 태그 생성 + DB 저장
            # ---------------------------------------------------------
            def stream_generator():
                # 태그와 요약을 한 번에 요구하는 프롬프트로 수정
                system_prompt = (
                    "당신은 법안을 분석하는 AI입니다. 다음 규칙을 엄격히 지켜주세요:\n"
                    "1. 첫 줄에는 반드시 이 법안의 핵심 주제를 나타내는 단어 2개를 해시태그 형식으로 적으세요. (예: #부동산 #세금)\n"
                    "2. 두 번째 줄부터는 일반인의 눈높이에 맞춰 딱 3문장(1., 2., 3.)으로 요약하세요.\n"
                    "3. 주어진 텍스트에 없는 내용은 지어내지 마세요."
                )

                stream = ollama.chat(
                    model='gemma4:e4b',
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': f"법안 내용:\n{bill_content}"}
                    ],
                    options={'temperature': 0.1, 'top_p': 0.5},
                    stream=True 
                )
                
                full_generated_text = ""
                
                # 실시간으로 화면에 쏴주기
                for chunk in stream:
                    text_chunk = chunk['message']['content']
                    full_generated_text += text_chunk
                    yield f"data: {json.dumps({'text': text_chunk})}\n\n"
                
                # 스트리밍이 끝난 후, 생성된 전체 텍스트를 분석하여 DB에 자동 저장!
                try:
                    # 첫 줄에서 #태그 두 개 추출 시도
                    tags = re.findall(r'#(\w+)', full_generated_text)
                    tag1 = f"#{tags[0]}" if len(tags) > 0 else "#분류없음"
                    tag2 = f"#{tags[1]}" if len(tags) > 1 else "#분류없음"
                    
                    # 태그를 제외한 나머지 부분을 요약 텍스트로 간주
                    summary_only = re.sub(r'#\w+', '', full_generated_text).strip()

                    # DB에 저장 (다음번엔 0.1초 만에 불러오기 위해)
                    BillSummaryCache.objects.create(
                        bill_id=bill_id,
                        tag1=tag1,
                        tag2=tag2,
                        summary_text=summary_only
                    )
                except Exception as e:
                    print("DB 저장 중 에러 발생:", e)

                yield "data: [DONE]\n\n"

            return StreamingHttpResponse(stream_generator(), content_type='text/event-stream')

        except Exception as e:
            return JsonResponse({'error': f'상세조회 중 오류 발생: {str(e)}'}, status=500)
            
    return JsonResponse({'error': 'POST 요청만 지원합니다.'}, status=405)