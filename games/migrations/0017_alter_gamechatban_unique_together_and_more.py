# Generated by Django 5.1.1 on 2025-02-14 11:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0016_remove_gamechatban_unique_chat_ban_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='gamechatban',
            unique_together=set(),
        ),
        migrations.AlterUniqueTogether(
            name='gamechatmute',
            unique_together=set(),
        ),
    ]
