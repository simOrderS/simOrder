from .models import ProductClass, Menu, Product, SystemSettings
from .email_backend import DatabaseEmailBackend
from django.urls import path, reverse
from django.utils.text import capfirst
from django.utils.encoding import force_bytes
from django.utils.html import format_html
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from django.forms import BooleanField, SplitDateTimeField, ModelMultipleChoiceField, SelectMultiple, ChoiceField, DecimalField
from django.apps import apps
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.core.mail import EmailMessage
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db.models.deletion import ProtectedError
from django.contrib import admin, messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator


class CustomAdminSite(admin.AdminSite):
    site_header = "Custom Admin Site"
    site_title = "Custom Admin"
    index_title = "Welcome to the Custom Admin"

    def index(self, request, extra_context=None):
        app_list = self.get_app_list(request)
        context = {
            **self.each_context(request),
            'title': self.index_title,
            'app_list': app_list,
            **(extra_context or {}),
        }
        request.current_app = self.name

        return TemplateResponse(request, "admin/admin_list.html", context)

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request)
        model_ordering = {"Users": 1, "Groups": 2, "Product Classes": 3, "Products": 4, "Menus": 5}

        for app in app_list:
            app['models'].sort(key=lambda x: model_ordering.get(x['name'], len(model_ordering)))

            for model in app['models']:
                # Get the model class
                model_class = apps.get_model(app['app_label'], model['object_name'])

                # Get the admin instance for this model
                model_admin = self._registry.get(model_class)

                # Use the list_display from the ModelAdmin
                list_display = model_admin.get_list_display(request)

                # Include verbose names for list_display fields
                model['list_display'] = []
                for field_name in list_display:
                    try:
                        field = model_class._meta.get_field(field_name)
                        verbose_name = field.verbose_name
                        model['list_display'].append({
                            'name': field_name,
                            'verbose_name': capfirst(str(verbose_name))
                        })
                    except FieldDoesNotExist:
                        # Skip non-field attributes like __str__
                        continue
                
                # Retrieve all objects for this model with prefetching if needed
                m2m_fields = [field.name for field in model_class._meta.many_to_many]
                if m2m_fields:
                    model['all_objects'] = list(model_class.objects.prefetch_related(*m2m_fields).all())
                else:
                    model['all_objects'] = list(model_class.objects.all())

                # Set verbose name for the model
                model['verbose_name'] = str(model_class._meta.verbose_name)
                model['verbose_name_plural'] = str(model_class._meta.verbose_name_plural)

                # Ensure 'name' key exists for models
                model['name'] = model.get('name', str(model_class._meta.verbose_name))

                # Add 'model_name' for URL reversing
                model['model_name'] = model_class._meta.model_name

                # Add permissions
                model['perms'] = {
                    'add': request.user.has_perm(f"{app['app_label']}.add_{model['model_name']}"),
                    'change': request.user.has_perm(f"{app['app_label']}.change_{model['model_name']}"),
                    'delete': request.user.has_perm(f"{app['app_label']}.delete_{model['model_name']}"),
                    'view': request.user.has_perm(f"{app['app_label']}.view_{model['model_name']}"),
                }

                # Add URLs
                info = (app['app_label'], model['model_name'])
                model['admin_url'] = reverse('admin:%s_%s_changelist' % info)
                #model['add_url'] = reverse('admin:%s_%s_add' % info)

        return app_list

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('auth/', self.admin_view(self.custom_admin_view), name='custom_auth'),
            path('simorder/', self.admin_view(self.custom_admin_view), name='custom_simorder'),
            path('<str:app_label>/<str:model_name>/<int:object_id>/change/', self.admin_view(self.custom_admin_view), name='custom_change'),
            path('<str:app_label>/<str:model_name>/add', self.admin_view(self.custom_admin_view), name='custom_add'),
            path('<str:app_label>/<str:model_name>/<int:object_id>/delete/', self.admin_view(self.custom_admin_view), name='custom_delete'),
            # For password reset:
            path('<str:app_label>/<str:model_name>/<int:object_id>/password/', self.admin_view(self.custom_admin_view), name='admin_password_reset'),
            path('password_reset/', self.custom_password_reset, name='login_password_reset'),
            path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
            path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
            path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
        ]
        return custom_urls + urls

    def custom_admin_view(self, request, app_label=None, model_name=None, object_id=None):
        app_list = self.get_app_list(request)
        if 'auth' in request.path:
            filtered_app_list = [item for item in app_list if item['name'] == "Authentication and Authorization"]
        elif 'simorder' in request.path:
            filtered_app_list = [item for item in app_list if item['name'] == "MasterData"]
        else:
            filtered_app_list = app_list

        for app in filtered_app_list:
            for model in app['models']:
                model_class = apps.get_model(app['app_label'], model['object_name'])
                m2m_fields = [field.name for field in model_class._meta.many_to_many]
                model_records = list(model_class.objects.prefetch_related(*m2m_fields).all())
                obj = model_records
                model['all_objects'] = model_records
        
        context = {
            'app_list': filtered_app_list,
            **self.each_context(request),
        }

        if 'add' in request.path and not object_id:
            model_info = next((m for a in filtered_app_list for m in a['models'] if m['model_name'] == model_name), None)
            model_class = apps.get_model(app['app_label'], model_info['object_name'])
            obj = model_class()
            form_class = self._registry[model_class].get_form(request)
            all_products = Product.objects.all()

            if request.method == 'POST':
                form = form_class(request.POST)
                if form.is_valid():
                    if model_info['model_name'] == 'menu':
                        obj = form.save(commit=False)
                        obj.save()
                        prod_query_data = form.cleaned_data.get('prodQuery')
                        if prod_query_data:
                            obj.prodQuery.set(prod_query_data)
                    else:
                        form.save()
                    return redirect(f"{filtered_app_list[0].get('app_url')}?tab={request.GET.get('tab', 0)}")
                else:
                    print(form.errors, form.non_field_errors())
            else:
                form = form_class()

            context.update({
                'object': obj,
                'adminform': form,
                'model_info': model_info,
                'all_products': all_products,
            })

            return TemplateResponse(request, "admin/admin_change.html", context)

        elif 'change' in request.path and object_id:
            model_info = next((m for a in filtered_app_list for m in a['models'] if m['model_name'] == model_name), None)
            model_class = apps.get_model(app['app_label'], model_info['object_name'])
            obj = get_object_or_404(model_class, id=object_id)
            form_class = self._registry[model_class].get_form(request, obj=obj)

            all_products = Product.objects.all()

            if request.method == 'POST':
                form = form_class(request.POST, instance=obj)
                if form.is_valid():
                    form.save()
                    return redirect(f"{filtered_app_list[0].get('app_url')}?tab={request.GET.get('tab', 0)}")
                else:
                    for field, errors in form.errors.items():
                        if field == '__all__':
                            messages.error(request, errors[0])
                        else:
                            verbose_name = form.fields[field].label or field
                            for error in errors:
                                messages.error(request, f"{verbose_name}: {error}")
            else:
                form = form_class(instance=obj)

            context.update({
                'object': obj,
                'adminform': form,
                'model_info': model_info,
                'all_products': all_products,
            })

            return TemplateResponse(request, "admin/admin_change.html", context)
        
        elif 'delete' in request.path and object_id:
            model_info = next((m for a in filtered_app_list for m in a['models'] if m['model_name'] == model_name), None)
            model_class = apps.get_model(app['app_label'], model_info['object_name'])

            try:
                obj = get_object_or_404(model_class, id=object_id)
                obj.delete()
                messages.success(request, _("%(obj)s successfully deleted.") % {'obj': obj})
            except ProtectedError as error:
                messages.error(request, _("%(obj)s cannot be deleted because it is linked to %(rel_obj)s.") % \
                               {'obj': obj, 'rel_obj': ", ".join([str(product) for product in error.protected_objects])})
            except FieldDoesNotExist as error:
                #print(type(error).__name__, error)
                messages.error(request, error)
            
            return redirect(f"{filtered_app_list[0].get('app_url')}?tab={request.GET.get('tab', 0)}")

        elif 'password' in request.path and object_id:
            model_info = next((m for a in filtered_app_list for m in a['models'] if m['model_name'] == model_name), None)
            model_class = apps.get_model(app['app_label'], model_info['object_name'])
            user = get_object_or_404(model_class, id=object_id)
            token = default_token_generator.make_token(user)
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            
            reset_url = reverse('admin:password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})
            
            return redirect(reset_url)
        
        return TemplateResponse(request, "admin/admin_list.html", context)

    def custom_password_reset(self, request):
        email_config = SystemSettings.objects.first()
        if not all([email_config.emailHost, email_config.emailUser, email_config.emailPassword]):
            messages.error(request, _("Unable to send password recovery email. System configuration incomplete."))
            return render(request, 'registration/password_reset_form.html')
        
        if request.method == 'POST':
            form = PasswordResetForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email']
                user = next(form.get_users(email), None)
                if user:
                    token = default_token_generator.make_token(user)
                    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                    reset_url = request.build_absolute_uri(reverse('password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token}))
                    try:
                        email_message = EmailMessage(
                            subject = _('Password Reset'),
                            body = _('Click here to reset your password: {}').format(reset_url),
                            from_email = email_config.emailUser,
                            to = [email],
                            connection = DatabaseEmailBackend()
                        )
                        email_message.send()
                        return redirect('password_reset_done')
                    
                    except Exception as e:
                        messages.error(request, _("Failed to send email: {}").format(str(e)))
                else:
                    messages.error(request, _("No user found with that email address."))
        else:
            form = PasswordResetForm()

        return render(request, 'registration/password_reset_form.html', {'form': form})


custom_admin_site = CustomAdminSite(name='customadmin')


class ProductClassAdmin(admin.ModelAdmin):
    list_display = ['classDescription', 'classColor', 'printQuery']
    exclude = ['isActive']
    list_display_links = ['classDescription']
    ordering = ['classDescription']

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj=obj, **kwargs)
        for field in form.base_fields:
            form.base_fields[field].widget.attrs.update({'class': 'form-control'})

        return form
 

class ProductAdmin(admin.ModelAdmin):
    list_display = ['prodclassQuery', 'prodDescription', 'prodStock', 'prodPrice', 'prodVAT']
    exclude = ['isActive']
    ordering = ['prodclassQuery', 'prodDescription']

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj=obj, **kwargs)
        for field in form.base_fields:
            form.base_fields[field].widget.attrs.update({'class': 'form-control'})

        form.base_fields['prodclassQuery'].widget.can_add_related = False
        form.base_fields['prodclassQuery'].widget.can_change_related = False
        form.base_fields['prodclassQuery'].widget.can_delete_related = False
        form.base_fields['prodclassQuery'].widget.can_view_related = False
        form.base_fields['prodPrice'].help_text = _("Including VAT.")
        form.base_fields['prodVAT'].help_text = _("e.g.: 19 for 19%.")

        return form


class MenuAdmin(admin.ModelAdmin):
    list_display = ['menuActive', 'menuService', 'printQuery', 'menuDescription', ]
    exclude = ['isActive']

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj=obj, **kwargs)
        for key in form.base_fields.keys():
            field = form.base_fields[key]
            if isinstance(field, BooleanField):
                field.widget.attrs.update({'class': 'form-check-input ms-1'})
            else:
                field.widget.attrs.update({'class': 'form-control'})

        form.base_fields['menuActive'].help_text = _("Set as active to display all listed products on (new) order form.")
        form.base_fields['menuService'].help_text = _("Set as active to generate an order to the kitchen. Set as not active for counter service, for example.")
        form.base_fields['prodQuery'].help_text = None

        return form


