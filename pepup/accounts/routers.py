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
        Route(
            url='{prefix}/confirmsms/',
            mapping={'post': 'confirmsms'},
            name='{basename}-confirmsms',
            detail=False,
            initkwargs={}
        ),
        Route(
            url='{prefix}/find_email/',
            mapping={'post': 'find_email'},
            name='{basename}-find-email',
            detail=False,
            initkwargs={}
        ),
        Route(
            url='{prefix}/reset_password/',
            mapping={'post': 'reset_password'},
            name='{basename}-reset-password',
            detail=False,
            initkwargs={}
        ),
        Route(
            url='{prefix}/profile/',
            mapping={'get': 'profile',
                     'post': 'profile'},
            name='{basename}-update-profile',
            detail=False,
            initkwargs={}
        ),
        Route(
            url='{prefix}/search_address/',
            mapping={'post': 'search_address'},
            name='{basename}-search-address',
            detail=False,
            initkwargs={}
        ),
        Route(
            url='{prefix}/set_address/',
            mapping={'post': 'set_address'},
            name='{basename}-set-address',
            detail=False,
            initkwargs={}
        ),

    ]


router_account = AccountRouter()
router_account.register('accounts', AccountViewSet, basename='accounts')