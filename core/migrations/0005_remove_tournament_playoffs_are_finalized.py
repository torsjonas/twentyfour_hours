# Generated by Django 2.2.3 on 2019-07-12 04:14

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_auto_20190711_1636'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='tournament',
            name='playoffs_are_finalized',
        ),
    ]
