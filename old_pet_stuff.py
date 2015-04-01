# this stuff is poached and only slightly modified from the reporting site

from django.contrib.syndication.views import Feed
from django.core.urlresolvers import reverse
from django.utils.dateformat import format as date_format
from django.http import Http404, HttpResponse

from models import get_all_pet_records

import datetime, json, csv

class PostEmploymentFeed(Feed):
    title = 'Upcoming lobbying restriction expirations'
    link = '/post-employment'
    description = 'Upcoming expirations of lobbying restrictions for Senate and House members and staffers'

    def items(self):
        cutoff = datetime.date.today() + datetime.timedelta(7)
        
        return sorted([item for item in get_all_pet_records() if item['end_time'].date() >= datetime.date.today() and item['end_time'].date() <= cutoff], key=lambda item: item['end_time'])

    def item_link(self, item):
        return reverse('pet-detail', args=[item['pk']])

    def item_description(self, item):
        return '%s left the office "%s" in the %s on %s. The lobbying restriction ends on %s' % (
                                    item['name'],
                                    item['office'],
                                    item['body'],
                                    date_format(item['start_time'], 'F j, Y'),
                                    date_format(item['end_time'], 'F j, Y')
                                )

    def item_pubdate(self, item):
        date = item['end_time'].date() - datetime.timedelta(7)
        return datetime.datetime(date.year, date.month, date.day)

    def item_title(self, item):
        return 'Lobbying restriction on %s ends %s' % (item['name'],
                                                       date_format(item['end_time'], 'M. j, Y'))

def willard_postemployment_api(request, format):
    allowed_formats = ('csv', 'json', )
    if format not in allowed_formats:
        raise Http404

    object_list = []
    for obj in sorted(get_all_pet_records(), key=lambda item: item['end_time']):
        object_list.append({'last': obj['last_name'],
                            'first': obj['first_name'],
                            'middle': obj['middle_name'],
                            'body': obj['body'],
                            'office': obj['office'],
                            'restriction_start': obj['start_time'].date().isoformat(),
                            'restriction_end': obj['end_time'].date().isoformat(),
                            })

    if format == 'json':
        return HttpResponse(json.dumps(object_list), content_type='application/json')

    elif format == 'csv':
        response = HttpResponse(content_type='text/csv')
        fieldnames = ['last', 'first', 'middle', 'body',
                        'office', 'restriction_start', 'restriction_end', ]
        writer = csv.DictWriter(response, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(object_list)
        return response