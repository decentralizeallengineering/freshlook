# label: distinct
# sample: random
# a: django/contrib/admin/widgets.py:42 get_context
# b: django/contrib/auth/views.py:111 get_context_data
# why: Different contexts: widget attrs for select filter vs auth view redirect/site context.
def get_context(self, name, value, attrs):
    context = super().get_context(name, value, attrs)
    context["widget"]["attrs"]["class"] = "selectfilter"
    if self.is_stacked:
        context["widget"]["attrs"]["class"] += "stacked"
    context["widget"]["attrs"]["data-field-name"] = self.verbose_name
    context["widget"]["attrs"]["data-is-stacked"] = int(self.is_stacked)
    return context


def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    current_site = get_current_site(self.request)
    context.update(
        {
            self.redirect_field_name: self.get_redirect_url(),
            "site": current_site,
            "site_name": current_site.name,
            **(self.extra_context or {}),
        }
    )
    return context
