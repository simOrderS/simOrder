from django.db import transaction
from django.core.exceptions import ValidationError
from django.forms import ModelForm, BooleanField, CheckboxInput, IntegerField, \
    ValidationError, IntegerField, inlineformset_factory, PasswordInput, CharField, EmailField, \
    DateInput, DecimalField, NumberInput, ChoiceField
from .models import ProductClass, Product, Menu, Order, ProductOrder, SystemSettings
from django.forms.widgets import CheckboxInput, Select
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
import re, warnings


class ProductClassForm(ModelForm):
    class Meta:
        model = ProductClass
        fields = '__all__'


class OrderForm(ModelForm):
    class Meta:
        model = Order
        exclude = ['orderStatus', 'orderUser', 'prodQuery']

    def __init__(self, *args, **kwargs):
        menu_id = kwargs.pop('menu_id', None)
        super(OrderForm, self).__init__(*args, **kwargs)
        if menu_id:
            selected_menu = Menu.objects.get(id=menu_id, menuActive=True)
            self.fields['menuQuery'].queryset = Menu.objects.filter(id=menu_id, menuActive=True)
            self.fields['orderTable'].initial = selected_menu.menuDescription if not selected_menu.menuService else None
        else:
            self.fields['menuQuery'].queryset = Menu.objects.filter(menuActive=True)

    def clean(self):
        cleaned_data = super().clean()
        order_table = self.cleaned_data.get('orderTable')    
        menu_query = cleaned_data.get('menuQuery')
        if menu_query and menu_query.menuService:
            existing_open_orders = Order.objects.filter(orderTable=order_table, orderStatus=0).exclude(pk=self.instance.pk if self.instance.pk else None)
            if existing_open_orders.exists():
                raise ValidationError(_("An open order already exists for table %(table)s."), params={'table': order_table})

        return cleaned_data


class ProductOrderForm(ModelForm):
    class Meta:
        model = ProductOrder
        fields = []

    def __init__(self, *args, **kwargs):
        menu_id = kwargs.pop('menu_id', None)
        super(ProductOrderForm, self).__init__(*args, **kwargs)

        if menu_id:
            products = Product.objects.filter(menu__id=menu_id).distinct()
        else:
            products = Product.objects.filter(menu__menuActive=True).distinct()
        
        for prod in products:
            field_name = f'prodQuery_{prod.id}'
            self.fields[field_name] = IntegerField(initial=0, min_value=0, step_size=1, 
                                                   label=prod.prodDescription, required=False)
            self.fields[field_name].product = prod
            self.fields[field_name].prodClass = prod.prodclassQuery

    def clean(self):
        cleaned_data = super().clean()
        if not self.has_changed():
            raise ValidationError(_("Order has no changes."))
        
        for key, value in cleaned_data.items():
            if value > 0:
                id = int(re.search(r'prodQuery_(\d+)', key).group(1))
                product = Product.objects.get(pk=id)
                if product.prodStock < value:
                    raise ValidationError(f"Not enough stock for {product.prodDescription}. Available: {product.prodStock}")
        
        return cleaned_data

    def save(self, orderInstance, commit=True):
        product_orders = []
        for key, value in self.cleaned_data.items():
            if value > 0:
                id = int(re.search(r'prodQuery_(\d+)', key).group(1))
                prodQuery_ = Product.objects.get(pk=id)
                prodQuery_.prodStock -= value
                if commit:
                    prodQuery_.save()

                product_orders.append({
                    'poOrder': orderInstance,
                    'prodQuery': prodQuery_,
                    'poQty': value,
                    'poStatus': 0,
                })
                for i in range(value):
                    prodOrderInstance = ProductOrder(poOrder = orderInstance, prodQuery = prodQuery_, poStatus = 0)
                    if commit:
                        prodOrderInstance.save()
        return product_orders


