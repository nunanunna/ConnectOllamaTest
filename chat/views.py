# chat/views.py
import json
import ollama
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# 1. 프론트엔드 HTML 페이지를 렌더링하는 뷰
def chat_page(request):
    return render(request, 'chat/index.html')

# 2. 로컬 LLM(Ollama)과 통신하는 API 뷰
@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_prompt = data.get('prompt', '')

            if not user_prompt:
                return JsonResponse({'error': '질문이 비어있습니다.'}, status=400)

            # Ollama를 통해 백그라운드에 떠 있는 모델 호출 (모델명을 꼭 확인해 주세요!)
            response = ollama.chat(
                model='gemma4:e4b', 
                messages=[{'role': 'user', 'content': user_prompt}]
            )

            llm_reply = response['message']['content']
            return JsonResponse({'reply': llm_reply}, status=200)

        except Exception as e:
            return JsonResponse({'error': f'서버 내부 오류: {str(e)}'}, status=500)
            
    return JsonResponse({'error': 'POST 요청만 지원합니다.'}, status=405)