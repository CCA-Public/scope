"""accesspoc URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from accounts import views as account_views
from dips import views

urlpatterns = [
	url(r'^$', views.home, name='home'),
    url(r'^login/$', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    url(r'^logout/$', auth_views.LogoutView.as_view(), name='logout'),
    url(r'^collection/(?P<identifier>[\w\.-_]+)/edit/$', views.edit_collection, name='edit_collection'),
    url(r'^collection/(?P<identifier>[\w\.-_]+)/delete/$', views.delete_collection, name='delete_collection'),
	url(r'^collection/(?P<identifier>[\w\.-_]+)/$', views.collection, name='collection'),
    url(r'^new_collection/', views.new_collection, name='new_collection'),
    url(r'^folder/(?P<identifier>[-\w.-_]+)/edit/$', views.edit_dip, name='edit_dip'),
    url(r'^folder/(?P<identifier>[-\w.-_]+)/delete/$', views.delete_dip, name='delete_dip'),
    url(r'^folder/(?P<identifier>[-\w.-_]+)/$', views.dip, name='dip'),
    url(r'^object/(?P<uuid>[-\w-]+)$', views.digital_file, name='digital_file'),
    url(r'^new_folder/', views.new_dip, name='new_dip'),
    url(r'^faq/', views.faq, name='faq'),
    url(r'^search/', views.search, name='search'),
    url(r'^user/(?P<pk>\d+)/edit$', views.edit_user, name='edit_user'),
    url(r'^new_user/', views.new_user, name='new_user'),
    url(r'^users/', views.users, name='users'),
    url(r'^admin/', admin.site.urls),
]

urlpatterns += staticfiles_urlpatterns()
if settings.DEBUG: 
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)