class UserAdmin(BaseUserAdmin):
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj=obj, **kwargs)
        try:
            for key in form.base_fields.keys():
                field = form.base_fields[key]
                if isinstance(field, BooleanField):
                    field.widget.attrs.update({'class': 'form-check-input ms-1'})
                elif isinstance(field, SplitDateTimeField):
                    field.widget.attrs.update({'class': 'form-control', 'readonly': 'readonly'})
                elif isinstance(field, ModelMultipleChoiceField):
                    field.widget = SelectMultiple(attrs={'type': 'checkbox', 'class': 'form-select', 'multiple': 'multiple'})
                elif isinstance(field, ChoiceField):
                    field.widget.attrs.update({'class': 'form-check-control', 'readonly': 'readonly'})
                else:
                    field.widget.attrs.update({'class': 'form-control'})
        except Exception as e:
            print(f"Error in get_form: {e}") # Avoid error if field is not available based on selected "fieldset"

        return form


class GroupAdmin(BaseGroupAdmin):
    list_display = ['name']

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj=obj, **kwargs)
        try:
            for key in form.base_fields.keys():
                field = form.base_fields[key]
                if isinstance(field, BooleanField):
                    field.widget.attrs.update({'class': 'form-check-input ms-1'})
                elif isinstance(field, SplitDateTimeField):
                    field.widget.attrs.update({'class': 'form-control', 'readonly': 'readonly'})
                elif isinstance(field, ModelMultipleChoiceField):
                    field.widget = SelectMultiple(attrs={'type': 'checkbox', 'class': 'form-select', 'multiple': 'multiple'})
                elif isinstance(field, ChoiceField):
                    field.widget.attrs.update({'class': 'form-check-control', 'readonly': 'readonly'})
                else:
                    field.widget.attrs.update({'class': 'form-control'})
        except Exception as e:
            print(f"Error in get_form: {e}") # Avoid error if field is not available based on selected "fieldset"

        return form


custom_admin_site.register(ProductClass, ProductClassAdmin)
custom_admin_site.register(Menu, MenuAdmin)
custom_admin_site.register(Product, ProductAdmin)

admin.site.unregister(User)
custom_admin_site.register(User, UserAdmin)

admin.site.unregister(Group)
custom_admin_site.register(Group, GroupAdmin)
