"""
URL configuration for ConnectOllamaTest project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include  # include 함수를 반드시 import 해야 합니다.

urlpatterns = [
    path('admin/', admin.site.urls),
    # 메인 경로 접속 시, 'chat' 앱 내부의 urls.py로 URL 처리를 위임합니다.
    path('', include('chat.urls')), 
]