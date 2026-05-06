# chat/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_page, name='chat_page'),
    path('api/chat/', views.chat_api, name='chat_api'),
    path('bills/', views.bill_list_page, name='bill_list_page'),
    path('api/bills/', views.fetch_recent_bills, name='fetch_recent_bills'),
    
    # AI 3줄 요약을 위한 새로운 통신 통로입니다♡
    path('api/summarize/', views.summarize_bill_api, name='summarize_bill_api'),
]