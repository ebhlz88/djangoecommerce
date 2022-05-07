from audioop import reverse
from base64 import urlsafe_b64decode
from django.shortcuts import render,redirect
from . import forms,models
from django.http import HttpResponseRedirect,HttpResponse
from django.core.mail import send_mail
from django.contrib.auth.models import Group
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib import messages
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import logout, authenticate, login
from django.contrib.auth.signals import user_logged_out,user_logged_in
from math import ceil
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.utils.encoding import force_bytes,force_str,DjangoUnicodeDecodeError
from django.core.mail import EmailMessage
from .utils import account_activation_token
from django.conf import settings
import threading
from datetime import datetime

class EmailThread(threading.Thread):
    def __init__(self, email):
        self.email= email
        threading.Thread.__init__(self)
    def run(self):
        self.email.send()
        

def send_action_email(user, request):
    current_site = get_current_site(request)
    email_subject = 'Activate you email'
    email_body = render_to_string('ecom/confirm_email.html',{
        'user': user,
        'domain':current_site,
        'uid': urlsafe_base64_encode(force_bytes(user.id)),
        'token': account_activation_token.make_token(user)
    }
    )
    email =  EmailMessage(subject=email_subject,body=email_body,from_email=settings.EMAIL_FROM_USER,to=[user.email])
    EmailThread(email).start()


def send_order_confirmation_email(user,product_names, request):
    email_subject = 'An order Placed By '+ user.email
    email_body = render_to_string('ecom/order_place_email.html',{
        'user': user,
        'prod_names':product_names
    }
    )
    email =  EmailMessage(subject=email_subject,body=email_body,from_email=settings.EMAIL_FROM_USER,to=[settings.EMAIL_FROM_USER])
    EmailThread(email).start()

def getProdswithCats():
        allProds = []
        catprods = models.Product.objects.values('category', 'id')
        cats = {item['category'] for item in catprods}
        for cat in cats:
            prod = models.Product.objects.filter(category=cat)
            n = len(prod)
            nSlides = n // 4 + ceil((n / 4) - (n // 4))
            allProds.append([prod, range(1, nSlides), nSlides])
        return allProds



def corousal(request):
    categories= models.categories.objects.all()
    return render(request, 'ecom/home.html', {'categories':categories,'allProds':getProdswithCats()})


def home_view(request):
    products=models.Product.objects.all()
    categories= models.categories.objects.all()
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return render(request,'ecom/index.html',{'products':products,'product_count_in_cart':product_count_in_cart,'categories':categories})


#for showing login button for admin
def adminclick_view(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('afterlogin')
    return HttpResponseRedirect('adminlogin')


def customer_signup_view(request):
    userForm=forms.CustomerUserForm()
    customerForm=forms.CustomerForm()
    mydict={'userForm':userForm,'customerForm':customerForm}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST)
        customerForm=forms.CustomerForm(request.POST,request.FILES)
        if userForm.is_valid() and customerForm.is_valid():
            password1 = userForm.cleaned_data['password']
            password2 = userForm.cleaned_data['confirm_password']
            is_email_verified = userForm.cleaned_data['is_email_verified']
            if(password1==password2):
                #render(request, 'ecom/confirm_email.html',{'text':'text'})
                user=userForm.save(commit=False)
                user.is_email_verified = False
                user.save()
                user.set_password(user.password)
                user.save()
                send_action_email(user,request)
                customer=customerForm.save(commit=False)
                customer.user=user
                customer.save()
                my_customer_group = Group.objects.get_or_create(name='CUSTOMER')
                my_customer_group[0].user_set.add(user)
                
                form = forms.loginForm()
                messages.success(request,'Verification Link sent By mail please check')
                return render(request,'ecom/customerlogin.html',{'form':form})
            else:
                messages.info(request, 'Password not matching')


    return render(request,'ecom/customersignup.html',context=mydict)

#-----------for checking user iscustomer
def is_customer(user):
    return user.groups.filter(name='CUSTOMER').exists()



#---------AFTER ENTERING CREDENTIALS WE CHECK WHETHER USERNAME AND PASSWORD IS OF ADMIN,CUSTOMER
def afterlogin_view(request):
    if is_customer(request.user):
        return redirect('customer-home')
    else:
        return redirect('admin-dashboard')

