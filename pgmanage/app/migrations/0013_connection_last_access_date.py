# Generated by Django 3.2.18 on 2023-11-16 16:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0012_userdetails_autocomplete'),
    ]

    operations = [
        migrations.AddField(
            model_name='connection',
            name='last_access_date',
            field=models.DateTimeField(null=True),
        ),
    ]
