try:
    import local_settings
except:
    local_settings = None

import djmicro, os
djmicro.configure({
    'INSTALLED_APPS': ('opencivicdata', 'django.contrib.staticfiles', 'dryrub'),
    'STATIC_URL': '/static/',
    'STATICFILES_DIRS': (os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'),)
}, local_settings=local_settings)

from django.views.generic import TemplateView, ListView, RedirectView
from django.http import Http404
from braces.views import OrderableListMixin
from models import *
from django.db.models import Count, Max

## Disclosures

@djmicro.route(r'^$')
class Index(RedirectView):
    url = '/lobbying/registrations'

@djmicro.route(r'^lobbying/registrations$', name='registration-list')
class DisclosureListView(OrderableListMixin, ListView):
    paginate_by = 10
    template_name = 'templates/registration_list.html'
    orderable_columns = ('start_time', 'client', 'registrant')
    orderable_columns_default = 'start_time'
    order_by_default = {'start_time': 'desc'}
    order_mapping = {'client': 'name', 'registrant': 'name'}

    def get_queryset(self, initial_qs=None):
        if initial_qs is None:
            initial_qs = LobbyingRegistration.objects.all()

        order_by = self.request.GET.get('order_by', 'start_time')
        if order_by in ('client', 'registrant'):
            qs = EventParticipant.objects.filter(event_id__in=initial_qs, note=order_by)
        else:
            qs = initial_qs.prefetch_related('participants__organization', 'agenda')
        return self.get_ordered_queryset(qs)

    def get_ordered_queryset(self, queryset=None):
        get_order_by = self.request.GET.get("order_by")

        order_by = get_order_by if get_order_by in self.get_orderable_columns() else self.get_orderable_columns_default()

        self.order_by = order_by
        self.ordering = self.request.GET.get("ordering", self.order_by_default.get(self.order_by, "asc"))

        order_by = self.order_mapping.get(order_by, order_by)
        if order_by and self.ordering == "desc":
            order_by = "-" + order_by

        return queryset.order_by(order_by)

    def paginate_queryset(self, queryset, page_size):
        paginator, page, object_list, is_paginated = super(DisclosureListView, self).paginate_queryset(queryset, page_size)

        if self.order_by in ('client', 'registrant'):
            object_list = sorted(LobbyingRegistration.objects.filter(id__in=object_list.values('event_id')).prefetch_related('participants__organization', 'agenda'), key=lambda lr: getattr(lr, self.order_by + "s")[0].name)

        return (paginator, page, object_list, is_paginated)

@djmicro.route(r'^lobbying/registrations/(?P<short_uuid>\w+)$', name='registration-detail')
class DisclosureView(TemplateView):
    template_name = 'templates/registration.html'

    def get_context_data(self, short_uuid):
        try:
            obj = LobbyingRegistration.filter_by_short_uuid(short_uuid).prefetch_related('participants__organization', 'participants__person', 'agenda').get()
        except LobbyingRegistration.DoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': LobbyingRegistration._meta.verbose_name})
        return {'object': obj}


## Issues

@djmicro.route(r'^lobbying/issues$', name='issue-list')
class IssueListView(TemplateView):
    template_name = 'templates/issue_list.html'

    def get_context_data(self):
        return {'object_list': sorted(GENERAL_ISSUE_CODES, key=lambda x: x['description'])}

@djmicro.route(r'^lobbying/issues/(?P<slug>[\w-]+)$', name='issue-detail')
class IssueView(DisclosureListView):
    template_name = 'templates/issue.html'

    def get_queryset(self):
        issue = issues_by_slug[self.kwargs['slug']]
        return super(IssueView, self).get_queryset(initial_qs=LobbyingRegistration.objects.filter(agenda__subjects__contains=[issue['issue_code']]))

    def get_context_data(self, *args, **kwargs):
        context_data = super(IssueView, self).get_context_data(*args, **kwargs)
        context_data['object'] = issues_by_slug[self.kwargs['slug']]
        return context_data


## Participants (clients/registrants/lobbyists)

class ParticipantListView(ListView):
    template_name = 'templates/participant_list.html'

    participant_type = None
    model = None

    def get_context_data(self, *args, **kwargs):
        context_data = super(ParticipantListView, self).get_context_data(*args, **kwargs)
        context_data['participants_by_alpha'] = [(letter, list(group)) for letter, group in itertools.groupby(self.model.objects.all().order_by('name'), key=lambda org: org.name[0].upper())]
        context_data['participant_type'] = self.participant_type
        return context_data

@djmicro.route(r'^lobbying/registrants$', name='registrant-list')
class RegistrantListView(ParticipantListView):
    model = Registrant
    participant_type = 'registrant'

@djmicro.route(r'^lobbying/clients$', name='client-list')
class ClientListView(ParticipantListView):
    model = Client
    participant_type = 'client'


class ParticipantView(DisclosureListView):
    template_name = 'templates/participant.html'

    participant_type = None
    model = None

    def get_queryset(self):
        try:
            self.participant = self.model.filter_by_short_uuid(self.kwargs['short_uuid']).get()
        except LobbyingRegistration.DoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': self.model._meta.verbose_name})
        
        participation = EventParticipant.objects.filter(**{("person" if self.participant_type == 'lobbyist' else "organization"): self.participant, 'note': self.participant_type})
        return super(ParticipantView, self).get_queryset(initial_qs=LobbyingRegistration.objects.filter(participants__in=participation))

    def get_context_data(self, *args, **kwargs):
        context_data = super(ParticipantView, self).get_context_data(*args, **kwargs)
        context_data['object'] = self.participant
        context_data['participant_type'] = self.participant_type
        return context_data

@djmicro.route(r'^lobbying/registrants/(?P<slug>[\w-]+)/(?P<short_uuid>[\w-]+)$', name='registrant-detail')
class RegistrantView(ParticipantView):
    model = Registrant
    participant_type = 'registrant'

@djmicro.route(r'^lobbying/clients/(?P<slug>[\w-]+)/(?P<short_uuid>[\w-]+)$', name='client-detail')
class ClientView(ParticipantView):
    model = Client
    participant_type = 'client'

@djmicro.route(r'^lobbying/lobbyists/(?P<slug>[\w-]+)/(?P<short_uuid>[\w-]+)$', name='lobbyist-detail')
class LobbyistView(ParticipantView):
    model = Lobbyist
    participant_type = 'lobbyist'

# the lobbyist list view is its own thing
@djmicro.route(r'^lobbying/lobbyists$', name='lobbyist-list')
class LobbyistListView(OrderableListMixin, ListView):
    paginate_by = 10
    template_name = 'templates/lobbyist_list.html'
    orderable_columns = ('name', 'num_registrations', 'most_recent')
    orderable_columns_default = 'name'

    def get_queryset(self):
        # I *think* this annotation does the right thing, per https://docs.djangoproject.com/en/1.7/topics/db/aggregation/#order-of-annotate-and-filter-clauses , but should recheck with more data
        qs = Lobbyist.objects.filter(eventparticipant__note="lobbyist", eventparticipant__event__classification="registration").annotate(
            num_registrations=Count('eventparticipant__event'),
            most_recent=Max('eventparticipant__event__start_time')
        ).prefetch_related('eventparticipant_set', 'eventparticipant_set__event', 'eventparticipant_set__event__participants')
        return self.get_ordered_queryset(qs)

# run the site
if __name__ == '__main__':
    djmicro.run()