#---------------------------------------------------------------------------------
#------------------------ ADMIN RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
@login_required(login_url='adminlogin')
@staff_member_required
def admin_dashboard_view(request):
    # for cards on dashboard
    customercount=models.Customer.objects.all().count()
    productcount=models.Product.objects.all().count()
    ordercount=models.Orders.objects.all().count()

    # for recent order tables
    orders=models.Orders.objects.all()
    ordered_products=[]
    ordered_bys=[]
    for order in orders:
        ordered_product=models.Product.objects.all().filter(id=order.product.id)
        ordered_by=models.Customer.objects.all().filter(id = order.customer.id)
        ordered_products.append(ordered_product)
        ordered_bys.append(ordered_by)

    mydict={
    'customercount':customercount,
    'productcount':productcount,
    'ordercount':ordercount,
    'data':zip(ordered_products,ordered_bys,orders),
    }
    return render(request,'ecom/admin_dashboard.html',context=mydict)


# admin view customer table
@login_required(login_url='adminlogin')
@staff_member_required
def view_customer_view(request):
    customers=models.Customer.objects.all()
    return render(request,'ecom/view_customer.html',{'customers':customers})

# admin delete customer
@login_required(login_url='adminlogin')
@staff_member_required
def delete_customer_view(request,pk):
    customer=models.Customer.objects.get(id=pk)
    user=models.User.objects.get(id=customer.user_id)
    user.delete()
    customer.delete()
    return redirect('view-customer')

@staff_member_required
@login_required(login_url='adminlogin')
def update_customer_view(request,pk):
    customer=models.Customer.objects.get(id=pk)
    user=models.User.objects.get(id=customer.user_id)
    userForm=forms.CustomerUserForm(instance=user)
    customerForm=forms.CustomerForm(request.FILES,instance=customer)
    mydict={'userForm':userForm,'customerForm':customerForm}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST,instance=user)
        customerForm=forms.CustomerForm(request.POST,instance=customer)
        if userForm.is_valid() and customerForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            customerForm.save()
            return redirect('view-customer')
    return render(request,'ecom/admin_update_customer.html',context=mydict)

# admin view the product
@login_required(login_url='adminlogin')
@staff_member_required
def admin_products_view(request):
    products=models.Product.objects.all()
    return render(request,'ecom/admin_products.html',{'products':products})


# admin add product by clicking on floating button
@login_required(login_url='adminlogin')
@staff_member_required
def admin_add_product_view(request):
    productForm=forms.ProductForm()
    if request.method=='POST':
        productForm=forms.ProductForm(request.POST, request.FILES)
        if productForm.is_valid():
            productForm.save()
        return HttpResponseRedirect('admin-products')
    return render(request,'ecom/admin_add_products.html',{'productForm':productForm})


@login_required(login_url='adminlogin')
@staff_member_required
def delete_product_view(request,pk):
    product=models.Product.objects.get(id=pk)
    product.delete()
    return redirect('admin-products')


@login_required(login_url='adminlogin')
@staff_member_required
def update_product_view(request,pk):
    product=models.Product.objects.get(id=pk)
    productForm=forms.ProductForm(instance=product)
    if request.method=='POST':
        productForm=forms.ProductForm(request.POST,request.FILES,instance=product)
        if productForm.is_valid():
            productForm.save()
            return redirect('admin-products')
    return render(request,'ecom/admin_update_product.html',{'productForm':productForm})


@login_required(login_url='adminlogin')
@staff_member_required
def admin_view_booking_view(request):
    orders=models.Orders.objects.all()
    ordered_products=[]
    ordered_bys=[]
    for order in orders:
        ordered_product=models.Product.objects.all().filter(id=order.product.id)
        ordered_by=models.Customer.objects.all().filter(id = order.customer.id)
        ordered_products.append(ordered_product)
        ordered_bys.append(ordered_by)
    return render(request,'ecom/admin_view_booking.html',{'data':zip(ordered_products,ordered_bys,orders)})


@login_required(login_url='adminlogin')
@staff_member_required
def delete_order_view(request,pk):
    order=models.Orders.objects.get(id=pk)
    order.delete()
    return redirect('admin-view-booking')

