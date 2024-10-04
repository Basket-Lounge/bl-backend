# Generated by Django 5.1.1 on 2024-10-04 14:48

from django.db import migrations

def create_roles(apps, schema_editor):
    Role = apps.get_model('users', 'Role')
    Role.objects.create(name='admin', description='The highest role', weight=1)
    Role.objects.create(name='site_moderator', description='Moderator of the site', weight=2)
    Role.objects.create(name='chat_moderator', description='Moderator of the chat', weight=3)
    Role.objects.create(name='user', description='Regular user', weight=4)
    Role.objects.create(name='deactivated', description='Deactivated user', weight=5)
    Role.objects.create(name='banned', description='Banned user', weight=6)


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_alter_role_description_alter_role_name_directmessage_and_more'),
    ]

    operations = [
        migrations.RunPython(create_roles),
    ]
