from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Sum, Count
from django.http import JsonResponse
from .models import ProvisionType, Provision, ProvisionEntry
from .forms import ProvisionTypeForm, ProvisionForm, ProvisionEntryForm
from backup.views import log_audit


class ProvisionTypeListView(ListView):
    model = ProvisionType
    template_name = 'provisions/provision_type_list.html'
    context_object_name = 'provision_types'
    paginate_by = 10

    def get_queryset(self):
        return ProvisionType.objects.filter(is_active=True)


class ProvisionTypeCreateView(CreateView):
    model = ProvisionType
    form_class = ProvisionTypeForm
    template_name = 'provisions/provision_type_form.html'
    success_url = reverse_lazy('provision_type_list')

    def form_valid(self, form):
        messages.success(self.request, _('Provision type created successfully'))
        log_audit(self.request.user, 'CREATE', 'ProvisionType', form.instance.id, f'Created provision type: {form.instance.name}')
        return super().form_valid(form)


class ProvisionTypeUpdateView(UpdateView):
    model = ProvisionType
    form_class = ProvisionTypeForm
    template_name = 'provisions/provision_type_form.html'
    success_url = reverse_lazy('provision_type_list')

    def form_valid(self, form):
        messages.success(self.request, _('Provision type updated successfully'))
        log_audit(self.request.user, 'UPDATE', 'ProvisionType', form.instance.id, f'Updated provision type: {form.instance.name}')
        return super().form_valid(form)


class ProvisionTypeDeleteView(DeleteView):
    model = ProvisionType
    template_name = 'provisions/provision_type_confirm_delete.html'
    success_url = reverse_lazy('provision_type_list')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        log_audit(request.user, 'DELETE', 'ProvisionType', obj.id, f'Deleted provision type: {obj.name}')
        messages.success(request, _('Provision type deleted successfully'))
        return super().delete(request, *args, **kwargs)


class ProvisionListView(ListView):
    model = Provision
    template_name = 'provisions/provision_list.html'
    context_object_name = 'provisions'
    paginate_by = 10

    def get_queryset(self):
        return Provision.objects.filter(is_active=True).select_related('provision_type', 'related_account', 'provision_account')


class ProvisionDetailView(DetailView):
    model = Provision
    template_name = 'provisions/provision_detail.html'
    context_object_name = 'provision'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entries'] = ProvisionEntry.objects.filter(provision=self.object).order_by('-date')
        context['total_entries'] = context['entries'].aggregate(total=Sum('amount'))['total'] or 0
        return context


class ProvisionCreateView(CreateView):
    model = Provision
    form_class = ProvisionForm
    template_name = 'provisions/provision_form.html'
    success_url = reverse_lazy('provision_list')

    def form_valid(self, form):
        messages.success(self.request, _('Provision created successfully'))
        log_audit(self.request.user, 'CREATE', 'Provision', form.instance.id, f'Created provision: {form.instance.name}')
        return super().form_valid(form)


class ProvisionUpdateView(UpdateView):
    model = Provision
    form_class = ProvisionForm
    template_name = 'provisions/provision_form.html'
    success_url = reverse_lazy('provision_list')

    def form_valid(self, form):
        messages.success(self.request, _('Provision updated successfully'))
        log_audit(self.request.user, 'UPDATE', 'Provision', form.instance.id, f'Updated provision: {form.instance.name}')
        return super().form_valid(form)


class ProvisionDeleteView(DeleteView):
    model = Provision
    template_name = 'provisions/provision_confirm_delete.html'
    success_url = reverse_lazy('provision_list')

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        log_audit(request.user, 'DELETE', 'Provision', obj.id, f'Deleted provision: {obj.name}')
        messages.success(request, _('Provision deleted successfully'))
        return super().delete(request, *args, **kwargs)


