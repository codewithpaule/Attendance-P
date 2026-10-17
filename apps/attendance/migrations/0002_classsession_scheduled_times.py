from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="classsession",
            name="scheduled_start_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="classsession",
            name="scheduled_end_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]