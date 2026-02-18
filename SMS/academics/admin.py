from django.contrib import admin
from .models import Class, Section, Subject, SectionSubject


# ----------------------------
# Section Inline (Inside Class)
# ----------------------------
class SectionInline(admin.TabularInline):
    model = Section
    extra = 0
    fields = ('name', 'code', 'capacity', 'room_number', 'is_active')
    readonly_fields = ('code',)
    show_change_link = True


# ----------------------------
# Class Admin
# ----------------------------
@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'code',
        'branch',
        'numeric_level',
        'is_active',
        'get_section_count',
    )

    list_filter = (
        'branch',
        'is_active',
    )

    search_fields = (
        'name',
        'code',
        'branch__name',
    )

    readonly_fields = (
        'code',
        'created_at',
        'updated_at',
    )

    autocomplete_fields = ('branch', 'created_by')

    inlines = [SectionInline]


# ----------------------------
# Section Admin
# ----------------------------
@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'class_obj',
        'branch',
        'capacity',
        'is_active',
        'get_subject_count',
    )

    list_filter = (
        'class_obj__branch',
        'class_obj',
        'is_active',
    )

    search_fields = (
        'name',
        'code',
        'class_obj__name',
    )

    readonly_fields = (
        'code',
        'created_at',
        'updated_at',
    )

    autocomplete_fields = ('class_obj', 'created_by')


# ----------------------------
# Subject Admin
# ----------------------------
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'code',
        'branch',
        'subject_type',
        'total_marks',
        'pass_marks',
        'is_active',
    )

    list_filter = (
        'branch',
        'subject_type',
        'is_active',
        'is_optional',
    )

    search_fields = (
        'name',
        'code',
        'branch__name',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    autocomplete_fields = ('branch', 'created_by')


# ----------------------------
# SectionSubject Admin
# ----------------------------
@admin.register(SectionSubject)
class SectionSubjectAdmin(admin.ModelAdmin):
    list_display = (
        'section',
        'subject',
        'teacher',
        'is_active',
        'assigned_at',
    )

    list_filter = (
        'section__class_obj__branch',
        'is_active',
    )

    search_fields = (
        'section__name',
        'subject__name',
        'teacher__username',
    )

    readonly_fields = (
        'assigned_at',
        'updated_at',
    )

    autocomplete_fields = (
        'section',
        'subject',
        'teacher',
        'assigned_by',
    )
