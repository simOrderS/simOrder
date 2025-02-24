from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.template import loader
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from django.db import transaction
from django.db.models import Avg, Sum, Count, Q, F, Min, Max
from django.db.models.functions import Coalesce
from collections import defaultdict, Counter
from decimal import Decimal
from .models import Printer, ProductClass, Product, Menu, Order, ProductOrder, SystemSettings
from .forms import OrderForm, ProductOrderForm, ProductOrderCloseForm, SystemSettingsForm, inlineformset_factory
from .filters import OrderFilter, AdminOrderFilter
from . import printers
import os


def home(request):
    return render(request, 'index.html', {})


@staff_member_required
def admin_orders_all(request):
    combined_orders = ProductOrder.objects.select_related('poOrder').annotate(
        order_id=F('poOrder__id'),
        order_user=F('poOrder__orderUser__username'),
        order_dt_open=F('poOrder__orderDtOpen'),
        order_dt_close=F('poOrder__orderDtClose'),
        order_status=F('poOrder__orderStatus'),
        order_table=F('poOrder__orderTable'),
        order_menu=F('poOrder__menuQuery__menuDescription'),
    ).order_by('-order_id').values(
        'id', 'order_id', 'order_user', 'order_dt_open', 'order_dt_close', 
        'order_status', 'order_table', 'order_menu',
        'poStatus', 'poTransNumber', 'poPayAmount', 'poPayMethod',
        'poDtOpen', 'poDtClose', 'poProdDescription', 'poProdPrice',
        'poProdVAT', 'poProdClass'
    )

    fields = [
        ('order_id', 'Order ID'),
        ('order_user', 'User'),
        ('order_table', 'Table'),
        ('order_menu', 'Menu'),
        ('order_dt_open', 'Order Open'),
        ('order_dt_close', 'Order Close'),
        ('order_status', 'Order Status'),
        ('id', 'PO ID'),
        ('poProdDescription', 'Product'),
        ('poProdPrice', 'Price'),
        ('poProdVAT', 'VAT'),
        ('poProdClass', 'Class'),
        ('poTransNumber', 'Transaction Number'),
        ('poPayAmount', 'Pay Amount'),
        ('poPayMethod', 'Pay Method'),
        ('poDtOpen', 'Product Open'),
        ('poDtClose', 'Product Close'),
        ('poStatus', 'Product Status'),
    ]

    order_filter = AdminOrderFilter(request.GET, queryset=combined_orders)
    filtered_orders = order_filter.qs
    total_revenue = filtered_orders.aggregate(total=Sum('poProdPrice'))['total']

    context = {
        'orders': filtered_orders,
        'fields': fields,
        'filter': order_filter,
        'revenue': total_revenue,
    }
    return render(request, 'admin/admin_orders_all.html', context)


@login_required
def display_orders(request):
    orders = Order.objects.filter(orderStatus=False, orderUser=request.user).order_by('-orderDtClose')
    orders_data = []
    for order in orders:
        product_orders = order.productorder_set.filter(poStatus=0).values('prodQuery__id', 'poProdDescription', 'poProdPrice', 'poProdVAT', 'poProdClass', 
                                                                          'poStatus').annotate(poQty_=Count('id'))
        
        total_price = Decimal('0')
        total_qty = 0
        for product in product_orders:
            total_price += Decimal(str(product['poProdPrice'])) * Decimal(str(product['poQty_']))
            total_qty += product['poQty_']

        orders_data.append({
            'id': order.id,
            'orderUser__username': order.orderUser.username,
            'menuQuery': order.menuQuery.id,
            'menuQuery__menuDescription': order.menuQuery.menuDescription,
            'orderDtClose': order.orderDtClose,
            'orderDtOpen': order.orderDtOpen,
            'orderStatus': order.orderStatus,
            'orderTable': order.orderTable,
            'products': list(product_orders),
            'total': {
                'poProdDescription': 'Total',
                'poProdPrice': total_price,
                'poQty': total_qty,
                'poStatus': None
            }
        })
    context = {
        'orders_products': orders_data,
        'active_menus': Menu.objects.filter(menuActive=True)
    }
    return render(request, 'orders.html', context)


@login_required
def display_orders_all(request):
    f = OrderFilter(request.GET, queryset=Order.objects.exclude(orderStatus=2).order_by('-orderDtClose'))
    return render(request, 'orders_all.html', {'filter': f})


