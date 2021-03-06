from haystack import indexes
from models import *

class DistinctMixin(indexes.SearchIndex):
    def index_queryset(self, using=None):
        return self.get_model().objects.all().distinct('id')

class IssueIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='description')
    
    def get_model(self):
        return SearchIssue

    def index_queryset(self, using=None):
        # hack: update the database before handing over the QS
        for issue in GENERAL_ISSUE_CODES:
            search_issue = SearchIssue(id=issue['issue_code'], description=issue['description'].replace("/", " "))
            search_issue.save()
        return SearchIssue.objects.all()

    def prepare(self, obj):
        data = super(IssueIndex, self).prepare(obj)
        data['boost'] = 1.5
        return data

class RegistrantIndex(DistinctMixin, indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='name')

    def get_model(self):
        return Registrant

class ClientIndex(DistinctMixin, indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='name')

    def get_model(self):
        return Client

class LobbyistIndex(DistinctMixin, indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='search_document')

    def get_model(self):
        return Lobbyist

class LobbyingRegistrationIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='search_document')

    def get_model(self):
        return LobbyingRegistration

    def index_queryset(self, using=None):
        return LobbyingRegistration.objects.all().distinct('id').prefetch_related('participants__organization', 'participants__person', 'agenda')

    def prepare(self, obj):
        data = super(LobbyingRegistrationIndex, self).prepare(obj)
        data['boost'] = 0.8
        return data