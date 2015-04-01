import global_settings, os
if 'DYNO' in os.environ:
    # we're on heroku
    import heroku_settings as local_settings
else:
    try:
        import local_settings
    except:
        local_settings = None

import djmicro, os, re
djmicro.configure([global_settings, local_settings], app_name="vashistha")

from django.views.generic import TemplateView, ListView, RedirectView
from django.core.urlresolvers import reverse
from django.http import Http404
from django.template import Context, loader
from braces.views import OrderableListMixin
from django.db.models import Count, Max, Min, Q
from django.utils.text import slugify

from models import *
from mixins import *

@djmicro.route(r'^$')
class Index(RedirectView):
    url = '/lobbying/registrations'

## Disclosures

@djmicro.route(r'^lobbying/registrations$', name='registration-list')
class DisclosureListView(EnhancedOrderableListView):
    paginate_by = 10
    template_name = 'templates/registration_list.html'
    orderable_columns = ('start_time', 'client', 'registrant')
    orderable_columns_default = 'start_time'
    order_by_default = {'start_time': 'desc'}
    order_mapping = {'client': 'name', 'registrant': 'name'}

    section = "registrations"

    def get_queryset(self, initial_qs=None):
        if initial_qs is None:
            initial_qs = LobbyingRegistration.objects.all()

        order_by = self.request.GET.get('order_by', 'start_time')
        if order_by in ('client', 'registrant'):
            qs = EventParticipant.objects.filter(event_id__in=initial_qs, note=order_by)
        else:
            qs = initial_qs.prefetch_related('participants__organization', 'agenda')
        return self.get_ordered_queryset(qs)

    def paginate_queryset(self, queryset, page_size):
        paginator, page, object_list, is_paginated = super(DisclosureListView, self).paginate_queryset(queryset, page_size)

        if self.order_by in ('client', 'registrant'):
            object_list = sorted(LobbyingRegistration.objects.filter(id__in=object_list.values('event_id')).prefetch_related('participants__organization', 'agenda'), key=lambda lr: getattr(lr, self.order_by + "s")[0].name)

        return (paginator, page, object_list, is_paginated)

    # rss
    @classmethod
    def as_rss(cls):
        class RssFeed(DisclosureRssMixin, cls):
            pass
        return RssFeed

    @property
    def rss_path(self):
        return reverse(self.request.resolver_match.url_name + "-feed", kwargs=self.kwargs)

    # csv
    @classmethod
    def as_csv(cls):
        class CsvDump(DisclosureCsvMixin, cls):
            pass
        return CsvDump

    @property
    def csv_path(self):
        return reverse(self.request.resolver_match.url_name + "-csv", kwargs=self.kwargs)

djmicro.route(r'^lobbying/registrations.rss$', name='registration-list-feed')(DisclosureListView.as_rss())

@djmicro.route(r'^lobbying/registrations/(?P<short_uuid>\w+)$', name='registration-detail')
class DisclosureView(TemplateView):
    template_name = 'templates/registration.html'
    section = 'registrations'

    def get_context_data(self, short_uuid):
        context = super(DisclosureView, self).get_context_data()
        try:
            obj = LobbyingRegistration.filter_by_short_uuid(short_uuid).prefetch_related('participants__organization', 'participants__person', 'agenda').get()
        except LobbyingRegistration.DoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': LobbyingRegistration._meta.verbose_name})
        context['object'] = obj
        return context


## Issues

@djmicro.route(r'^lobbying/issues$', name='issue-list')
class IssueListView(TemplateView):
    template_name = 'templates/issue_list.html'
    section = 'issues'

    def get_context_data(self):
        context = super(IssueListView, self).get_context_data()
        context['object_list'] = sorted(GENERAL_ISSUE_CODES, key=lambda x: x['description'])
        return context

