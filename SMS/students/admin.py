from django.contrib import admin
from .models import Student, Parent


# ----------------------------
# Student Admin
# ----------------------------
@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'admission_number',
        'roll_number',
        'section',
        'branch',
        'phone_number',
        'is_active',
        'enrollment_date',
    )

    list_filter = (
        'is_active',
        'gender',
        'section__class_obj__branch',
        'section',
        'enrollment_date',
    )

    search_fields = (
        'first_name',
        'last_name',
        'admission_number',
        'roll_number',
        'phone_number',
        'email',
    )

    readonly_fields = (
        'admission_number',
        'created_at',
        'updated_at',
    )

    autocomplete_fields = ('section', 'created_by', 'user')

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "admission_number",
                "roll_number",
                "first_name",
                "last_name",
                "father_name",
                "mother_name",
                "date_of_birth",
                "gender",
                "profile_picture",
            )
        }),
        ("Contact Information", {
            "fields": (
                "phone_number",
                "alternate_phone",
                "email",
                "address",
                "city",
                "postal_code",
            )
        }),
        ("Academic Information", {
            "fields": (
                "section",
                "enrollment_date",
                "is_active",
            )
        }),
        ("Medical & Emergency", {
            "fields": (
                "blood_group",
                "medical_conditions",
                "emergency_contact_name",
                "emergency_contact_phone",
            )
        }),
        ("System Information", {
            "fields": (
                "user",
                "created_by",
                "created_at",
                "updated_at",
            )
        }),
    )


# ----------------------------
# Parent Admin
# ----------------------------
@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'relationship',
        'phone_number',
        'email',
        'is_active',
    )

    list_filter = (
        'relationship',
        'is_active',
        'city',
    )

    search_fields = (
        'first_name',
        'last_name',
        'phone_number',
        'email',
    )

    filter_horizontal = ('students',)

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    autocomplete_fields = ('created_by', 'user')

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "first_name",
                "last_name",
                "relationship",
                "profile_picture",
            )
        }),
        ("Contact Information", {
            "fields": (
                "phone_number",
                "alternate_phone",
                "email",
            )
        }),
        ("Address & Details", {
            "fields": (
                "occupation",
                "qualification",
                "address",
                "city",
            )
        }),
        ("Students", {
            "fields": ("students",)
        }),
        ("System Info", {
            "fields": (
                "user",
                "created_by",
                "is_active",
                "created_at",
                "updated_at",
            )
        }),
    )
