from django.http import Http404
from django.shortcuts import render
from django.views.decorators.csrf import requires_csrf_token

ERROR_PAGES = {
    400: {
        "error_code": "400",
        "error_eyebrow": "Bad request",
        "error_title": "This request cannot be processed",
        "error_message": "The portal could not understand that request. Check the address and try again.",
    },
    403: {
        "error_code": "403",
        "error_eyebrow": "Access denied",
        "error_title": "You do not have permission",
        "error_message": "This part of the 1 BIR portal is restricted. Return to a page you are allowed to use, or sign in with an authorised account.",
    },
    404: {
        "error_code": "404",
        "error_eyebrow": "Not found",
        "error_title": "This page is not on the portal",
        "error_message": "The address may be mistyped, or the page may have been moved. Use the portal menu or go back to a previous page.",
    },
    500: {
        "error_code": "500",
        "error_eyebrow": "Server error",
        "error_title": "Something went wrong",
        "error_message": "The portal hit an unexpected problem. Try again in a moment. If it continues, contact the system administrator.",
    },
}


def _render_error(request, status, extra=None):
    context = dict(ERROR_PAGES[status])
    if extra:
        context.update(extra)
    return render(request, f"errors/{status}.html", context, status=status)


def bad_request(request, exception):
    return _render_error(request, 400)


def permission_denied(request, exception):
    return _render_error(request, 403)


def page_not_found(request, exception):
    return _render_error(request, 404)


@requires_csrf_token
def server_error(request):
    return _render_error(request, 500)


def csrf_failure(request, reason=""):
    return _render_error(
        request,
        403,
        {
            "error_eyebrow": "Session expired",
            "error_title": "This form could not be verified",
            "error_message": "Your session may have expired. Return to the portal, refresh the page, and submit the form again.",
        },
    )


def preview(request, code):
    if code not in ERROR_PAGES:
        raise Http404("Unknown error page.")
    if code == 500:
        return server_error(request)
    if code == 403 and request.GET.get("csrf"):
        return csrf_failure(request)
    return _render_error(request, code)
