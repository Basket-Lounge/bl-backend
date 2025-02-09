# Generated by Django 5.1.1 on 2024-11-07 07:42

from django.db import migrations

STATUSES = [
    {'name': 'created'},
    {'name': 'deleted'},
    {'name': 'blocked'},
]

def create_status(apps, schema_editor):
    UserChatStatus = apps.get_model('users', 'UserChatStatus')
    existing_statuses = UserChatStatus.objects.values_list('name', flat=True)
    statuses_to_create = [status for status in STATUSES if status['name'] not in existing_statuses]

    if statuses_to_create:
        try:
            UserChatStatus.objects.bulk_create([UserChatStatus(**status) for status in statuses_to_create])
        except Exception as e:
            raise RuntimeError(f"Error creating statuses: {e}")

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_remove_userchatparticipantmessage_read_by_receiver'),
    ]

    operations = [
        migrations.RunPython(create_status),
    ]
