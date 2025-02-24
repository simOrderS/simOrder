from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import random


class Printer(models.Model):
    printName = models.CharField(max_length=255, verbose_name=_('Printer'), unique=True, null=True)
    printType = models.CharField(max_length=25)
    printIdVendor = models.PositiveIntegerField(null=True)
    printIdProduct = models.PositiveIntegerField(null=True)
    printIn_ep = models.PositiveIntegerField(null=True)
    printOut_ep = models.PositiveIntegerField(null=True)
    printMacAddress = models.CharField(max_length=17, null=True)

    class Meta:
        ordering = ['printName']

    def __str__(self):
        return self.printName


class ProductClass(models.Model):
    classDescription = models.CharField(verbose_name=_('Description'), max_length=255, unique=True)
    classColor = models.CharField(verbose_name=_('Display color'), max_length=7, default='#0d6efd')
    printQuery = models.ForeignKey(Printer, verbose_name=_('Order Printer'), on_delete=models.SET_NULL, blank=True, null=True)
    isActive = models.BooleanField(verbose_name=_('Active?'), default=True)

    class Meta:
        verbose_name = _('Product Class')
        verbose_name_plural = _('Product Classes')

    def __str__(self):
        return self.classDescription


class Product(models.Model):
    prodclassQuery = models.ForeignKey(ProductClass, verbose_name=_('Product Class'), on_delete=models.PROTECT, default=1)
    prodDescription = models.CharField(verbose_name=_('Product'), max_length=255)
    prodStock = models.DecimalField(verbose_name=_('Stock'), max_digits=6, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])
    prodPrice = models.DecimalField(verbose_name=_('Price'), max_digits=6, decimal_places=2, default=0.00, validators=[MinValueValidator(0)])
    prodVAT = models.DecimalField(verbose_name=_('VAT (%)'), max_digits=5, decimal_places=2, default=0.00, validators=[MinValueValidator(0), MaxValueValidator(100)])
    isActive = models.BooleanField(verbose_name=_('Active?'), default=True)

    class Meta:
        ordering = ['prodclassQuery', 'prodDescription']

    def __str__(self):
        return self.prodDescription


class Menu(models.Model):
    menuActive = models.BooleanField(verbose_name=_('Active?'), default=False)
    menuService = models.BooleanField(verbose_name=_('Table Service?'), default=False)
    menuDescription = models.CharField(max_length=255, verbose_name=_('Menu'))
    prodQuery = models.ManyToManyField(Product, verbose_name=_('Product'))
    printQuery = models.ForeignKey(Printer, verbose_name=_('Receipt Printer'), on_delete=models.SET_NULL, blank=True, null=True)
    isActive = models.BooleanField(verbose_name=_('Active?'), default=True)

    class Meta:
        ordering = ['menuDescription']
    
    def __str__(self):
        return self.menuDescription


class Order(models.Model):
    orderUser = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    orderDtOpen = models.DateTimeField(auto_now_add=True)
    orderDtClose = models.DateTimeField(auto_now=True)
    orderStatus = models.IntegerField(default=0, verbose_name=_('Order Status')) #0: open, 1: closed, 2: cancelled/ deleted
    orderTable = models.CharField(max_length=25, verbose_name=_('Table'))
    menuQuery = models.ForeignKey(Menu, on_delete=models.PROTECT, verbose_name=_('Menu'), default=1)
    prodQuery = models.ManyToManyField(Product, through='ProductOrder')
        
    def save_model(self, request, obj, form, change):
        obj.orderuser = request.user
        super().save_model(request, obj, form, change)

    @property
    def get_total_order(self):
        return ProductOrder.get_total_order(self)
    
    @property
    def get_total_closed(self):
        return ProductOrder.get_total_closed(self)


class ProductOrder(models.Model):
    poOrder = models.ForeignKey(Order, on_delete=models.CASCADE, verbose_name=_('Order'), default=1)
    poStatus = models.IntegerField(default=0, verbose_name=_('Product Order Status')) #0: open, 1: closed, 2: cancelled/ deleted
    prodQuery = models.ForeignKey(Product, on_delete=models.SET_NULL, verbose_name=_('Product'), default=1, null=True)
    poTransNumber = models.CharField(max_length=20, verbose_name=_('Transaction Number'), blank=True)
    poPayAmount = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    poPayMethod = models.CharField(max_length=2, choices=[('CH', _('Cash')), ('DC', _('Debit card')), ('CC', _('Credit card'))], blank=True)
    poDtOpen = models.DateTimeField(auto_now_add=True)
    poDtClose = models.DateTimeField(auto_now=True)

    # Additional fields for hardcopy product information
    poProdDescription = models.CharField(max_length=255)
    poProdPrice = models.DecimalField(max_digits=6, decimal_places=2)
    poProdVAT = models.DecimalField(max_digits=5, decimal_places=2)
    poProdClass = models.CharField(max_length=255)

    def save(self, *args, **kwargs):
            if self.prodQuery and not self.id:
                self.poProdDescription = self.prodQuery.prodDescription
                self.poProdPrice = self.prodQuery.prodPrice
                self.poProdVAT = self.prodQuery.prodVAT
                self.poProdClass = self.prodQuery.prodclassQuery.classDescription
            super().save(*args, **kwargs)

    def generate_transNumber(self):
        while True:
            year = timezone.now().year
            random_number = random.randint(1, 999999999)
            last_two_digits = self.generate_suffix(random_number)
            transaction_number = f"{year}-{random_number:09d}-{last_two_digits:02d}"

            if not ProductOrder.objects.filter(poTransNumber=transaction_number).exists():
                return transaction_number

    def generate_suffix(self, random_number):
        return sum(int(digit) for digit in str(random_number)) % 100
    
    @classmethod
    def get_total_order(cls, order):
        return cls.objects.filter(poOrder=order).exclude(poStatus=2).aggregate(total=models.Sum('poProdPrice'))['total'] or 0

    @classmethod
    def get_total_closed(cls, order):
        return cls.objects.filter(poOrder=order, poStatus=1).aggregate(total=models.Sum('poProdPrice'))['total'] or 0

class SingletonModel(models.Model):
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SystemSettings(SingletonModel):
    companyName = models.CharField(max_length=255, verbose_name=_('Company Name'), blank=True)
    companyAdress1 = models.CharField(max_length=255, verbose_name=_('Address'), blank=True)
    companyAdress2 = models.CharField(max_length=255, verbose_name=_('Zip, City'), blank=True)
    companyInfo1 = models.CharField(max_length=255, verbose_name=_('Add. Information 1'), blank=True)
    companyInfo2 = models.CharField(max_length=255, verbose_name=_('Add. Information 2'), blank=True)
    taxIdNumber = models.CharField(max_length=255, verbose_name=_('Tax Number'), blank=True)
    emailHost = models.CharField(max_length=255, verbose_name=_('Email Host'), blank=True)
    emailUser = models.CharField(max_length=255, verbose_name=_('Email User'), blank=True)
    emailPassword = models.CharField(max_length=255, verbose_name=_('Password'), blank=True)

    def __str__(self):
        return "System Settings"
