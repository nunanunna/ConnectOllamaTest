# chat/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_page, name='chat_page'),         # 메인 화면 접속 시 HTML 렌더링
    path('api/chat/', views.chat_api, name='chat_api'),  # JS에서 비동기로 호출할 API 주소
]