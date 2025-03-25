class DynamicFieldsSerializerMixin(object):
    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop('fields', None)
        fields_exclude = kwargs.pop("fields_exclude", None)

        allowed = None
        excluded = None

        # Instantiate the superclass normally
        super(DynamicFieldsSerializerMixin, self).__init__(*args, **kwargs)

        existing = set(self.fields.keys())

        if fields_exclude is not None:
            excluded = set(fields_exclude)
            for field_name in excluded.intersection(existing):
                self.fields.pop(field_name)

        if fields is not None:
            allowed = set(fields)
            if excluded is not None:
                allowed.difference_update(excluded)
            # Drop any fields that are not specified in the `fields` argument.
            for field_name in existing - allowed:
                self.fields.pop(field_name)