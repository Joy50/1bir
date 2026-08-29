from django.shortcuts import resolve_url
from django.utils.http import url_has_allowed_host_and_scheme


def safe_redirect_target(request, fallback, next_value=None):
    candidate = next_value if next_value is not None else request.POST.get("next")
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return resolve_url(fallback)
