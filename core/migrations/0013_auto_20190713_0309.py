# Generated by Django 2.2.3 on 2019-07-13 01:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_auto_20190713_0307'),
    ]

    operations = [
        migrations.CreateModel(
            name='MatchPoints',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('points', models.IntegerField()),
            ],
            options={
                'verbose_name_plural': 'Match points',
            },
        ),
        migrations.RemoveField(
            model_name='tournament',
            name='match_points',
        ),
    ]
