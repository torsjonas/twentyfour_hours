# Generated by Django 2.2.3 on 2019-07-12 05:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_match_division'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='disable_in_playoffs',
            field=models.BooleanField(default=False),
        ),
    ]
