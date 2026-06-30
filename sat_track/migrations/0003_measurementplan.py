from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('sat_track', '0002_event_satellite_key'),
    ]

    operations = [
        migrations.CreateModel(
            name='MeasurementPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('crop_type', models.CharField(
                    choices=[
                        ('winter_wheat', 'Winter Wheat / Pszenica ozima'),
                        ('spring_barley', 'Spring Barley / Jęczmień jary'),
                        ('rapeseed', 'Winter Rapeseed / Rzepak ozimy'),
                        ('corn', 'Corn (Maize) / Kukurydza'),
                        ('sugar_beet', 'Sugar Beet / Burak cukrowy'),
                        ('potato', 'Potato / Ziemniak'),
                        ('other', 'Other / Inne'),
                    ],
                    default='winter_wheat',
                    max_length=30,
                )),
                ('season_year', models.IntegerField(default=2026)),
                ('area_geojson', models.TextField(blank=True, default='')),
                ('fields_json', models.TextField(blank=True, default='[]')),
                ('home_lat', models.FloatField(blank=True, null=True)),
                ('home_lon', models.FloatField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='measurement_plans',
                    to='sat_track.useraccountmodel',
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
