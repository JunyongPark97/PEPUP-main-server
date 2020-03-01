from payment.models import Deal, Delivery
from accounts.models import User
# Create your tests here.

seller = User.objects.all()[12]
buyer = User.objects.all()[2]


def createdeal():
    delivery = Delivery(sender=seller, receiver=buyer, address='', memo='')
    deal = Deal(buyer=buyer, seller=seller, total=10000, remain=10000, delivery=delivery, delivery_charge=2500)
    Delivery.objects.bulk_create([delivery])
    print(delivery.pk)
    # Deal.objects.bulk_create([deal])
