from django.db import models
from django.contrib.auth.models import User
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.models import BaseUserManager
import secrets
from .paystack import Paystack
from .utils import unique_order_id_generator
from django.db.models.signals import pre_save

class CustomUserManager(BaseUserManager):
    """ Manager for user profiles """
    def _create_user(self, email, first_name, last_name, password, **extra_fields):
        """ Create a new user profile """
        if not email:
            raise ValueError('User must have an email address')
        if not password:
            raise ValueError('User must have an Password')

        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name, **extra_fields)

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name,last_name, password, **extra_fields):
        """ Create a new superuser profile """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_email_verified', False)
        extra_fields.setdefault('is_superuser', True)
        return self._create_user(email,first_name,last_name,  password, **extra_fields)

    def create_user(self, email, first_name,last_name, password, **extra_fields):
        """ Create a new superuser profile """
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_email_verified', False)
        return self._create_user(email,first_name,last_name,  password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    """ Database model for users in the system """
    email = models.EmailField(db_index=True,max_length=255, unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)


    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name','last_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

# Create your models here.
class Customer(models.Model):
    user=models.OneToOneField(User,on_delete=models.CASCADE)
    #profile_pic= models.ImageField(upload_to='profile_pic/CustomerProfilePic/',null=True,blank=True)
    #address = models.CharField(max_length=40)
    mobile = models.CharField(max_length=20,null=False)
    @property
    def get_name(self):
        return self.user.first_name+" "+self.user.last_name
    @property
    def get_id(self):
        return self.user.id
    def __str__(self):
        return self.user.first_name

class categories(models.Model):
    category = models.CharField(max_length=50, default="")
    def __str__(self):
        return self.category

class Product(models.Model):
    name=models.CharField(max_length=40)
    product_image= models.ImageField(upload_to='product_image/',null=True,blank=True)
    category = models.ForeignKey(categories, on_delete=models.CASCADE)
    price = models.PositiveIntegerField()
    description=models.CharField(max_length=40)
    quantity=models.IntegerField(default=1)
    def __str__(self):
        return self.name



class Feedback(models.Model):
    name=models.CharField(max_length=40)
    feedback=models.CharField(max_length=500)
    date= models.DateField(auto_now_add=True,null=True)
    def __str__(self):
        return self.name



class Payment(models.Model):
    amount = models.PositiveIntegerField()
    ref = models.CharField(max_length=200)
    email = models.EmailField()
    verified = models.BooleanField(default=False)
    date_created = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ('-date_created',)

    def __str__(self) -> str:
        return f"Payment: {self.amount}"

    def save(self, *args, **kwargs) -> None:
        while not self.ref:
            ref = secrets.token_urlsafe(50)
            object_with_similar_ref = Payment.objects.filter(ref=ref)
            if not object_with_similar_ref:
                self.ref = ref
        super().save(*args, **kwargs)
    
    def amount_value(self) -> int:
        return self.amount *100 

    def verify_payment(self):
        paystack = Paystack()
        status, result = paystack.verify_payment(self.ref, self.amount)
        if status:
            if result['amount'] / 100 == self.amount:
                self.verified = True
            self.save()
        if self.verified:
            return True
            return False

class Orders(models.Model):
    STATUS =(
        ('Pending','Pending'),
        ('Order Confirmed','Order Confirmed'),
        ('Out for Delivery','Out for Delivery'),
        ('Delivered','Delivered'),
    )
    ref_code = models.CharField(max_length=20, blank=True, null=True)
    Payment = models.ForeignKey('Payment',on_delete=models.CASCADE,null=True)
    customer=models.ForeignKey('Customer', on_delete=models.CASCADE,null=True)
    product=models.ForeignKey('Product',on_delete=models.CASCADE,null=True)
    address = models.CharField(max_length=500,null=True)
    mobile = models.CharField(max_length=20,null=True)
    order_date= models.DateField(auto_now_add=True,null=True)
    status=models.CharField(max_length=50,null=True,choices=STATUS)
    quantity = models.PositiveIntegerField(default=1)
    
    def save(self, *args, **kwargs) -> None:
        while not self.ref_code:
            ref = secrets.token_urlsafe(5)
            object_with_similar_ref = Payment.objects.filter(ref=ref)
            if not object_with_similar_ref:
                self.ref_code = ref
        super().save(*args, **kwargs)