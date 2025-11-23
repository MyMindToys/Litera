"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('about/', views.about, name='about'),
    # CRUD для ReferenceType
    path('reference-types/', views.reference_type_list, name='reference_type_list'),
    path('reference-types/create/', views.reference_type_create, name='reference_type_create'),
    path('reference-types/<int:pk>/', views.reference_type_detail, name='reference_type_detail'),
    path('reference-types/<int:pk>/update/', views.reference_type_update, name='reference_type_update'),
    path('reference-types/<int:pk>/delete/', views.reference_type_delete, name='reference_type_delete'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
