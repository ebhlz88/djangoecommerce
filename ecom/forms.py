from dataclasses import field
from django import forms
from ecom.models import User
from . import models

class loginForm(forms.Form):
    email = forms.EmailField()
    password=forms.CharField(widget=forms.PasswordInput())



class CustomerUserForm(forms.ModelForm):
    password=forms.CharField(widget=forms.PasswordInput())
    confirm_password=forms.CharField(widget=forms.PasswordInput())
    class Meta:
        model=User
        fields=['first_name','last_name','email','password','is_email_verified']
        widgets = {
        'password': forms.PasswordInput()
        }
        
class CustomerForm(forms.ModelForm):
    class Meta:
        model=models.Customer
        fields=['mobile']

class ProductForm(forms.ModelForm):
    class Meta:
        model=models.Product
        fields=['name','price','description','product_image','quantity','category']

#address of shipment
class AddressForm(forms.Form):
    Mobile= forms.IntegerField()
    Address = forms.CharField(max_length=500)

class FeedbackForm(forms.ModelForm):
    class Meta:
        model=models.Feedback
        fields=['name','feedback']

#for updating status of order
class OrderForm(forms.ModelForm):
    class Meta:
        model=models.Orders
        fields=['status']

#for contact us page
class ContactusForm(forms.Form):
    Name = forms.CharField(max_length=30)
    Email = forms.EmailField()
    Message = forms.CharField(max_length=500,widget=forms.Textarea(attrs={'rows': 3, 'cols': 30}))


class CategoriesForm(forms.ModelForm):
    class Meta:
        model = models.categories
        fields = "__all__"

class PaymentForm(forms.ModelForm):
    class Meta:
        model = models.Payment
        fields  = ("amount", "email")