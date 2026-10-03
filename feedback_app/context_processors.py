from django.conf import settings


def demo_accounts(request):
    return {"show_demo_accounts": settings.DEBUG}
