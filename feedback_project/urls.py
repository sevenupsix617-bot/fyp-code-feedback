from django.contrib import admin
from django.urls import include, path
from feedback_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', views.home, name='home'),
    path('experiment/', views.submit_code, name='experiment'),
    path('student/', views.student_submit, name='student_submit'),
    path('profile/', views.my_profile, name='my_profile'),
    path('instructor/', views.instructor_dashboard, name='instructor_dashboard'),
    path('analytics/', views.analytics_dashboard, name='analytics_dashboard'),
    path('evaluation/', views.evaluation_dashboard, name='evaluation_dashboard'),
    path('analytics/students/<int:user_id>/', views.student_profile, name='student_profile'),
    path('analytics/students/<int:user_id>/skill/<str:topic_id>/', views.student_skill_detail, name='student_skill_detail'),
    path('history/', views.history, name='history'), 
    path('history/<int:record_id>/', views.history_detail, name='history_detail'), 
]
