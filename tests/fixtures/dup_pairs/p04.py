# label: distinct
# sample: random
# a: django/contrib/admin/filters.py:275 get_facet_counts
# b: django/contrib/admin/filters.py:412 get_facet_counts
# why: Same Count-dict idiom but different choice sources, key schemes and empty-choice handling; behavior differs per filter type.
def get_facet_counts(self, pk_attname, filtered_qs):
    counts = {
        f"{pk_val}__c": models.Count(
            pk_attname, filter=models.Q(**{self.lookup_kwarg: pk_val})
        )
        for pk_val, _ in self.lookup_choices
    }
    if self.include_empty_choice:
        counts["__c"] = models.Count(
            pk_attname, filter=models.Q(**{self.lookup_kwarg_isnull: True})
        )
    return counts


def get_facet_counts(self, pk_attname, filtered_qs):
    return {
        f"{i}__c": models.Count(
            pk_attname,
            filter=models.Q(
                (self.lookup_kwarg, value)
                if value is not None
                else (self.lookup_kwarg_isnull, True)
            ),
        )
        for i, (value, _) in enumerate(self.field.flatchoices)
    }