@login_required
def create_order(request, menu_id=None):
    if request.method == 'POST':
        orderForm = OrderForm(request.POST or None, menu_id=menu_id)
        prodOrderForm = ProductOrderForm(request.POST or None, menu_id=menu_id)

        if orderForm.is_valid() and prodOrderForm.is_valid():
            order = orderForm.save(commit=False)
            order.orderUser = request.user
            order.save()

            savedOrder = prodOrderForm.save(order)
            
            if Menu.objects.get(id=menu_id).menuService:
                try:
                    printers.print_order(savedOrder)
                except AssertionError as error:
                    messages.warning(request, str(error))
                    return redirect('urlCreateOrder', menu_id=menu_id)
                return redirect('urlOrders')
            else:
                return redirect('urlCloseOrder', id=order.id)
        
        else:
            for form in [orderForm, prodOrderForm]:
                for field, errors in form.errors.items():
                    if field == '__all__':
                        messages.error(request, errors[0])
                    else:
                        verbose_name = form.fields[field].label or field
                        for error in errors:
                            messages.error(request, f"{verbose_name}: {error}")
    else:
        orderForm = OrderForm(menu_id=menu_id)
        prodOrderForm = ProductOrderForm(menu_id=menu_id)
   
    context = {
        'orderForm': orderForm, 
        'prodOrderForm': prodOrderForm,
    }
    return render(request,'create_order.html', context)


@login_required
def update_order(request, id=None):
    orderInstance = get_object_or_404(Order, id=id)
    menu_id = orderInstance.menuQuery_id

    if request.POST:
        orderForm = OrderForm(request.POST or None, menu_id=menu_id)
        prodOrderForm = ProductOrderForm(request.POST or None, menu_id=menu_id)
        if prodOrderForm.is_valid():
            savedOrder = prodOrderForm.save(orderInstance)
            try:
                printers.print_order(savedOrder)
            except AssertionError as error:
                messages.warning(request, str(error))
                return redirect('urlUpdateOrder', id=orderInstance.id)
            return redirect('urlOrders')
        else:
            for form in [orderForm, prodOrderForm]:
                for field, errors in form.errors.items():
                    if field == '__all__':
                        messages.error(request, errors[0])
                    else:
                        verbose_name = form.fields[field].label or field
                        for error in errors:
                            messages.error(request, f"{verbose_name}: {error}")
    else:
        orderForm = OrderForm(request.POST or None, instance=orderInstance, menu_id=menu_id)
        prodOrderForm = ProductOrderForm(request.POST or None, menu_id=menu_id)

    context = {
        'orderForm': orderForm, 
        'prodOrderForm': prodOrderForm,
    }
    return render(request,'update_order.html', context)


@login_required
def close_order(request, id=None, poTransNumber=None):
    orderInstance = get_object_or_404(Order, id=id)
    menu_id = orderInstance.menuQuery_id

    if request.POST:
        orderForm = OrderForm(request.POST, instance=orderInstance, menu_id=menu_id)
        prodOrderForm = ProductOrderCloseForm(request.POST, instance=orderInstance, trans_number=poTransNumber)
        if orderForm.is_valid() and prodOrderForm.is_valid():
            savedProdOrder = prodOrderForm.save(orderInstance)
            try:
                printers.print_receipt(orderInstance, savedProdOrder)
            except AssertionError as error:
                messages.warning(request, error)
                return redirect('urlCloseOrder', id=orderInstance.id)
            return redirect('urlOrders')
        else:
            for form in [orderForm, prodOrderForm]:
                for field, errors in form.errors.items():
                    if field == '__all__':
                        messages.error(request, errors[0])
                    else:
                        verbose_name = form.fields[field].label or field
                        for error in errors:
                            messages.error(request, f"{verbose_name}: {error}")
    else:
        orderForm = OrderForm(instance=orderInstance, menu_id=menu_id)
        prodOrderForm = ProductOrderCloseForm(instance=orderInstance, trans_number=poTransNumber)

    context = {
        'order': orderInstance,
        'orderForm': orderForm, 
        'prodOrderForm': prodOrderForm,
    }
    return render(request,'close_order.html', context)

    
@login_required
def delete_order(request, id):
    with transaction.atomic():
        order = get_object_or_404(Order, id=id)
        try:
            product_orders = ProductOrder.objects.filter(poOrder=order)
            for product_order in product_orders:
                product = product_order.prodQuery
                product.prodStock += 1
                product.save()

            order.orderStatus = 2
            order.save()
            product_orders.update(poStatus=2)
            messages.success(request, _("Order marked for deletion and stock updated."))
        except Exception as e:
            messages.error(request, _("An error occurred while deleting the order: %(error)s.") % {'error': str(e)})
    return redirect('urlOrdersAll')


