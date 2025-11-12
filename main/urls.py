
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('', views.main, name='main'),
    path('addtobalance', views.addtobalance, name='addtobalance'),
    path('outbalance', views.outbalance, name='outbalance'),
    path('activities', views.activities, name='activities'),
    path('createactivity', views.createactivity, name='createactivity'),
    path('updateactiv', views.updateactiv, name='updateactiv'),
    path('getsource', views.getsource, name='getsource'),
    path('adjustsold', views.adjustsold, name='adjustsold'),
    path('updatesleeptime', views.updatesleeptime, name='updatesleeptime'),
    path('updatewaketime', views.updatewaketime, name='updatewaketime'),
    path('addevents', views.addevents, name='addevents'),
    path('tree', views.tree, name='tree'),
    path('get_board_data/', views.get_board_data, name='get_board_data'),
    path('save_board/', views.save_board, name='save_board'),
    path('quran', views.quran, name='quran'),
    path('lastnodeid', views.lastnodeid, name='lastnodeid'),
    path("create_node/", views.create_node, name="create_node"),
    path("update_node/<int:node_id>/", views.update_node_position, name="update_node"),
    path('create_connection/', views.create_connection, name='create_connection'),
    path('update_connection/', views.update_connection, name='update_connection'),
    path('getnodedata', views.getnodedata, name='getnodedata'),
    path('updatenode', views.updatenode, name='updatenode'),
    path('updatelabel', views.updatelabel, name='updatelabel'),
    # path('addtobalance', views.addtobalance, name='addtobalance'),
    # path('addtobalance', views.addtobalance, name='addtobalance'),
    # path('addtobalance', views.addtobalance, name='addtobalance'),
    # path('addtobalance', views.addtobalance, name='addtobalance'),
    # path('addtobalance', views.addtobalance, name='addtobalance'),
    # path('addtobalance', views.addtobalance, name='addtobalance'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
