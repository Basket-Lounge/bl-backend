# Generated by Django 5.1.1 on 2025-02-14 11:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0013_gamechatmute_disabled'),
    ]

    operations = [
        migrations.AddField(
            model_name='gamechatban',
            name='disabled',
            field=models.BooleanField(default=False),
        ),
    ]