# for changing status of order (pending,delivered...)
@login_required(login_url='adminlogin')
@staff_member_required
def update_order_view(request,pk):
    order=models.Orders.objects.get(id=pk)
    orderForm=forms.OrderForm(instance=order)
    if request.method=='POST':
        orderForm=forms.OrderForm(request.POST,instance=order)
        if orderForm.is_valid():
            orderForm.save()
            return redirect('admin-view-booking')
    return render(request,'ecom/update_order.html',{'orderForm':orderForm})


# admin view the feedback
@login_required(login_url='adminlogin')
@staff_member_required
def view_feedback_view(request):
    feedbacks=models.Feedback.objects.all().order_by('-id')
    return render(request,'ecom/view_feedback.html',{'feedbacks':feedbacks})

def add_categories(request):
    categories = models.categories.objects.all()
    categoriesform = forms.CategoriesForm()
    if request.method == 'POST':
        categoriesform = forms.CategoriesForm(request.POST)
        if categoriesform.is_valid():
            categoriesform.save()
            return render(request,'ecom/admin_add_categories.html',{'categories':categories,'form':categoriesform})
    return render(request,'ecom/admin_add_categories.html',{'categories':categories,'form':categoriesform})

#---------------------------------------------------------------------------------
#------------------------ PUBLIC CUSTOMER RELATED VIEWS START ---------------------
#---------------------------------------------------------------------------------
def search_view(request):
    # whatever user write in search box we get in query
    query = request.GET['query']
    categ = request.GET['categ']
    products=models.Product.objects.all().filter(name__icontains=query,category__category__icontains=categ)
    categories= models.categories.objects.all()
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0
    # word variable will be shown in html when user click on search button
    word = ""
    if query:
        word="Searched Result :" + query

    return render(request,'ecom/index.html',{'products':products,'word':word,'product_count_in_cart':product_count_in_cart,'categories':categories})

def search_viewbyCategory(request):
    # whatever user write in search box we get in query
    query = request.GET['query']
    categories= models.categories.objects.all()
    products=models.Product.objects.all().filter(category__category__icontains=query)
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0

    # word variable will be shown in html when user click on search button
    word = ""
    if query:
        word="Category :" + query
    return render(request,'ecom/index.html',{'products':products,'word':word,'product_count_in_cart':product_count_in_cart,'categories':categories})

# any one can add product to cart, no need of signin
def add_to_cart_view(request,pk,quantity):
    categories=models.categories.objects.all()
    #for cart counter, fetching products ids added by customer from cookies
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=1

    response = render(request, 'ecom/home.html',{'allProds':getProdswithCats(),'product_count_in_cart':product_count_in_cart,'categories':categories})

    #adding product id to cookies
    if 'product_ids' in request.COOKIES:
        product_quantities = ""
        product_ids = request.COOKIES['product_ids']
        product_quantities = request.COOKIES['product_quantities']
        product_list = product_ids.split('|')
        if str(pk) not in product_list:
            if product_ids=="":
                product_ids=str(pk)
                product_quantities = str(quantity)
            else:
                product_ids=product_ids+"|"+str(pk)
                product_quantities = product_quantities+"|"+ str(quantity)
        response.set_cookie('product_ids', product_ids)
        response.set_cookie('product_quantities', product_quantities)
    else:
        response.set_cookie('product_ids', pk)
        response.set_cookie('product_quantities', quantity)

    product=models.Product.objects.get(id=pk)
    messages.info(request, product.name + ' added to cart successfully!')
    return response


from django.db.models import Case, When
# for checkout of cart
def cart_view(request):
    #for cart counter
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0

    # fetching product details from db whose id is present in cookie
    products=None
    product_quantities_in_cart=0
    total=0
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        product_quantities = request.COOKIES['product_quantities']
        if product_ids != "":
            product_id_in_cart=product_ids.split('|')
            product_quantities_in_cart=product_quantities.split('|')
            preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(product_id_in_cart)])
            products=models.Product.objects.filter(pk__in = product_id_in_cart).order_by(preserved)
            #for total price shown in cart
            for p in range(len(products)):
                total=total+(products[p].price*int(product_quantities_in_cart[p]))
    return render(request,'ecom/cart.html',{'products':products,'product_quantities_in_cart':product_quantities_in_cart,'total':total,'product_count_in_cart':product_count_in_cart})


