from django.contrib import admin
from .models import Customer,Product,Orders,Feedback,categories,User,Payment,Featured
# Register your models here.
class CustomerAdmin(admin.ModelAdmin):
    pass
admin.site.register(Customer, CustomerAdmin)

class ProductAdmin(admin.ModelAdmin):
    pass
admin.site.register(Product, ProductAdmin)

class OrderAdmin(admin.ModelAdmin):
    pass
admin.site.register(Orders, OrderAdmin)

class FeedbackAdmin(admin.ModelAdmin):
    pass
admin.site.register(Feedback, FeedbackAdmin)
class CategoryAdmin(admin.ModelAdmin):
    pass
admin.site.register(categories, ProductAdmin)
# Register your models here.

admin.site.register(User)
admin.site.register(Payment)
admin.site.register(Featured)
