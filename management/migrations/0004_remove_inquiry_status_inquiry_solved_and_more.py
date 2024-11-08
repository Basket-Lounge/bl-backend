# Generated by Django 5.1.1 on 2024-11-08 08:41

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('management', '0003_auto_20241108_0824'),
        ('teams', '0006_alter_postcommentreply_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='inquiry',
            name='status',
        ),
        migrations.AddField(
            model_name='inquiry',
            name='solved',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='InquiryTypeDisplayName',
            fields=[
                ('id', models.SmallAutoField(primary_key=True, serialize=False)),
                ('display_name', models.CharField(max_length=512)),
                ('inquiry_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='management.inquirytype')),
                ('language', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='teams.language')),
            ],
        ),
        migrations.DeleteModel(
            name='InquiryStatus',
        ),
    ]