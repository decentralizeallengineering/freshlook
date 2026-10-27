# label: duplicate
# sample: sought
# a: django/core/mail/__init__.py:118 mail_admins
# b: django/core/mail/__init__.py:138 mail_managers
# why: Identical mail sending logic with ADMINS vs MANAGERS setting and messages swapped.
def mail_admins(
    subject, message, fail_silently=False, connection=None, html_message=None
):
    """Send a message to the admins, as defined by the ADMINS setting."""
    if not settings.ADMINS:
        return
    if not all(isinstance(a, (list, tuple)) and len(a) == 2 for a in settings.ADMINS):
        raise ValueError("The ADMINS setting must be a list of 2-tuples.")
    mail = EmailMultiAlternatives(
        "%s%s" % (settings.EMAIL_SUBJECT_PREFIX, subject),
        message,
        settings.SERVER_EMAIL,
        [a[1] for a in settings.ADMINS],
        connection=connection,
    )
    if html_message:
        mail.attach_alternative(html_message, "text/html")
    mail.send(fail_silently=fail_silently)


def mail_managers(
    subject, message, fail_silently=False, connection=None, html_message=None
):
    """Send a message to the managers, as defined by the MANAGERS setting."""
    if not settings.MANAGERS:
        return
    if not all(isinstance(a, (list, tuple)) and len(a) == 2 for a in settings.MANAGERS):
        raise ValueError("The MANAGERS setting must be a list of 2-tuples.")
    mail = EmailMultiAlternatives(
        "%s%s" % (settings.EMAIL_SUBJECT_PREFIX, subject),
        message,
        settings.SERVER_EMAIL,
        [a[1] for a in settings.MANAGERS],
        connection=connection,
    )
    if html_message:
        mail.attach_alternative(html_message, "text/html")
    mail.send(fail_silently=fail_silently)
