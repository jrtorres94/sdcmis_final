from django.urls import path

from . import views

urlpatterns = [

    path('', views.home, name=""),

    path('register/', views.register, name='register'),

    path('login', views.login, name='login'),

    path('logout', views.logout, name='logout'),

    #crud

    path('dashboard/', views.dashboard, name='dashboard'),

    path('iec_addrecord/', views.iec_addrecord, name='iec_addrecord'),

    path('update_iec/<int:pk>', views.update_iec, name='update_iec'),

    path('view_iec/<int:pk>', views.view_iec, name='view_iec'),

    path('delete_iec/<int:pk>', views.delete_iec, name='delete_iec'),
    
    path('iec_record/<int:pk>/acknowledge_route/', views.acknowledge_and_route, name='acknowledge_and_route'),
    
    path('iec_record/<int:pk>/submit_notice_pci/', views.submit_notice_pci, name='submit_notice_pci'),

    # path('search/', views.search_record, name='search'),
    
]
