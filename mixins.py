from django.utils import feedgenerator
from django.views.generic import TemplateView, ListView, RedirectView
from django.core.urlresolvers import reverse
from django.template import Context, loader
from django.http import HttpResponse
from braces.views import OrderableListMixin
from models import *
import csv, re

class DisclosureRssMixin(object):
    paginate_by = 20

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset()
        context = self.get_context_data(**kwargs)
        object_type, object_name = None, None
        if 'object' in context:
            if type(context['object']) == dict:
                object_type, object_name = "issue", context['object']['description']
            else:
                object_type, object_name = context['object']._meta.model_name, context['object'].name
        feed = feedgenerator.Rss201rev2Feed(
            title=u"Latest lobbying registrations" + (" for %s \"%s\"" % (object_type, object_name) if object_type else ""),
            link=self.request.build_absolute_uri().replace(".rss", ""),
            description=u"The latest lobbyist registrations submitted to the U.S. Senate",
            feed_url=self.request.build_absolute_uri()
        )
        template = loader.get_template("templates/registration_feed_item.html")
        for obj in context['object_list']:
            clients = obj.clients
            registrants = obj.registrants
            feed.add_item(
                title='%s registered to lobby for %s' % (registrants[0].name if registrants else "A registrant", clients[0].name if clients else "a client"),
                link=self.request.build_absolute_uri(reverse('registration-detail', args=(obj.short_uuid,))),
                description=template.render(Context({'object': obj})).replace("\n", " "),
                pubdate=obj.start_time
            )

        response = HttpResponse(content_type="application/rss+xml")
        feed.write(response, 'utf-8')

        return response

source_url_parser = re.compile(r"filingID=(?P<filingID>[0-9a-fA-F-]+)&filingTypeID=(?P<filingTypeID>\d+)")
class DisclosureCsvMixin(object):
    # get everything
    paginate_by = 1000000

    def get(self, request, *args, **kwargs):
        self.object_list = self.get_queryset().prefetch_related('sources')
        context = self.get_context_data(**kwargs)

        response = HttpResponse(content_type="text/csv")

        outcsv = csv.DictWriter(response, ['senate_id', 'registration_type' , 'client', 'registrant', 'received', 'issues', 'specific_issue'])
        outcsv.writeheader()

        for obj in context['object_list']:
            clients = obj.clients
            registrants = obj.registrants
            
            source_url = obj.sources.all()[0].url
            filing_info = source_url_parser.search(source_url).groupdict()

            outcsv.writerow(dict(
                senate_id=filing_info.get('filingID', '').upper(),
                registration_type=filing_types_by_code[filing_info.get('filingTypeID', 1)]['name'],
                client=clients[0].name if clients else "",
                registrant=registrants[0].name if registrants else "",
                received=obj.start_time.isoformat(),
                issues="|".join([issue['description'] for issue in obj.issues]),
                specific_issue="; ".join([specific_issue for specific_issue in obj.specific_issues])
            ))

        return response


class EnhancedOrderableListView(OrderableListMixin, ListView):
    order_by_default = {}
    order_mapping = {}

    def get_ordered_queryset(self, queryset=None):
        get_order_by = self.request.GET.get("order_by")

        order_by = get_order_by if get_order_by in self.get_orderable_columns() else self.get_orderable_columns_default()

        self.order_by = order_by
        self.ordering = self.request.GET.get("ordering", self.order_by_default.get(self.order_by, "asc"))

        order_by = self.order_mapping.get(order_by, order_by)
        if order_by and self.ordering == "desc":
            order_by = "-" + order_by

        return queryset.order_by(order_by)