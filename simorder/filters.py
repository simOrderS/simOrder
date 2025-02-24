import django_filters
from .models import Order, Menu
from .forms import DateInput
from django.contrib.auth import get_user_model
from django.db import models
from django_filters.widgets import RangeWidget
from django.utils import timezone
from datetime import timedelta

class OrderFilter(django_filters.FilterSet):
    class Meta:
        model = Order
        fields = {
            'orderUser': ['exact'],
            'orderDtClose': ['gt'],
            'orderStatus': ['exact'],
            }
        filter_overrides = {
            models.DateTimeField: {
                'filter_class': django_filters.DateFilter,
                'extra': lambda f: {
                    'widget': DateInput(attrs={'type': 'date'}),
                },
            },
        }


class AdminOrderFilter(django_filters.FilterSet):
    order_user = django_filters.ModelChoiceFilter(
        queryset=get_user_model().objects.filter(order__isnull=False).distinct(),
        lookup_expr='icontains',
        label='User'
        )
    order_dt_close = django_filters.DateFromToRangeFilter(
        widget=RangeWidget(attrs={'type': 'date', 'class': 'form-control'}),
        label='Order closed range'
    )
    order_status = django_filters.MultipleChoiceFilter(
        choices=((0, 'Open'), (1, 'Closed'), (2, 'Cancelled')),
        label='Order status',
    )    
    menu = django_filters.ModelChoiceFilter(
        queryset=Menu.objects.all(),
        label='Menu',
        field_name='order_menu',
        to_field_name='id'
    )
    poProdDescription = django_filters.CharFilter(lookup_expr='icontains', label='Product')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.form.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

    class Meta:
        fields = ['order_user', 'order_dt_close', 'order_status', 'menu', 'poProdDescription']