def remove_from_cart_view(request,pk):
    #for counter in cart
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0

    # removing product id from cookie
    total=0
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        product_quantities = request.COOKIES['product_quantities']
        product_id_in_cart=product_ids.split('|')
        product_quantities_in_cart=product_quantities.split('|')


        for i in range(len(product_id_in_cart)):
            if(int(product_id_in_cart[i])==pk):
                product_quantities_in_cart.remove(product_quantities_in_cart[i])

        product_id_in_cart=list(set(product_id_in_cart))
        product_id_in_cart.remove(str(pk))
        products=models.Product.objects.all().filter(id__in = product_id_in_cart)

        #for total price shown in cart after removing product
        for p in products:
            total=total+p.price

        #  for update coookie value after removing product id in cart
        value=""
        quantity_value = ""
        for i in range(len(product_id_in_cart)):
            if i==0:
                value=value+product_id_in_cart[0]
                quantity_value = quantity_value+product_quantities_in_cart[0]
            else:
                value=value+"|"+product_id_in_cart[i]
                quantity_value = quantity_value+"|"+product_quantities_in_cart[i]
        response = redirect( 'cart')
        if value=="":
            response.delete_cookie('product_ids')
            response.delete_cookie('product_quantities')
        response.set_cookie('product_ids',value)
        response.set_cookie('product_quantities',quantity_value)
        return response

#update quantity
def update_quantity_cart(request,pk,quantity):
    #for counter in cart
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))

    # # removing product id from cookie
    total=0
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        product_quantities = request.COOKIES['product_quantities']
        product_id_in_cart=product_ids.split('|')
        product_quantities_in_cart = product_quantities.split('|')

        for i in range(len(product_id_in_cart)):
            if(int(product_id_in_cart[i])==pk):
                product_quantities_in_cart[i] = quantity

        response = redirect('cart')
        product_quantities=""
        for i in range(len(product_quantities_in_cart)):
            if i==0:
                product_quantities = product_quantities+str(product_quantities_in_cart[0])
            else:
                product_quantities=product_quantities+"|"+str(product_quantities_in_cart[i])

        response = redirect( 'cart')
        response.set_cookie('product_quantities', product_quantities)
        return response


def send_feedback_view(request):
    feedbackForm=forms.FeedbackForm()
    categories= models.categories.objects.all()
    if request.method == 'POST':
        feedbackForm = forms.FeedbackForm(request.POST)
        if feedbackForm.is_valid():
            feedbackForm.save()
            return render(request, 'ecom/feedback_sent.html')
    return render(request, 'ecom/send_feedback.html', {'feedbackForm':feedbackForm,'categories':categories})


#---------------------------------------------------------------------------------
#------------------------ CUSTOMER RELATED VIEWS START ------------------------------
#---------------------------------------------------------------------------------
@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def customer_home_view(request):
    categories= models.categories.objects.all()
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0
    return render(request,'ecom/home.html',{'allProds':getProdswithCats(),'product_count_in_cart':product_count_in_cart,'categories':categories})



