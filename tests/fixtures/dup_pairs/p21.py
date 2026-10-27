# label: duplicate
# sample: sought
# a: django/contrib/admindocs/views.py:68 get_context_data
# b: django/contrib/admindocs/views.py:105 get_context_data
# why: Same template-library docs walk with variables renamed (tags/filters, tag_name/filter_name) and library.tags vs library.filters.
def get_context_data(self, **kwargs):
    tags = []
    try:
        engine = Engine.get_default()
    except ImproperlyConfigured:
        # Non-trivial TEMPLATES settings aren't supported (#24125).
        pass
    else:
        app_libs = sorted(engine.template_libraries.items())
        builtin_libs = [("", lib) for lib in engine.template_builtins]
        for module_name, library in builtin_libs + app_libs:
            for tag_name, tag_func in library.tags.items():
                title, body, metadata = utils.parse_docstring(tag_func.__doc__)
                title = title and utils.parse_rst(
                    title, "tag", _("tag:") + tag_name
                )
                body = body and utils.parse_rst(body, "tag", _("tag:") + tag_name)
                for key in metadata:
                    metadata[key] = utils.parse_rst(
                        metadata[key], "tag", _("tag:") + tag_name
                    )
                tag_library = module_name.split(".")[-1]
                tags.append(
                    {
                        "name": tag_name,
                        "title": title,
                        "body": body,
                        "meta": metadata,
                        "library": tag_library,
                    }
                )
    return super().get_context_data(**{**kwargs, "tags": tags})


def get_context_data(self, **kwargs):
    filters = []
    try:
        engine = Engine.get_default()
    except ImproperlyConfigured:
        # Non-trivial TEMPLATES settings aren't supported (#24125).
        pass
    else:
        app_libs = sorted(engine.template_libraries.items())
        builtin_libs = [("", lib) for lib in engine.template_builtins]
        for module_name, library in builtin_libs + app_libs:
            for filter_name, filter_func in library.filters.items():
                title, body, metadata = utils.parse_docstring(filter_func.__doc__)
                title = title and utils.parse_rst(
                    title, "filter", _("filter:") + filter_name
                )
                body = body and utils.parse_rst(
                    body, "filter", _("filter:") + filter_name
                )
                for key in metadata:
                    metadata[key] = utils.parse_rst(
                        metadata[key], "filter", _("filter:") + filter_name
                    )
                tag_library = module_name.split(".")[-1]
                filters.append(
                    {
                        "name": filter_name,
                        "title": title,
                        "body": body,
                        "meta": metadata,
                        "library": tag_library,
                    }
                )
    return super().get_context_data(**{**kwargs, "filters": filters})
