from datetime import datetime
from django.db import transaction
from inboxen.models import Tag, Alias, Domain, Email
from celery import task

@task(default_retry_delay=5 * 60) # 5 minutes
@transaction.commit_on_success
def delete_alias(email, user):
    alias, domain = email.split("@", 1)
    
    try:
        domain = Domain.objects.get(domain=domain)
        alias = Alias.objects.get(alias=alias, domain=domain, user=user, deleted=False)
    except Alias.DoesNotExist:
        return False

    # delete emails
    emails = Email.objects.filter(inbox=alias, user=user).iterator()

    # it seems to cause problems if you do QuerySet.delete()
    # this seems to be more efficiant when we have a lot of data
    for email in emails:
        delete_email(email).delay()

    # delete tags
    tags = Tag.objects.filter(alias=alias)
    tags.delete()

    # okay now mark the alias as deleted
    alias.deleted = True
    alias.created = datetime.fromtimestamp(0)
    alias.save()

    return True

@task(rate_limit=20)
def delete_email(email):
    email.delete()

@task(default_retry_delay=10 * 60)
def delete_account(user):
    # first we have to transfer all the Aliases
    pass