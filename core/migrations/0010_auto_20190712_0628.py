# Generated by Django 2.2.3 on 2019-07-12 06:28

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_game_ipdb_id'),
    ]

    operations = [
        migrations.RenameField(
            model_name='game',
            old_name='enabled_in_playoffs',
            new_name='is_active_in_playoffs',
        ),
        migrations.RemoveField(
            model_name='game',
            name='ipdb_id',
        ),
    ]