@login_required
def provision_entry_create(request, provision_id):
    provision = get_object_or_404(Provision, id=provision_id)
    if request.method == 'POST':
        form = ProvisionEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.provision = provision
            entry.save()
            messages.success(request, _('Provision entry added successfully'))
            log_audit(request.user, 'CREATE', 'ProvisionEntry', entry.id, f'Created provision entry for: {provision.name}')
            return redirect('provision_detail', pk=provision_id)
    else:
        form = ProvisionEntryForm()
    return render(request, 'provisions/provision_entry_form.html', {'form': form, 'provision': provision})


@login_required
def provision_entry_update(request, entry_id):
    entry = get_object_or_404(ProvisionEntry, id=entry_id)
    if request.method == 'POST':
        form = ProvisionEntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, _('Provision entry updated successfully'))
            log_audit(request.user, 'UPDATE', 'ProvisionEntry', entry.id, f'Updated provision entry for: {entry.provision.name}')
            return redirect('provision_detail', pk=entry.provision.id)
    else:
        form = ProvisionEntryForm(instance=entry)
    return render(request, 'provisions/provision_entry_form.html', {'form': form, 'provision': entry.provision})


@login_required
def provision_entry_delete(request, entry_id):
    entry = get_object_or_404(ProvisionEntry, id=entry_id)
    provision_id = entry.provision.id
    if request.method == 'POST':
        log_audit(request.user, 'DELETE', 'ProvisionEntry', entry.id, f'Deleted provision entry for: {entry.provision.name}')
        entry.delete()
        messages.success(request, _('Provision entry deleted successfully'))
        return redirect('provision_detail', pk=provision_id)
    return render(request, 'provisions/provision_entry_confirm_delete.html', {'entry': entry})


@login_required
def provision_report(request):
    provisions = Provision.objects.filter(is_active=True).select_related('provision_type', 'related_account', 'provision_account')
    total_provisions = provisions.aggregate(total=Sum('amount'))['total'] or 0

    # Report by type
    type_report = provisions.values('provision_type__name').annotate(
        total_amount=Sum('amount'),
        count=Count('id')
    ).order_by('-total_amount')

    # Report by fiscal year
    fiscal_year_report = provisions.values('fiscal_year').annotate(
        total_amount=Sum('amount'),
        count=Count('id')
    ).order_by('-fiscal_year')

    # Convert data to JSON for charts
    import json
    type_report_json = json.dumps(list(type_report))
    fiscal_year_report_json = json.dumps(list(fiscal_year_report))

    context = {
        'provisions': provisions,
        'total_provisions': total_provisions,
        'type_report': type_report,
        'fiscal_year_report': fiscal_year_report,
        'type_report_json': type_report_json,
        'fiscal_year_report_json': fiscal_year_report_json,
    }
    return render(request, 'provisions/provision_report.html', context)


@login_required
def provision_movement_report(request):
    entries = ProvisionEntry.objects.select_related('provision__provision_type').order_by('-date')

    # Filter by provision
    provision_id = request.GET.get('provision')
    if provision_id:
        entries = entries.filter(provision_id=provision_id)

    # Filter by date
    date_from = request.GET.get('date_from')
    if date_from:
        entries = entries.filter(date__gte=date_from)

    date_to = request.GET.get('date_to')
    if date_to:
        entries = entries.filter(date__lte=date_to)

    total_movements = entries.aggregate(total=Sum('amount'))['total'] or 0

    # Get all provisions for filtering
    provisions = Provision.objects.filter(is_active=True)

    context = {
        'entries': entries,
        'total_movements': total_movements,
        'provisions': provisions,
    }
    return render(request, 'provisions/provision_movement_report.html', context)


@login_required
def ajax_provision_balance(request, provision_id):
    provision = get_object_or_404(Provision, id=provision_id)
    total_entries = ProvisionEntry.objects.filter(provision=provision).aggregate(total=Sum('amount'))['total'] or 0
    balance = provision.amount - total_entries
    return JsonResponse({'balance': balance})
