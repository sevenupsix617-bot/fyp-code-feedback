from pathlib import Path

from django.conf import settings


def demo_accounts(request):
    # Identify known local demo environments without labelling every record real.
    notice = settings.REPORT_DATA_NOTICE
    if not notice:
        database_name = Path(str(settings.DATABASES["default"]["NAME"])).name
        notice = {
            "fictional_class.sqlite3": "Demonstration dataset — 30 fictional students; scripted feedback, not research results.",
            "record_snapshot.sqlite3": "Practice snapshot — seeded history and saved submissions; new submissions use the live feedback workflow.",
        }.get(database_name, "")
    return {
        "show_demo_accounts": settings.DEBUG,
        "report_data_notice": notice,
    }
