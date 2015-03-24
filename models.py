import itertools
from opencivicdata.models import *
from django.db import models

import uuid, shortuuid, json

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
        return cls.objects.filter(id='ocd-%s/%s' % (cls._meta.get_field_by_name('id')[0].ocd_type, str(shortuuid.decode(short_uuid))))


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
        return [swap_type(participant.organization, Client) for participant in self.participants.all() if participant.note == "client"]

    @property
    def registrants(self):
        return [swap_type(participant.organization, Registrant) for participant in self.participants.all() if participant.note == "registrant"]

    @property
    def lobbyists(self):
        return [swap_type(participant.person, Lobbyist) for participant in self.participants.all() if participant.note == "lobbyist"]

    @property
    def issues(self):
        return list(itertools.chain.from_iterable(([issues_by_code[subject] for subject in item.subjects] for item in self.agenda.all())))


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
        registrants = itertools.chain.from_iterable([[part.organization for part in participant.event.participants.all() if part.note == 'registrant'] for participant in self.eventparticipant_set.all()])
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

    objects = LobbyistManager()


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


## Issues -- not really models, but same idea
from sopr_lobbying_reference import GENERAL_ISSUE_CODES
from django.utils.text import slugify

issues_by_code = {}
issues_by_slug = {}

for issue in GENERAL_ISSUE_CODES:
    issue['slug'] = slugify(unicode(issue['description']))
    issues_by_code[issue['issue_code']] = issue
    issues_by_slug[issue['slug']] = issue
