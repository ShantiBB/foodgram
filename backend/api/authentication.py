from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils.translation import gettext_lazy as _



class BearerAuthentication(TokenAuthentication):
    keyword = 'Bearer'
