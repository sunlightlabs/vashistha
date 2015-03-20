try:
    import local_settings
except:
    local_settings = None

import djmicro
djmicro.configure({'INSTALLED_APPS': ('opencivicdata',)}, local_settings=local_settings)

from django.shortcuts import render

@djmicro.route(r'^$')
def index(request):
    return render(request, 'templates/registration_list.html', {'id': id})

from django.views.generic import TemplateView, ListView
from django.http import Http404
from braces.views import OrderableListMixin
from models import *

@djmicro.route(r'^lobbying/disclosures$')
class DisclosureListView(ListView, OrderableListMixin):
    paginate_by = 10
    template_name = 'templates/registration_list.html'
    orderable_columns = ('start_time', 'name')
    orderable_columns_default = 'start_time'

    def get_queryset(self, initial_qs=None):
        if initial_qs is None:
            initial_qs = LobbyingRegistration.objects.all()

        order_type = self.request.GET.get('order_type', 'start_time')
        if order_type in ('client', 'registrant'):
            qs = EventParticipant.objects.filter(event_id__in=initial_qs, note=order_type).order_by('name')
        else:
            qs = initial_qs.prefetch_related('participants__organization', 'agenda')
        return self.get_ordered_queryset(qs)

    def paginate_queryset(self, queryset, page_size):
        paginator, page, object_list, is_paginated = super(DisclosureListView, self).paginate_queryset(queryset, page_size)

        order_type = self.request.GET.get('order_type', 'start_time')
        if order_type in ('client', 'registrant'):
            object_list = sorted(LobbyingRegistration.objects.filter(id__in=object_list.values('event_id')).prefetch_related('participants__organization', 'agenda'), key=lambda lr: getattr(lr, order_type + "s")[0].name)

        return (paginator, page, object_list, is_paginated)

@djmicro.route(r'^lobbying/disclosures/(?P<short_uuid>\w+)$')
class DisclosureView(TemplateView):
    template_name = 'templates/registration.html'

    def get_context_data(self, short_uuid):
        try:
            obj = LobbyingRegistration.filter_by_short_uuid(short_uuid).prefetch_related('participants__organization', 'participants__person', 'agenda').get()
        except LobbyingRegistration.DoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': LobbyingRegistration._meta.verbose_name})
        return {'object': obj}

if __name__ == '__main__':
    djmicro.run()