# shipment address before placing order
@login_required(login_url='customerlogin')
def customer_address_view(request):
    # this is for checking whether product is present in cart or not
    # if there is no product in cart we will not show address form
    email = request.user.email
    product_in_cart=False
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        if product_ids != "":
            product_in_cart=True
    #for counter in cart
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        counter=product_ids.split('|')
        product_count_in_cart=len(set(counter))
    else:
        product_count_in_cart=0

    addressForm = forms.AddressForm()
    total=0
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        product_quantities = request.COOKIES['product_quantities']
        if product_ids != "":
            product_id_in_cart=product_ids.split('|')
            product_quantities_in_cart=product_quantities.split('|')
            products=models.Product.objects.all().filter(id__in = product_id_in_cart)
            for p in range(len(products)):
                total=total+(products[p].price*int(product_quantities_in_cart[p]))
    if request.method == 'POST':
        addressForm = forms.AddressForm(request.POST)
        paymentForm = forms.PaymentForm()
        if addressForm.is_valid():
            # here we are taking address, email, mobile at time of order placement
            # we are not taking it from customer account table because
            # these thing can be changes
            mobile=addressForm.cleaned_data['Mobile']
            address = addressForm.cleaned_data['Address']
            #for showing total price on payment page.....accessing id from cookies then fetching  price of product from db
            payment = models.Payment(email=email,amount=total)
            payment.save()
            response =  render(request,'ecom/make_payment.html', {'total':total,'payment': payment, 'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY})
            response.set_cookie('mobile',mobile)
            response.set_cookie('address',address)

            
            return response
    return render(request,'ecom/customer_address.html',{'addressForm':addressForm,'product_in_cart':product_in_cart,'product_count_in_cart':product_count_in_cart,'total':total})




# here we are just directing to this view...actually we have to check whther payment is successful or not
#then only this view should be accessed
@login_required(login_url='customerlogin')
def payment_success_view(request):
    # Here we will place order | after successful payment
    # we will fetch customer  mobile, address, Email
    # we will fetch product id from cookies then respective details from db
    # then we will create order objects and store in db
    # after that we will delete cookies because after order placed...cart should be empty
    customer=models.Customer.objects.get(user_id=request.user.id)
    products=None
    mobile=None
    address=None
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        if product_ids != "":
            product_id_in_cart=product_ids.split('|')
            products=models.Product.objects.all().filter(id__in = product_id_in_cart)
            # Here we get products list that will be ordered by one customer at a time

    # these things can be change so accessing at the time of order...
    if 'mobile' in request.COOKIES:
        mobile=request.COOKIES['mobile']
    if 'address' in request.COOKIES:
        address=request.COOKIES['address']

    # here we are placing number of orders as much there is a products
    # suppose if we have 5 items in cart and we place order....so 5 rows will be created in orders table
    # there will be lot of redundant data in orders table...but its become more complicated if we normalize it
    for product in products:
        models.Orders.objects.get_or_create(customer=customer,product=product,status='Pending',mobile=mobile,address=address)

    # after order placed cookies should be deleted
    response = render(request,'ecom/payment_success.html')
    response.delete_cookie('product_ids')
    response.delete_cookie('mobile')
    response.delete_cookie('address')
    return response




@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def my_order_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    orders=models.Orders.objects.all().filter(customer_id = customer)
    categories= models.categories.objects.all()
    ordered_products=[]
    for order in orders:
        ordered_product=models.Product.objects.all().filter(id=order.product.id)
        ordered_products.append(ordered_product)

    return render(request,'ecom/my_order.html',{'data':zip(ordered_products,orders),'categories':categories})




#--------------for discharge patient bill (pdf) download and printing
import io
from xhtml2pdf import pisa
from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse


def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return

@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def download_invoice_view(request,orderID,productID):
    order=models.Orders.objects.get(id=orderID)
    product=models.Product.objects.get(id=productID)
    mydict={
        'orderDate':order.order_date,
        'customerName':request.user,
        'customerMobile':order.mobile,
        'shipmentAddress':order.address,
        'orderStatus':order.status,

        'productName':product.name,
        'productImage':product.product_image,
        'productPrice':product.price,
        'productDescription':product.description,


    }
    return render_to_pdf('ecom/download_invoice.html',mydict)






@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def my_profile_view(request):
    categories= models.categories.objects.all()
    customer=models.Customer.objects.get(user_id=request.user.id)
    return render(request,'ecom/my_profile.html',{'customer':customer,'categories':categories})


@login_required(login_url='customerlogin')
@user_passes_test(is_customer)
def edit_profile_view(request):
    customer=models.Customer.objects.get(user_id=request.user.id)
    user=models.User.objects.get(id=customer.user_id)
    userForm=forms.CustomerUserForm(instance=user)
    customerForm=forms.CustomerForm(request.FILES,instance=customer)
    mydict={'userForm':userForm,'customerForm':customerForm,'customer':customer}
    if request.method=='POST':
        userForm=forms.CustomerUserForm(request.POST,instance=user)
        customerForm=forms.CustomerForm(request.POST,instance=customer)
        if userForm.is_valid() and customerForm.is_valid():
            user=userForm.save()
            user.set_password(user.password)
            user.save()
            customerForm.save()
            return HttpResponseRedirect('my-profile')
    return render(request,'ecom/edit_profile.html',context=mydict)



#---------------------------------------------------------------------------------
#------------------------ ABOUT US AND CONTACT US VIEWS START --------------------
#---------------------------------------------------------------------------------
def aboutus_view(request):
    categories= models.categories.objects.all()
    return render(request,'ecom/aboutus.html',{'categories':categories})

def contactus_view(request):
    categories= models.categories.objects.all()
    sub = forms.ContactusForm()
    if request.method == 'POST':
        sub = forms.ContactusForm(request.POST)
        if sub.is_valid():
            email = sub.cleaned_data['Email']
            name=sub.cleaned_data['Name']
            message = sub.cleaned_data['Message']
            send_mail(str(name)+' || '+str(email),message, settings.EMAIL_HOST_USER, settings.EMAIL_RECEIVING_USER, fail_silently = False)
            return render(request, 'ecom/contactussuccess.html')
    return render(request, 'ecom/contactus.html', {'form':sub,'categories':categories})

def show_message_logout(sender, user, request, **kwargs):
    # whatever...
    messages.info(request, 'You have been logged out Successfully.')

user_logged_out.connect(show_message_logout)

def show_message_login(sender, user, request, **kwargs):
    # whatever...
    messages.info(request, 'You have been logged In Successfully.')

user_logged_in.connect(show_message_login)

def activate_user(request, uidb64, token):

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = models.User.objects.get(pk=uid)
    except Exception as e:
        user= None
    if user and account_activation_token.check_token(user, token):
        user.is_email_verified = True
        user.save()

        #messages.success(request, 'Email verified you can login As '+{{user}})
        return redirect('customerlogin')

    return render(request,'ecom/auth_activation_failed.html')



def customer_login_view(request):
    form = forms.loginForm()
    if request.method == 'POST':
        form = forms.loginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(email=email, password=password)
        if user is not None:
            if user.is_email_verified:
                login(request, user)
                return redirect('customer-home')
            else:
                messages.info(request, 'Please verify you email first.')
        else:
            messages.info(request, 'Invalid Password Credentials')
    return render(request,'ecom/customerlogin.html',{'form':form})




# paystack payments
# Paystack Payments
from django.conf import settings
def initiate_payment(request):
    if request.method == 'POST':
        payment_form = forms.PaymentForm(request.POST)
        if payment_form.is_valid():
            payment = payment_form.save()
            return render(request,'ecom/make_payment.html', {'payment': payment, 'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY})
    
    else:
        payment_form = forms.PaymentForm()
        return render(request, 'ecom/customer_address.html',{'payment_form': payment_form})

from django.shortcuts import get_object_or_404

def verify_payment(request, ref):
    customer=models.Customer.objects.get(user_id=request.user.id)
    payment = models.Payment.objects.get(ref=ref)
    products=None
    mobile=None
    address=None
    if 'product_ids' in request.COOKIES:
        product_ids = request.COOKIES['product_ids']
        product_quantities = request.COOKIES['product_quantities']
        if product_ids != "":
            product_id_in_cart=product_ids.split('|')
            product_quantities_in_cart=product_quantities.split('|')
            products=models.Product.objects.all().filter(id__in = product_id_in_cart)
            # Here we get products list that will be ordered by one customer at a time

    # these things can be change so accessing at the time of order...
    if 'mobile' in request.COOKIES:
        mobile=request.COOKIES['mobile']
    if 'address' in request.COOKIES:
        address=request.COOKIES['address']

    # here we are placing number of orders as much there is a products
    # suppose if we have 5 items in cart and we place order....so 5 rows will be created in orders table
    # there will be lot of redundant data in orders table...but its become more complicated if we normalize it


    payment = get_object_or_404(models.Payment, ref=ref)
    verified = payment.verify_payment()
    if verified:
        # current_datetime = datetime.now().strftime('%Y%m%d%H%M%S')
        # orders_count = models.Orders.objects.count()
        # last_order = models.Orders.objects.last()
        # id = 0 if orders_count < 1 else last_order.id
        # ref_code = f'{current_datetime}{id+1}'
        product_names = ""
        for p in range(len(products)):
            product_names = product_names+","+products[p].name
            models.Orders.objects.get_or_create(customer=customer,product=products[p],status='Pending',mobile=mobile,address=address,Payment=payment,quantity=product_quantities_in_cart[p])
        categories = models.categories.objects.all()
        # after order placed cookies should be deleted
        response = render(request,'ecom/home.html',{'categories':categories,'allProds':getProdswithCats()})
        response.delete_cookie('product_ids')
        response.delete_cookie('mobile')
        response.delete_cookie('address')
        messages.success(request, 'verficatoin successfull')
        product_names.split()
        product_names.replace(" ","")
        send_order_confirmation_email(customer.user,product_names,request)
    else:
        messages.error(request, 'verficatoin failed')

    return response
