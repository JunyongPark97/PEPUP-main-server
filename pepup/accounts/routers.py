from rest_framework.routers import Route, DefaultRouter,SimpleRouter, DynamicRoute
from .views import AccountViewSet


class AccountRouter(DefaultRouter):
    DefaultRouter.routes += [
        Route(
            url='{prefix}/login/',
            mapping={'post': 'login'},
            name='{basename}-login',
            detail=False,
            initkwargs={}
        ),
        Route(
            url='{prefix}/logout/',
            mapping={'post': 'logout'},
            name='{basename}-logout',
            detail=False,
            initkwargs={}
        ),
        Route(
            url='{prefix}/signup/',
            mapping={'post': 'signup'},
            name='{basename}-signup',
            detail=False,
            initkwargs={}
        ),
    ]


router_account = AccountRouter()
router_account.register('accounts', AccountViewSet, basename='accounts')