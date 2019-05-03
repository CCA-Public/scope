"""SCOPE URL Configuration

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
from django.conf.urls import include, url
from django.contrib.auth import views as auth_views

from dips import views

urlpatterns = [
    url(r"^$", views.collections, {"template": "home.html"}, name="home"),
    url(
        r"^login/$",
        auth_views.LoginView.as_view(template_name="login.html"),
        name="login",
    ),
    url(r"^logout/$", auth_views.LogoutView.as_view(), name="logout"),
    url(
        r"^collections/",
        views.collections,
        {"template": "collections.html"},
        name="collections",
    ),
    url(
        r"^collection/(?P<pk>\d+)/edit/$", views.edit_collection, name="edit_collection"
    ),
    url(
        r"^collection/(?P<pk>\d+)/delete/$",
        views.delete_collection,
        name="delete_collection",
    ),
    url(r"^collection/(?P<pk>\d+)/$", views.collection, name="collection"),
    url(r"^new_collection/", views.new_collection, name="new_collection"),
    url(r"^folder/(?P<pk>\d+)/edit/$", views.edit_dip, name="edit_dip"),
    url(r"^folder/(?P<pk>\d+)/delete/$", views.delete_dip, name="delete_dip"),
    url(r"^folder/(?P<pk>\d+)/$", views.dip, name="dip"),
    url(r"^folder/(?P<pk>\d+)/download$", views.download_dip, name="download_dip"),
    url(r"^object/(?P<pk>[-\w-]+)$", views.digital_file, name="digital_file"),
    url(r"^new_folder/", views.new_dip, name="new_dip"),
    url(r"^orphan_folders/", views.orphan_dips, name="orphan_dips"),
    url(r"^faq/", views.faq, name="faq"),
    url(r"^search/", views.search, name="search"),
    url(r"^user/(?P<pk>\d+)/edit$", views.edit_user, name="edit_user"),
    url(r"^new_user/", views.new_user, name="new_user"),
    url(r"^users/", views.users, name="users"),
    url(r"^settings/", views.settings, name="settings"),
    url(r"^api/v1/", include("dips.api_urls")),
    url(r"^i18n/", include("django.conf.urls.i18n")),
]
