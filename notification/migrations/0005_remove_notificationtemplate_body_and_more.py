# Generated by Django 5.1.1 on 2025-01-02 07:37

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notification', '0004_notification_data'),
        ('teams', '0012_alter_post_title'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='notificationtemplate',
            name='body',
        ),
        migrations.CreateModel(
            name='NotificationTemplateBody',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('body', models.TextField()),
                ('language', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='teams.language')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='notification.notificationtemplate')),
            ],
            options={
                'unique_together': {('template', 'language')},
            },
        ),
    ]
