from django.contrib import admin
from django.urls import path
from feedback_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.submit_code, name='submit'), 
    path('history/', views.history, name='history'), 
    # 新增下面这行：如果是 history/数字/，就去看详情
    path('history/<int:record_id>/', views.history_detail, name='history_detail'), 
]