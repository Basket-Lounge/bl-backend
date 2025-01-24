# Generated by Django 5.1.1 on 2025-01-21 17:21

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0011_inquirymessage_management__inquiry_9bb34c_idx_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddIndex(
            model_name='inquiry',
            index=models.Index(fields=['-updated_at'], name='management__updated_515ea5_idx'),
        ),
        migrations.AddIndex(
            model_name='inquirymoderator',
            index=models.Index(fields=['inquiry', 'moderator'], name='management__inquiry_d46fe0_idx'),
        ),
        migrations.AddIndex(
            model_name='inquirymoderator',
            index=models.Index(fields=['last_read_at'], name='management__last_re_6d61a0_idx'),
        ),
        migrations.AddIndex(
            model_name='inquirymoderatormessage',
            index=models.Index(fields=['created_at'], name='management__created_062093_idx'),
        ),
        migrations.AddConstraint(
            model_name='inquirymoderator',
            constraint=models.UniqueConstraint(fields=('inquiry', 'moderator'), name='unique_inquiry_moderator'),
        ),
    ]
