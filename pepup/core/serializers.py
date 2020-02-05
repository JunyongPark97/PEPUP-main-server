from rest_framework import serializers


class CommaSeparatedUUIDField(serializers.CharField):
    def to_internal_value(self, data):
        if not data:
            return []
        from uuid import UUID
        return [UUID(x) for x in data.split(',')]


class BlankAbleCommaSeparatedUUIDField(serializers.CharField):
    def to_internal_value(self, data):
        if not data:
            return []
        from uuid import UUID
        return [UUID(x) if x != u'' else '' for x in data.split(',')]


class CommaSeparatedIntegerListField(serializers.CharField):
    def to_internal_value(self, data):
        # string("1, 2, 3, 4, ") => array([1, 2, 3, 4])
        return map(int, filter(lambda x1: x1, [x.strip() for x in data.split(',')]))


class CommaSeparatedStringListField(serializers.CharField):
    def to_internal_value(self, data):
        # string("1, 2, 3, 4, ") => array([1, 2, 3, 4])
        return map(str, filter(lambda x1: x1, [x.strip() for x in data.split(',')]))


# class ClientDeviceIDDefault(object):
#     def set_context(self, serializer_field):
#         try:
#             self.device_id = serializer_field.context['request'].device.device_id
#         except:
#             self.device_id = ''
#
#     def __call__(self):
#         return self.device_id
#
#     def __repr__(self):
#         return unicode_to_repr('%s()' % self.__class__.__name__)


# class ClientIPAddressDefault(object):
#     def set_context(self, serializer_field):
#         self.client_ip, _ = get_client_ip(serializer_field.context['request'])
#
#     def __call__(self):
#         return self.client_ip
#
#     def __repr__(self):
#         return unicode_to_repr('%s()' % self.__class__.__name__)


# class NullableCurrentUserDefault(object):
#     def set_context(self, serializer_field):
#         user = serializer_field.context['request'].user
#         if user.is_anonymous:
#             self.user = None
#         else:
#             self.user = user
#
#     def __call__(self):
#         return self.user
#
#     def __repr__(self):
#         return unicode_to_repr('%s()' % self.__class__.__name__)


# NOT WOKRKING
# class BidirectionalField(serializers.PrimaryKeyRelatedField):
#
#     def __init__(self, *args, **kwargs):
#         self.model = kwargs.pop('model')
#         self.serializer = kwargs.pop('serializer')
#         super(BidirectionalField, self).__init__(*args, **kwargs)
#
#     def to_representation(self, value):
#         pk = super(BidirectionalField, self).to_representation(value)
#         try:
#             item = self.model.objects.get(pk=pk)
#             serializer = self.serializer(item)
#             return serializer.data
#         except self.model.DoesNotExist:
#             return None
#
#     def to_internal_value(self, data):
#         return data

class NestedSerializer(serializers.PrimaryKeyRelatedField, serializers.ModelSerializer):

    # def __init__(self, instance=None, data=empty, **kwargs):
    #     queryset = kwargs.pop('queryset', None)
    #     serializers.PrimaryKeyRelatedField.__init__(self, queryset=queryset, **kwargs)
    #     serializers.ModelSerializer.__init__(self, instance=instance, data=data, **kwargs)

    def to_representation(self, data):
        if self.context.get('nested', 'true') == 'true':
            return serializers.ModelSerializer.to_representation(self, data)
        else:
            return serializers.PrimaryKeyRelatedField.to_representation(self, data)

    def use_pk_only_optimization(self):
        return False


class NullToBlankCharField(serializers.CharField):
    def __init__(self, **kwargs):
        keys = [('allow_blank', True), ('required', False)]
        for key, default_value in keys:
            if key in  kwargs:
                raise Exception('Keyword argument "{}" is redundant for NullToBlankCharField'.format(key))
            kwargs.update({key: default_value})
        super(NullToBlankCharField, self).__init__(**kwargs)

    def run_validation(self, data=serializers.empty):
        if data == '' or data is None:
            return ''
        return super(NullToBlankCharField, self).run_validation(data)


class ReferencibleNestedSerializer(NestedSerializer):

    def to_internal_value(self, data):
        return serializers.PrimaryKeyRelatedField.to_internal_value(self, data)


class PseudoSerializer(serializers.Serializer):
    no_post_data = serializers.CharField(max_length=1)

    def create(self, validated_data):
        raise Exception('DO NOT CALL THIS SERIALIZER!')

    def update(self, instance, validated_data):
        raise Exception('DO NOT CALL THIS SERIALIZER!')
