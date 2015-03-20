import itertools
from opencivicdata.models import *

import uuid, shortuuid

class LobbyingRegistration(Event):
    class Meta:
        proxy = True
        app_label = 'opencivicdata'

    objects = Event.objects.filter(disclosurerelatedentity__disclosure__classification="lobbying", classification="registration").as_manager()

    @property
    def clients(self):
        return [participant.organization for participant in self.participants.all() if participant.note == "client"]

    @property
    def registrants(self):
        return [participant.organization for participant in self.participants.all() if participant.note == "registrant"]

    @property
    def lobbyists(self):
        return [participant.person for participant in self.participants.all() if participant.note == "lobbyist"]

    @property
    def issues(self):
        return list(itertools.chain.from_iterable((item.subjects for item in self.agenda.all())))

    # short uuid stuff
    @property
    def short_uuid(self):
        return shortuuid.encode(uuid.UUID(self.id.split("/")[-1]))

    @classmethod
    def filter_by_short_uuid(cls, short_uuid):
        return cls.objects.filter(id='ocd-event/%s' % str(shortuuid.decode(short_uuid)))