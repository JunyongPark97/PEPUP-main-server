from django.db import models, transaction


class Commission(models.Model):
    commission = models.IntegerField(help_text="수수료 30%")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '수수료'
        verbose_name_plural = '수수료'


class Applicant(models.Model):
    name = models.CharField(max_length=30)
    box_apply = models.BooleanField(default=False)
    address = models.TextField(help_text="펩업 박스 발송 주소", null=True, blank=True)
    phone = models.CharField(max_length=50)
    apply_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '신청자 관리'
        verbose_name_plural = '신청자 관리'

    def __str__(self):
        return self.name

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super(Applicant, self).save()
        ApplicantManager.objects.create(user=self)


class ApplicantManager(models.Model):
    user = models.ForeignKey(Applicant, on_delete=models.CASCADE)
    outer_count = models.IntegerField(default=0)
    top_count = models.IntegerField(default=0)
    bottom_count = models.IntegerField(default=0)
    dress_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '신청자 관리'
        verbose_name_plural = '신청자 관리'

    def __str__(self):
        return self.user.name

    @transaction.atomic
    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):

        super(ApplicantManager, self).save(force_insert=False, force_update=False)
        self._create_outer()
        self._create_top()
        self._create_bottom()
        self._create_dress()

    def _create_outer(self):
        count = self.outer_count
        if count > 0:
            self.clothes.filter(kinds=1).delete()
            for i in range(count):
                ApplyClothes.objects.create(kinds=1, clothes_manager=self)

    def _create_top(self):
        count = self.top_count
        if count > 0:
            self.clothes.filter(kinds=2).delete()
            for i in range(count):
                ApplyClothes.objects.create(kinds=2, clothes_manager=self)

    def _create_bottom(self):
        count = self.bottom_count
        if count > 0:
            self.clothes.filter(kinds=3).delete()
            for i in range(count):
                ApplyClothes.objects.create(kinds=3, clothes_manager=self)

    def _create_dress(self):
        count = self.dress_count
        if count > 0:
            self.clothes.filter(kinds=4).delete()
            for i in range(count):
                ApplyClothes.objects.create(kinds=4, clothes_manager=self)


class ApplyClothes(models.Model):
    OUTER = 1
    TOP = 2
    BOTTOM = 3
    DRESS = 4

    CLOTHES_KINDS = (
        (OUTER, 'outer'),
        (TOP, 'top'),
        (BOTTOM, 'bottom'),
        (DRESS, 'dress'),
    )

    kinds = models.IntegerField(choices=CLOTHES_KINDS, verbose_name="상품종류")
    name = models.CharField(max_length=100, null=True, blank=True, verbose_name="상품이름")
    clothes_manager = models.ForeignKey(ApplicantManager, on_delete=models.CASCADE, related_name='clothes', verbose_name="신청자")
    # image = models.ImageField(upload_to=clothes_directory_path, null=True, blank=True)
    is_checked = models.BooleanField(default=False)
    measure_price = models.IntegerField(default=0, verbose_name="측정가")
    sold = models.BooleanField(default=False, verbose_name="판매여부")
    deposit = models.BooleanField(default=False, verbose_name="입금여부")
    delivery = models.BooleanField(default=False, verbose_name="배송여부")

    class Meta:
        verbose_name = '신청 상품 관리'
        verbose_name_plural = '신청 상품 관리'

    @property
    def user_revenue(self):
        commission = float(Commission.objects.last().commission)
        price = self.measure_price * (1 - 0.01 * commission)
        return '{} 원'.format(int(price))

    @property
    def our_revenue(self):
        commission = float(Commission.objects.last().commission)
        price = self.measure_price * (0.01 * commission)
        return '{} 원'.format(int(price))


class Manager(models.Model):
    # TODO : instagram 하고 연동
    apply = models.OneToOneField(ApplyClothes, on_delete=models.CASCADE, related_name='manager')


class Test(models.Model):
    count = models.IntegerField()
    text = models.CharField(max_length=100)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        print(self.count)
        super(Test, self).save()
        print(self.count)