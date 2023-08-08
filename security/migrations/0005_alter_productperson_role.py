# Generated by Django 4.2.2 on 2023-08-03 07:44

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("security", "0004_productperson_delete_organisationperson"),
    ]

    operations = [
        migrations.AlterField(
            model_name="productperson",
            name="role",
            field=models.IntegerField(
                choices=[
                    (0, "Follower"),
                    (1, "Contributor"),
                    (2, "Manager"),
                    (3, "Admin"),
                ],
                default=0,
            ),
        ),
    ]