@djmicro.route(r'^lobbying/issues/(?P<slug>[\w-]+)$', name='issue-detail')
class IssueView(DisclosureListView):
    template_name = 'templates/issue.html'
    section = 'issues'

    def get_queryset(self):
        issue = issues_by_slug[self.kwargs['slug']]
        return super(IssueView, self).get_queryset(initial_qs=LobbyingRegistration.objects.filter(agenda__subjects__contains=[issue['issue_code']]))

    def get_context_data(self, *args, **kwargs):
        context_data = super(IssueView, self).get_context_data(*args, **kwargs)
        context_data['object'] = issues_by_slug[self.kwargs['slug']]
        return context_data

djmicro.route(r'^lobbying/issues/(?P<slug>[\w-]+).rss$', name='issue-detail-feed')(IssueView.as_rss())
djmicro.route(r'^lobbying/issues/(?P<slug>[\w-]+).csv$', name='issue-detail-csv')(IssueView.as_csv())


## Participants (clients/registrants/lobbyists)

class ParticipantListView(ListView):
    template_name = 'templates/participant_list.html'

    participant_type = None
    model = None

    def get_context_data(self, *args, **kwargs):
        context_data = super(ParticipantListView, self).get_context_data(*args, **kwargs)
        nonletters = re.compile('[^A-Z0-9]')
        objects = sorted(self.model.objects.all().only('name').distinct('id'), key=lambda org: org.name.upper())
        context_data['participants_by_alpha'] = [(letter, list(group)) for letter, group in itertools.groupby(objects, key=lambda org: org.name[0].upper())]
        context_data['participant_type'] = self.participant_type
        return context_data

@djmicro.route(r'^lobbying/registrants$', name='registrant-list')
class RegistrantListView(ParticipantListView):
    model = Registrant
    participant_type = 'registrant'
    section = 'registrants'

@djmicro.route(r'^lobbying/clients$', name='client-list')
class ClientListView(ParticipantListView):
    model = Client
    participant_type = 'client'
    section = 'clients'


class ParticipantView(DisclosureListView):
    template_name = 'templates/participant.html'

    participant_type = None
    model = None

    def get_queryset(self):
        try:
            self.participant = self.model.filter_by_short_uuid(self.kwargs['short_uuid']).get()
        except:
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
    section = 'registrants'

djmicro.route(r'^lobbying/registrants/(?P<slug>[\w-]+)/(?P<short_uuid>[\w-]+).rss$', name='registrant-detail-feed')(RegistrantView.as_rss())
djmicro.route(r'^lobbying/registrants/(?P<slug>[\w-]+)/(?P<short_uuid>[\w-]+).csv$', name='registrant-detail-csv')(RegistrantView.as_csv())

@djmicro.route(r'^lobbying/clients/(?P<slug>[\w-]+)/(?P<short_uuid>[\w-]+)$', name='client-detail')
class ClientView(ParticipantView):
    model = Client
    participant_type = 'client'
    section = 'clients'

djmicro.route(r'^lobbying/clients/(?P<slug>[\w-]+)/(?P<short_uuid>[\w-]+).rss$', name='client-detail-feed')(ClientView.as_rss())
djmicro.route(r'^lobbying/clients/(?P<slug>[\w-]+)/(?P<short_uuid>[\w-]+).csv$', name='client-detail-csv')(ClientView.as_csv())

@djmicro.route(r'^lobbying/lobbyists/(?P<slug>[\w-]+)/(?P<short_uuid>[\w-]+)$', name='lobbyist-detail')
class LobbyistView(ParticipantView):
    model = Lobbyist
    participant_type = 'lobbyist'
    section = 'lobbyists'
    template_name = 'templates/lobbyist.html'

djmicro.route(r'^lobbying/lobbyists/(?P<slug>[\w-]+)/(?P<short_uuid>[\w-]+).rss$', name='lobbyist-detail-feed')(LobbyistView.as_rss())
djmicro.route(r'^lobbying/lobbyists/(?P<slug>[\w-]+)/(?P<short_uuid>[\w-]+).csv$', name='lobbyist-detail-csv')(LobbyistView.as_csv())