@login_required
def delete_order_product(request, id):
    orderproduct = get_object_or_404(ProductOrder, id=id)
    try:
        product = orderproduct.prodQuery
        product.prodStock += 1
        product.save()

        orderproduct.poStatus = 2
        orderproduct.save()
        messages.success(request, _("Product removed from order and stock updated."))
    except Exception as e:
        messages.error(request, _("An error occurred while deleting the product: %(error)s.") % {'error': str(e)})
    return redirect('urlOrdersAll')


@login_required
def printers_view(request):
    listAllUSB = printers.list_all_USB_devices()
    statusBT = printers.statusBTAdapter()
    listBTPaired = printers.list_paired_BT_devices()
    listBTAvailable = None

    if request.method == 'GET' and 'install_USB' in request.GET:
        install = printers.install_USB_printer(request.GET['install_USB'])
        if install:
            messages.success(request, 'Printer successfully installed.')
        else:
            messages.error(request, 'Error! Printer not installed.')
        return redirect('urlPrinters')

    if request.method == 'GET' and 'delete_USB' in request.GET:
        delete = printers.delete_USB_printer(request.GET['delete_USB'])
        if delete:
            messages.success(request, 'Printer successfully deleted.')
        else:
            messages.error(request, 'Error! Printer not deleted.')
        return redirect('urlPrinters')
    
    if request.method == 'GET' and 'toggle_BT' in request.GET:
        toggle_BT = printers.toggleBTAdapter()
        if not toggle_BT:
            messages.error(request, 'Error! Bluetooth could not be activated.')
        return redirect('urlPrinters')
    
    if request.method == 'GET' and 'btnSearchBT' in request.GET:
        listBTAvailable = printers.list_available_BT_devices()
        if not listBTAvailable:
            messages.warning(request, 'No compatible Bluetooth devices found.')
        return render(request, 'printers.html', {'listAllUSB': listAllUSB,
                                              'statusBT': statusBT,
                                              'listBTPaired': listBTPaired,
                                              'listBTAvailable': listBTAvailable,})
    
    if request.method == 'GET' and 'install_BT' in request.GET:
        install = printers.install_BT_printer(request.GET['install_BT'])
        if install:
            messages.success(request, 'Printer successfully installed.')
        else:
            messages.error(request, 'Error! Printer not installed.')
        return redirect('urlPrinters')
    
    if request.method == 'GET' and 'delete_BT' in request.GET:
        delete = printers.delete_BT_printer(request.GET['delete_BT'])
        if delete:
            messages.success(request, 'Printer successfully deleted.')
        else:
            messages.error(request, 'Error! Printer not deleted.')
        return redirect('urlPrinters')
    
    context = {
        'listAllUSB': listAllUSB,
        'statusBT': statusBT,
        'listBTPaired': listBTPaired,
        'listBTAvailable': listBTAvailable,
    }
    return render(request,'printers.html', context)


@staff_member_required
def settings(request):
    settings = SystemSettings.load()  # Load the singleton instance
    if request.method == 'POST':
        form = SystemSettingsForm(request.POST, instance=settings)
        if form.is_valid():
            form.save()
            messages.success(request, _('System settings updated successfully.'))
            if not all([settings.emailUser, settings.emailPassword, settings.emailHost]):
                messages.warning(request, _('Email configuration is incomplete. No system emails will be sent.'))
            
            return redirect('urlSettings')
        else:
            for field, errors in form.errors.items():
                if field == '__all__':
                    messages.error(request, errors[0])
                else:
                    verbose_name = form.fields[field].label or field
                    for error in errors:
                        messages.error(request, f"{verbose_name}: {error}")
    else:
        form = SystemSettingsForm(instance=settings)

    context = {'form': form, }
    return render(request, 'settings.html', context)


@login_required
def power(request, op_id=None):
    if op_id is not None:
        op_id = int(op_id)
        if op_id == 0:
            os.system('sudo shutdown -h now')
            return render(request, 'power.html', {'message': 'System is shutting down...', 'op_id': op_id})
        elif op_id == 1:
            os.system('sudo shutdown -r now')
            return render(request, 'power.html', {'message': 'System is restarting...', 'op_id': op_id})
    
    return render(request, 'power.html', {'op_id': op_id})

