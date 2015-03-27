# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SearchIssue',
            fields=[
                ('id', models.CharField(max_length=8, serialize=False, primary_key=True)),
                ('description', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
