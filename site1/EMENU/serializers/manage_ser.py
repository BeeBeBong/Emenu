from rest_framework import serializers
from ..models import Revenue, Booking, Notification

class RevenueSerializer(serializers.ModelSerializer):
    orderId = serializers.IntegerField(source='order.id', read_only=True)
    paidAt = serializers.DateTimeField(source='paid_at', read_only=True)
    class Meta: model = Revenue; fields = ['id', 'orderId', 'method', 'amount', 'paidAt']

class BookingSerializer(serializers.ModelSerializer):
    class Meta: model = Booking; fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    tableName = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    class Meta: model = Notification; fields = ['id', 'type', 'tableName', 'status', 'created_at'] 
    def get_tableName(self, obj): return f" {obj.table.number}" if obj.table else "Không xác định"
    def get_status(self, obj): return "read" if obj.is_read else "unread"
    def get_type(self, obj): return "PAYMENT_REQUEST"