# the lobbyist list view is its own thing
@djmicro.route(r'^lobbying/lobbyists$', name='lobbyist-list')
class LobbyistListView(EnhancedOrderableListView):
    paginate_by = 10
    template_name = 'templates/lobbyist_list.html'
    orderable_columns = ('name', 'num_registrations', 'most_recent')
    orderable_columns_default = 'most_recent'
    order_by_default = {'most_recent': 'desc', 'num_registrations': 'desc'}
    section = 'lobbyists'

    def get_queryset(self):
        # I *think* this annotation does the right thing, per https://docs.djangoproject.com/en/1.7/topics/db/aggregation/#order-of-annotate-and-filter-clauses , but should recheck with more data
        qs = Lobbyist.unfiltered_objects.values('id').filter(eventparticipant__note="lobbyist", eventparticipant__event__classification="registration").annotate(
            num_registrations=Count('eventparticipant__event'),
            most_recent=Max('eventparticipant__event__start_time')
        )
        
        return self.get_ordered_queryset(qs)

    def get_context_data(self, *args, **kwargs):
        context = super(LobbyistListView, self).get_context_data(*args, **kwargs)

        # our object list isn't really an object list because of the hackery to get the queries to perform sanely, realize it again
        object_dict = {obj['id']: dict(order=i, **obj) for i, obj in enumerate(context['object_list'])}
        qs = Lobbyist.unfiltered_objects.filter(id__in=object_dict.keys())\
            .prefetch_related('eventparticipant_set__event__participants__organization')
        
        new_object_list = list(qs)

        # copy the annotations back
        for obj in qs:
            obj.num_registrations = object_dict[obj.id]['num_registrations']
            obj.most_recent = object_dict[obj.id]['most_recent']

        # match the original order, and save it back into the context
        context['object_list'] = sorted(new_object_list, key=lambda obj: object_dict[obj.id]['order'])
        return context


## Search
from haystack.query import SearchQuerySet
@djmicro.route(r'^lobbying/search$', name='search')
class SearchView(ListView):
    paginate_by = 10
    template_name = 'templates/search_results.html'
    section = None

    def get_queryset(self):
        return SearchQuerySet().filter(content=self.request.GET.get('q', ''))

    def get_context_data(self, *args, **kwargs):
        context = super(SearchView, self).get_context_data(*args, **kwargs)
        
        # make a new object list we can hang extra stuff off of
        model_overrides = {'searchissue': 'issue', 'lobbyingregistration': 'registration'}
        object_list = [{
            'text': obj.text if obj.model_name != "searchissue" else issues_by_code[obj.pk]['description'],
            'model_name': model_overrides.get(obj.model_name, obj.model_name),
            'pk': obj.pk,
            'is_participant': obj.model_name in ('client', 'registrant', 'lobbyist'),
        } for obj in context['object_list']]

        result_stats = {}

        # get stats about registrations for clients, registrants, and lobbyists
        participants = [result for result in object_list if result['is_participant']]
        if participants:
            participant_stats_list = EventParticipant.objects\
                .filter(
                    Q(organization_id__in=[participant['pk'] for participant in participants if participant['model_name'] in ('registrant', 'client')]) |\
                    Q(person_id__in=[participant['pk'] for participant in participants if participant['model_name'] == 'lobbyist']),
                    event__classification="registration", event__disclosurerelatedentity__disclosure__classification="lobbying",\
                )\
                .values('person_id', 'organization_id', 'note')\
                .annotate(num_registrations=Count('event_id'), first_registration=Min('event__start_time'), last_registration=Max('event__start_time'))
            result_stats.update({(participant['note'], participant['person_id'] if participant['note'] == 'lobbyist' else participant['organization_id']) : participant for participant in participant_stats_list})

        # same with issues
        # there's some crazy hackery here because unrolling Postgres arrays and aggregating their contents turns out to be a huge pain
        issues = [result for result in object_list if result['model_name'] == "issue"]
        if issues:
            issue_ids = [result['pk'] for result in issues]
            issue_stats_list = LobbyingRegistration.objects\
                .filter(agenda__subjects__overlap=issue_ids)\
                .extra(select={'issue': 'unnest(%s.subjects)' % EventAgendaItem._meta.db_table}, tables=(EventAgendaItem._meta.db_table,))\
                .values("issue")\
                .annotate(num_registrations=Count('agenda'), first_registration=Min('start_time'), last_registration=Max('start_time'))
            result_stats.update({('issue', issue['issue']) : issue for issue in issue_stats_list if issue['issue'] in issue_ids})

        # grab the full records for any matched registrations
        registrations = [result for result in object_list if result['model_name'] == 'registration']
        if registrations:
            registration_records = LobbyingRegistration.objects.filter(id__in=[r['pk'] for r in registrations]).prefetch_related('participants__organization', 'agenda')
            result_stats.update({('registration', r.id): r for r in registration_records})

        # combine everything
        for result in object_list:
            result['stats'] = result_stats.get((result['model_name'], result['pk']), {})

            # hang URLs and other necessary metadata
            result['nice_name'] = result['model_name']
            if result['is_participant']:
                if result['model_name'] == 'lobbyist':
                    # only use up until the first carriage return, because the rest might be covered positions
                    result['text'] = result['text'].split('\n')[0]
                slug = slugify(result['text'])
                short_pk = shortuuid.encode(uuid.UUID(result['pk'].split("/")[-1]))
                result['url'] = reverse(result['model_name'] + '-detail', args=[slug if slug else '-', short_pk])
            elif result['model_name'] == 'issue':
                result['url'] = reverse('issue-detail', args=(issues_by_code[result['pk']]['slug'],))
            elif result['model_name'] == 'registration':
                result['url'] = reverse('registration-detail', args=(result['stats'].short_uuid,))
                result['nice_name'] = 'lobbying registration'
                registrants = result['stats'].registrants
                clients = result['stats'].clients
                result['text'] = "%s for %s" % (registrants[0].name if registrants else "A registrant", clients[0].name if clients else "a client")

        context['query'] = self.request.GET.get('q', '')
        context['object_list'] = object_list
        return context

