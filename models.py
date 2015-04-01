import itertools
from opencivicdata.models import *
from django.db import models

import uuid, shortuuid, json, re, datetime

def swap_type(obj, new_type):
    o = new_type()
    o.__dict__ = obj.__dict__
    return o

class ShortUUIDMixin(object):
    # short uuid stuff
    @property
    def short_uuid(self):
        return shortuuid.encode(uuid.UUID(self.id.split("/")[-1]))

    @classmethod
    def filter_by_short_uuid(cls, short_uuid):
        return cls.objects.filter(id='ocd-%s/%s' % (cls._meta.get_field_by_name('id')[0].ocd_type, str(shortuuid.decode(short_uuid)))).distinct()


## Lobbying registration

class LobbyingRegistrationManager(models.Manager):
    def get_queryset(self):
        return super(LobbyingRegistrationManager, self).get_queryset().filter(disclosurerelatedentity__disclosure__classification="lobbying", classification="registration")

class LobbyingRegistration(Event, ShortUUIDMixin):
    class Meta:
        proxy = True
        app_label = 'opencivicdata'

    objects = LobbyingRegistrationManager()

    @property
    def clients(self):
        return [swap_type(participant.organization, Client) for participant in self.participants.all() if participant.note == "client" and participant.organization_id]

    @property
    def registrants(self):
        return [swap_type(participant.organization, Registrant) for participant in self.participants.all() if participant.note == "registrant" and participant.organization_id]

    @property
    def lobbyists(self):
        return [swap_type(participant.person, Lobbyist) for participant in self.participants.all() if participant.note == "lobbyist" and participant.person_id]

    @property
    def issues(self):
        return list(itertools.chain.from_iterable(([issues_by_code[subject] for subject in item.subjects] for item in self.agenda.all())))

    @property
    def specific_issues(self):
        return list(itertools.chain.from_iterable((item.notes for item in self.agenda.all())))

    @property
    def search_document(self):
        return u"\n".join([
            u"\n".join([registrant.name for registrant in self.registrants]),
            u"\n".join([client.name for client in self.clients]),
            u"\n".join([lobbyist.name for lobbyist in self.lobbyists]),
            u"\n".join([issue['description'].replace("\n", " ") for issue in self.issues]),
            u"\n".join([specific_issue for specific_issue in self.specific_issues]),
        ]).strip()


## Lobbyist

class LobbyistManager(models.Manager):
    def get_queryset(self):
        return super(LobbyistManager, self).get_queryset().filter(eventparticipant__note="lobbyist")

class Lobbyist(Person, ShortUUIDMixin):
    class Meta:
        proxy = True
        app_label = 'opencivicdata'

    @property
    def registrations(self):
        return [swap_type(participant.event, LobbyingRegistration) for participant in self.eventparticipant_set.all() if participant.note == "lobbyist" and participant.event.classification == "registration"]

    @property
    def most_recent_registration(self):
        return max(self.registrations, key=lambda r: r.start_time)

    @property
    def registrants(self):
        registrants = itertools.chain.from_iterable([[part.organization for part in participant.event.participants.all() if part.note == 'registrant'] for participant in self.eventparticipant_set.all().prefetch_related('event', 'event__participants', 'event__participants__organization')])
        unique_registrants = {org.id : org for org in registrants}
        return [swap_type(registrant, Registrant) for registrant in sorted(unique_registrants.values(), key=lambda org: org.name)]

    @property
    def covered_positions(self):
        extras = json.loads(self.extras) if self.extras else {}
        return [x.get('covered_official_position', None) for x in extras.get('lda_covered_official_positions', [])]

    @property
    def slug(self):
        slug = slugify(self.name)
        return slug if slug else "-"

    @property
    def search_document(self):
        return u"\n".join([
            self.name,
            u"\n".join(self.covered_positions)
        ]).strip()

    objects = LobbyistManager()

    # add a way to get to the raw manager -- Django doesn't always make the best decisions about combining the prefiltered manager stuff with new queries
    unfiltered_objects = models.Manager()


## Registrant

class RegistrantManager(models.Manager):
    def get_queryset(self):
        return super(RegistrantManager, self).get_queryset().filter(eventparticipant__note="registrant")

class Registrant(Organization, ShortUUIDMixin):
    class Meta:
        proxy = True
        app_label = 'opencivicdata'

    objects = RegistrantManager()


## Client

class ClientManager(models.Manager):
    def get_queryset(self):
        return super(ClientManager, self).get_queryset().filter(eventparticipant__note="client")

class Client(Organization, ShortUUIDMixin):
    class Meta:
        proxy = True
        app_label = 'opencivicdata'

    objects = ClientManager()


## Issues and registration types -- not really models, but same idea
from sopr_lobbying_reference import GENERAL_ISSUE_CODES, FILING_TYPES
from django.utils.text import slugify

issues_by_code = {}
issues_by_slug = {}

for issue in GENERAL_ISSUE_CODES:
    issue['slug'] = slugify(unicode(issue['description']))
    issues_by_code[issue['issue_code']] = issue
    issues_by_slug[issue['slug']] = issue

filing_types_by_code = {}

for filing_type in FILING_TYPES:
    filing_types_by_code[filing_type['code']] = filing_type

# except actually, for issues we have to fake a model for search
class SearchIssue(models.Model):
    class Meta:
        app_label = "vashistha"

    id = models.CharField(max_length=8, primary_key=True)
    description = models.TextField()

# post-employment
import name_cleaver

class PostEmploymentRegistrationManager(models.Manager):
    def get_queryset(self):
        return super(PostEmploymentRegistrationManager, self).get_queryset().filter(classification="post_employment")

lowercase_letters = re.compile(r'[a-z]+')
class PostEmploymentRegistration(Event, ShortUUIDMixin):
    class Meta:
        proxy = True
        app_label = 'opencivicdata'

    objects = PostEmploymentRegistrationManager()

    def as_row(self):
        office = json.loads(self.extras)['office_name']
        if not lowercase_letters.findall(office):
            office = office.title()

        source_url = self.sources.all()[0].url

        original_name = self.participants.all()[0].name

        # fix the stupid thing with the house names having extra commas
        parts = original_name.split(',')
        to_parse = original_name if len(parts) <= 2 else "".join([",".join(parts[:2])] + parts[2:])

        parsed = name_cleaver.IndividualNameCleaver(to_parse).parse()

        days_left = (self.end_time.date() - datetime.datetime.now().date()).days
        days_left_s = days_left if days_left >= 0 else (-1 * days_left) + 1000000
        
        return {
            'name': parsed.name_str(),
            'last_name': parsed.last,
            'middle_name': parsed.middle,
            'first_name': parsed.first,
            'original_name': original_name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'office': office,
            'source_url': source_url,
            'body': 'Senate' if 'senate.gov' in source_url else 'House',
            'days_left_real': days_left,
            'days_left': days_left_s,
            'pk': self.short_uuid
        }

# a convenience method to grab and cache all the PET rows
from util import cache
@cache(seconds=86400 * 365)
def get_all_pet_records():
    queryset = PostEmploymentRegistration.objects.all().prefetch_related('sources', 'participants').distinct('id')
    return [item.as_row() for item in queryset]