class ProductOrderCloseForm(ModelForm):
    class Meta:
        model = ProductOrder
        fields = []

    def __init__(self, *args, **kwargs):
        self.trans_number = kwargs.pop('trans_number', None)
        super(ProductOrderCloseForm, self).__init__(*args, **kwargs)
        
        product_orders = ProductOrder.objects.filter(poOrder=self.instance).exclude(poStatus=2)
        if self.trans_number:
            product_orders = product_orders.filter(poTransNumber=self.trans_number)
        product_orders = product_orders.distinct()

        for prod in product_orders:
            field_name = f'poStatus_{prod.id}'

            self.fields[field_name] = BooleanField(
                required = False,
                label = prod.prodQuery.prodDescription,
                widget = CheckboxInput(attrs = {'class': 'form-check-input'})
            )
            self.fields[field_name].prodInstance = prod
        
        if self.instance:
            self.fields['poPayAmount_'] = DecimalField(
                label=_('Payed amount'),
                max_digits = 6,
                decimal_places = 2,
                required = True,
            )
            self.fields['poPayMethod_'] = ChoiceField(
                choices = [('CH', 'Cash'), ('DC', 'Debit card'), ('CC', 'Credit card'),],
                required = True,
                widget = Select(attrs = {'class': 'form-control'})
            )
            self.fields['poPayAmount_'].initial = product_orders[0].poPayAmount if product_orders[0].poPayAmount else self.instance.get_total_order - self.instance.get_total_closed
            self.fields['poPayMethod_'].initial = product_orders[0].poPayMethod if product_orders[0].poPayMethod else None
        
    def has_changed(self):
        changed_data = super().changed_data
        ignored_fields = ['poPayAmount_', 'poPayMethod_']
        return any(field for field in changed_data if field not in ignored_fields)
    
    def clean(self):
        cleaned_data = super().clean()
        if not self.has_changed():
            raise ValidationError(_("Order has no changes."))
        return cleaned_data

    def save(self, orderInstance, commit=True):
        if not orderInstance.orderStatus:
            if all(value for key, value in self.cleaned_data.items() if key.startswith('poStatus_')):
                orderInstance.orderStatus = True
                orderInstance.orderDtClose = timezone.now()
                orderInstance.save()

            transaction_number = ProductOrder().generate_transNumber()
            product_orders = []
            loop = 1
            for key, value in self.cleaned_data.items():
                if key.startswith('poStatus_'):
                    id = int(re.search(r'poStatus_(\d+)', key).group(1))
                    try:
                        product_order = ProductOrder.objects.get(pk=id, poOrder=orderInstance)
                        new_status = 1 if value else 0
                        if product_order.poStatus != new_status:
                            product_order.poStatus = new_status
                            product_order.poTransNumber = transaction_number
                            product_order.poPayAmount = self.cleaned_data.get('poPayAmount_') if loop == 1 else 0
                            loop += loop
                            product_order.poPayMethod = self.cleaned_data.get('poPayMethod_')
                            product_order.poDtClose = timezone.now()
                            if commit:
                                product_order.save()
                            product_orders.append(product_order)
                    except ProductOrder.DoesNotExist:
                        raise ValidationError(_("Error closing the order - Product does not exist!"))

            return product_orders
        else:
            return ProductOrder.objects.filter(poOrder=orderInstance, poTransNumber=self.trans_number)


class SystemSettingsForm(ModelForm):
    class Meta:
        model = SystemSettings
        fields = '__all__'

    emailUser = EmailField()
    emailPassword = CharField(widget = PasswordInput())
    
    def __init__(self, *args, **kwargs):
        super(SystemSettingsForm, self).__init__(*args, **kwargs)
        #self.fields['taxRate'].widget.attrs.update({'step': '0.01'})
        self.fields['emailUser'].label = _("Email User")
        self.fields['emailPassword'].label = _("Password")
        self.fields['emailHost'].help_text = mark_safe(_('<a href="https://www.google.com/search?q=how+to+get+the+SMTP+address+of+my+email+provider" \
                                                         target="_blank">Find your SMTP server address</a>. Most email providers require \
                                                         special configuration to allow programattically email sending.'))



        



