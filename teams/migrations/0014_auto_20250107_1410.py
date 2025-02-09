# Generated by Django 5.1.1 on 2025-01-07 14:10

from django.db import migrations


def create_postcommentreplystatus(apps, schema_editor):
    PostCommentReplyStatus = apps.get_model('teams', 'PostCommentReplyStatus')
    PostCommentReplyStatus.objects.get_or_create(name='created')
    PostCommentReplyStatus.objects.get_or_create(name='deleted')

    Language = apps.get_model('teams', 'Language')
    english = Language.objects.get(name='English')
    korean = Language.objects.get(name='Korean')

    PostCommentReplyStatusDisplayName = apps.get_model('teams', 'PostCommentReplyStatusDisplayName')
    PostCommentReplyStatusDisplayName.objects.get_or_create(post_comment_reply_status=PostCommentReplyStatus.objects.get(name='created'), language=english, defaults={'display_name': 'Create'})
    PostCommentReplyStatusDisplayName.objects.get_or_create(post_comment_reply_status=PostCommentReplyStatus.objects.get(name='deleted'), language=english, defaults={'display_name': 'Delete'})

    PostCommentReplyStatusDisplayName.objects.get_or_create(post_comment_reply_status=PostCommentReplyStatus.objects.get(name='created'), language=korean, defaults={'display_name': '생성하기'})
    PostCommentReplyStatusDisplayName.objects.get_or_create(post_comment_reply_status=PostCommentReplyStatus.objects.get(name='deleted'), language=korean, defaults={'display_name': '삭제하기'})


class Migration(migrations.Migration):
    dependencies = [
        ('teams', '0013_postcommentreplystatusdisplayname'),
    ]

    operations = [
        migrations.RunPython(create_postcommentreplystatus),
    ]
