
from django.urls import path
from . import views, nodeviews
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
    path('quran', views.quran, name='quran'),
    path('get_board_data/', nodeviews.get_board_data, name='get_board_data'),
    path('save_board/', nodeviews.save_board, name='save_board'),
    path('lastnodeid', nodeviews.lastnodeid, name='lastnodeid'),
    path("create_node/", nodeviews.create_node, name="create_node"),
    path("update_node/<int:node_id>/", nodeviews.update_node_position, name="update_node"),
    path('create_connection/', nodeviews.create_connection, name='create_connection'),
    path('update_connection/', nodeviews.update_connection, name='update_connection'),
    path('getnodedata', nodeviews.getnodedata, name='getnodedata'),
    path('updatenode', nodeviews.updatenode, name='updatenode'),
    path('updatelabel', nodeviews.updatelabel, name='updatelabel'),
    # path('addtobalance', views.addtobalance, name='addtobalance'),
    # path('addtobalance', views.addtobalance, name='addtobalance'),
    # path('addtobalance', views.addtobalance, name='addtobalance'),
    # path('addtobalance', views.addtobalance, name='addtobalance'),
    # path('addtobalance', views.addtobalance, name='addtobalance'),
    # path('addtobalance', views.addtobalance, name='addtobalance'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
