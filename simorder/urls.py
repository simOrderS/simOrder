from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='urlHome'),
    path('orders/', views.display_orders, name='urlOrders'),
    path('orders/all', views.display_orders_all, name='urlOrdersAll'),
    path('orders/create/<int:menu_id>', views.create_order, name='urlCreateOrder'),
    path('orders/update/<int:id>', views.update_order, name='urlUpdateOrder'),
    path('orders/close/<int:id>', views.close_order, name='urlCloseOrder'),    
    path('orders/close/<int:id>/<str:poTransNumber>', views.close_order, name='urlReprintOrder'),    
    path('orders/delete/<int:id>', views.delete_order, name='urlDeleteOrder'),
    path('orders/delete/orderproduct/<int:id>', views.delete_order_product, name='urlDeleteOrderProduct'),
    path('orders/admin/all', views.admin_orders_all, name='urlAdminOrdersAll'),
    path('printers/', views.printers_view, name='urlPrinters'),    
    path('settings/', views.settings, name='urlSettings'),    
    path('power/<int:op_id>', views.power, name='urlPower'),
]