# label: duplicate
# sample: sought
# a: django/core/checks/security/sessions.py:67 check_session_cookie_secure
# b: django/core/checks/security/sessions.py:81 check_session_cookie_httponly
# why: Identical session cookie deploy check with a different setting and different warning constants.
@register(Tags.security, deploy=True)
def check_session_cookie_secure(app_configs, **kwargs):
    if settings.SESSION_COOKIE_SECURE is True:
        return []
    errors = []
    if _session_app():
        errors.append(W010)
    if _session_middleware():
        errors.append(W011)
    if len(errors) > 1:
        errors = [W012]
    return errors


@register(Tags.security, deploy=True)
def check_session_cookie_httponly(app_configs, **kwargs):
    if settings.SESSION_COOKIE_HTTPONLY is True:
        return []
    errors = []
    if _session_app():
        errors.append(W013)
    if _session_middleware():
        errors.append(W014)
    if len(errors) > 1:
        errors = [W015]
    return errors