## Post-employment tracker

@djmicro.route(r'^post-employment$', name='pet-list')
class PETListView(EnhancedOrderableListView):
    template_name = 'templates/pet_list.html'
    orderable_columns = ('last_name', 'start_time', 'end_time', 'office', 'body', 'days_left')
    orderable_columns_default = 'days_left'

    def get_queryset(self):
        return self.get_ordered_queryset(PostEmploymentRegistration.objects.all().prefetch_related('sources', 'participants').distinct('id'))

    def get_ordered_queryset(self, queryset=None):
        get_order_by = self.request.GET.get("order_by")

        order_by = get_order_by if get_order_by in self.get_orderable_columns() else self.get_orderable_columns_default()

        self.order_by = order_by
        self.ordering = self.request.GET.get("ordering", self.order_by_default.get(self.order_by, "asc"))

        order_by = self.order_mapping.get(order_by, order_by)
        
        reverse = self.ordering == "desc"

        # we just sort everything in-memory, because not everything is handy in the database
        return sorted([item.as_row() for item in queryset], key=lambda item: item[order_by], reverse=reverse)

@djmicro.route(r'^post-employment/(?P<short_uuid>\w+)$', name='pet-detail')
class PETDetailView(TemplateView):
    template_name = 'templates/pet_detail.html'

    def get_context_data(self, short_uuid):
        context = super(PETDetailView, self).get_context_data()
        try:
            obj = PostEmploymentRegistration.filter_by_short_uuid(short_uuid).prefetch_related('sources', 'participants').distinct('id').get()
        except LobbyingRegistration.DoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': LobbyingRegistration._meta.verbose_name})
        context['object'] = obj.as_row()
        return context
        

# make a couple of other modules visible to Django
import models, migrations, search_indexes
djmicro.add_module_to_app(models)
djmicro.add_module_to_app(migrations)
djmicro.add_module_to_app(search_indexes)

# run the site
if __name__ == '__main__':
    djmicro.run()