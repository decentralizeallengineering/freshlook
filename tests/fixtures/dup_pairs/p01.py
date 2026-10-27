# label: distinct
# sample: random
# a: django/contrib/contenttypes/fields.py:147 get_content_type
# b: django/contrib/contenttypes/fields.py:520 get_content_type
# why: Different signatures and logic: one dispatches on obj/id/model with db_manager, the other returns the field's own model content type in one call.
def get_content_type(self, obj=None, id=None, using=None, model=None):
    if obj is not None:
        return ContentType.objects.db_manager(obj._state.db).get_for_model(
            obj, for_concrete_model=self.for_concrete_model
        )
    elif id is not None:
        return ContentType.objects.db_manager(using).get_for_id(id)
    elif model is not None:
        return ContentType.objects.db_manager(using).get_for_model(
            model, for_concrete_model=self.for_concrete_model
        )
    else:
        # This should never happen. I love comments like this, don't you?
        raise Exception("Impossible arguments to GFK.get_content_type!")


def get_content_type(self):
    """
    Return the content type associated with this field's model.
    """
    return ContentType.objects.get_for_model(
        self.model, for_concrete_model=self.for_concrete_model
    )
