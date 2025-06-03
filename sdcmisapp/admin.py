from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

# Register your models here.

from . models import iec_records, CustomUser

class CustomUserAdmin(BaseUserAdmin):
    # Add 'role', 'location', 'designation' to the fieldsets for editing users
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role', 'location', 'designation')}),
    )
    # Add 'role', 'location', 'designation' to the add_fieldsets for creating users
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('role', 'location', 'designation', 'first_name', 'last_name', 'email')}), # Ensure all necessary fields are here for creation
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'role', 'location', 'designation')
    search_fields = BaseUserAdmin.search_fields + ('role', 'location', 'designation')
    list_filter = BaseUserAdmin.list_filter + ('role', 'location', 'is_active') # Add is_active for filtering

    actions = ['approve_selected_users']

    def approve_selected_users(self, request, queryset):
        queryset.update(is_active=True)
        self.message_user(request, f"{queryset.count()} selected users have been approved and activated.")
    approve_selected_users.short_description = "Approve selected users"

admin.site.register(iec_records)
admin.site.register(CustomUser, CustomUserAdmin)
