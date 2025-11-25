from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from core.signals import log_view_activity, log_export_activity

from .models import Document
from .forms import DocumentForm

@login_required
def upload_document(request, content_type_id, object_id):
    content_type = get_object_or_404(ContentType, id=content_type_id)
    model_class = content_type.model_class()
    obj = get_object_or_404(model_class, pk=object_id)

    # Check permissions
    if not request.user.has_perm(f'{content_type.app_label}.view_{content_type.model}'):
        return HttpResponseForbidden(_("You do not have permission to access this object"))

    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.content_type = content_type
            document.object_id = object_id
            document.uploaded_by = request.user
            document.save()

            # Log activity
            try:
                log_view_activity(request, 'add', document, _('Document uploaded: %(title)s') % {'title': document.title})
            except:
                pass

            messages.success(request, _('Document uploaded successfully'))
            return redirect(request.META.get('HTTP_REFERER', reverse('core:dashboard')))
    else:
        form = DocumentForm()

    context = {
        'form': form,
        'object': obj,
        'content_type': content_type,
    }
    return render(request, 'documents/upload.html', context)

@login_required
def document_list(request, content_type_id, object_id):
    content_type = get_object_or_404(ContentType, id=content_type_id)
    model_class = content_type.model_class()
    obj = get_object_or_404(model_class, pk=object_id)

    # Check permissions
    if not request.user.has_perm(f'{content_type.app_label}.view_{content_type.model}'):
        return HttpResponseForbidden(_("You do not have permission to access this object"))

    documents = Document.objects.filter(content_type=content_type, object_id=object_id)

    # Log activity
    try:
        log_view_activity(request, 'view', obj, _('Viewing documents related to %(obj)s') % {'obj': obj})
    except:
        pass

    context = {
        'documents': documents,
        'object': obj,
        'content_type': content_type,
    }
    return render(request, 'documents/list.html', context)

@login_required
def delete_document(request, document_id):
    document = get_object_or_404(Document, id=document_id)

    # Check if user can delete
    if document.uploaded_by != request.user and not request.user.is_superuser:
        return HttpResponseForbidden(_("You cannot delete this document"))

    if request.method == 'POST':
        # Log activity
        try:
            log_view_activity(request, 'delete', document, _('Document deleted: %(title)s') % {'title': document.title})
        except:
            pass

        document.delete()
        messages.success(request, _('Document deleted successfully'))
        return redirect(request.META.get('HTTP_REFERER', reverse('core:dashboard')))

    context = {
        'document': document,
    }
    return render(request, 'documents/delete.html', context)

@login_required
def document_report(request):
    # Check permissions
    if not request.user.has_perm('reports.can_view_documents_report'):
        return HttpResponseForbidden(_("You do not have permission to view documents report"))

    documents = Document.objects.select_related('content_type', 'uploaded_by').order_by('-uploaded_at')

    # Log activity
    try:
        class ReportObj:
            id = 0
            pk = 0
            def __str__(self):
                return _('Documents Report')
        log_view_activity(request, 'view', ReportObj(), _('Viewing documents report'))
    except:
        pass

    context = {
        'documents': documents,
    }
    return render(request, 'documents/report.html', context)
