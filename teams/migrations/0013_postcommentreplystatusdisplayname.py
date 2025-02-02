# Generated by Django 5.1.1 on 2025-01-07 14:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0012_alter_post_title'),
    ]

    operations = [
        migrations.CreateModel(
            name='PostCommentReplyStatusDisplayName',
            fields=[
                ('id', models.SmallAutoField(primary_key=True, serialize=False)),
                ('display_name', models.CharField(max_length=128)),
                ('language', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='teams.language')),
                ('post_comment_reply_status', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='teams.postcommentreplystatus')),
            ],
            options={
                'unique_together': {('post_comment_reply_status', 'language')},
            },
        ),
    ]
