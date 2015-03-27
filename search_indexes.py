from haystack import indexes
from models import *

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

class RegistrantIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='name')

    def get_model(self):
        return Registrant

class ClientIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='name')

    def get_model(self):
        return Client

class LobbyistIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='search_document')

    def get_model(self):
        return Lobbyist

class LobbyingRegistrationIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr='search_document')

    def get_model(self):
        return LobbyingRegistration

    def index_queryset(self, using=None):
        return LobbyingRegistration.objects.all().prefetch_related('participants__organization', 'participants__person', 'agenda')