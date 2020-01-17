from rest_framework.routers import Route, DefaultRouter,SimpleRouter, DynamicRoute
from .views import (
    ProductViewSet, TradeViewSet, FollowViewSet,
    PaymentViewSet
)



class ProductRouter(DefaultRouter):
    DefaultRouter.routes += [
        Route(
            url='{prefix}/search/{lookup}/',
            mapping={'get': 'search'},
            name='{basename}-search',
            detail=False,
            initkwargs={}
        ),
        Route(
            url='{prefix}/{lookup}/like/',
            mapping={'post': 'like'},
            name='{basename}-like',
            detail=False,
            initkwargs={}
        ),
        Route(
            url='{prefix}/{lookup}/liked/',
            mapping={'get': 'liked'},
            name='{basename}-liked',
            detail=False,
            initkwargs={}
        ),
        Route(
            url='{prefix}/create/',
            mapping={'post': 'create'},
            name='{basename}-create',
            detail=False,
            initkwargs={}
        ),
    ]
    DefaultRouter.routes.sort(reverse=True)


class TradeRouter(DefaultRouter):
    DefaultRouter.routes += [
        Route(
            url='{prefix}/bagging/{lookup}/',
            mapping={'post': 'bagging'},
            name='{basename}-bagging',
            detail=False,
            initkwargs={}
        ),
        Route(
            url='{prefix}/cart/',
            mapping={'get': 'cart'},
            name='{basename}-cart',
            detail=False,
            initkwargs={}
        ),
        Route(
            url='{prefix}/cancel/',
            mapping={'post': 'cancel'},
            name='{basename}-cancel',
            detail=False,
            initkwargs={}
        )
    ]


class PaymentRouter(DefaultRouter):
    DefaultRouter.routes += [
        Route(
            url='{prefix}/payform/',
            mapping={'post': 'get_payform'},
            name='{basename}-payform',
            detail=False,
            initkwargs={}
        ),
        Route(
            url='{prefix}/confirm/',
            mapping={'post': 'confirm'},
            name='{basename}-confirm',
            detail=False,
            initkwargs={}
        ),
        Route(
            url='{prefix}/done/',
            mapping={'post': 'done'},
            name='{basename}-confirm',
            detail=False,
            initkwargs={}
        )
    ]


class FollowRouter(DefaultRouter):
    DefaultRouter.routes += [
        Route(
            url='{prefix}/following',
            mapping={'post': 'following'},
            name='{basename}-following',
            detail=False,
            initkwargs={}
        ),
        Route(
            url='{prefix}/check_follow/',
            mapping={'post': 'check_follow'},
            name='{basename}-check_follow',
            detail=False,
            initkwargs={}
        )
    ]


router = ProductRouter()
router.register('products', ProductViewSet, basename='products')
router_trades = TradeRouter()
router_trades.register('trades', TradeViewSet, basename='trades')
router_follow = FollowRouter()
router_follow.register('follow', FollowViewSet,basename='follow')
router_payment = PaymentRouter()
router_payment.register('payment', PaymentViewSet, basename='payment')