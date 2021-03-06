import traceback

from django.db import connection
from django.http import HttpResponseNotAllowed
from django.template import RequestContext
from django.template import loader
from django.middleware.locale import LocaleMiddleware
from django.utils.translation.trans_real import parse_accept_lang_header


class ExceptionLoggingMiddleware(object):

    def process_exception(self, request, exception):
        print(traceback.format_exc())


class HTTPResponseNotAllowedMiddleware(object):

    def process_response(self, request, response):
        if isinstance(response, HttpResponseNotAllowed):
            context = RequestContext(request)
            response.content = loader.render_to_string(
                "405.html", context_instance=context)

        return response


class LocaleMiddlewareWithTweaks(LocaleMiddleware):
    """
    Overrides LocaleMiddleware from django with:
        Khmer `km` language code in Accept-Language is rewritten to km-kh
    """

    def process_request(self, request):
        accept = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        try:
            codes = [code for code, r in parse_accept_lang_header(accept)]
            if 'km' in codes and 'km-kh' not in codes:
                request.META['HTTP_ACCEPT_LANGUAGE'] = accept.replace('km',
                                                                      'km-kh')
        except:
            # this might fail if i18n is disabled.
            pass

        super(LocaleMiddlewareWithTweaks, self).process_request(request)


class SqlLogging:
    def process_response(self, request, response):
        from sys import stdout
        if stdout.isatty():
            for query in connection.queries:
                print "\033[1;31m[%s]\033[0m \033[1m%s\033[0m" % (
                    query['time'], " ".join(query['sql'].split()))

        return response


class BrokenClientMiddleware(object):
    """
    ODK Collect sends HTTP-violating localized date strings, e.g.
    'mar., 25 ao\xfbt 2015 07:11:56 GMT+00:00', which wreak havoc on oauthlib.
    This middleware detects and discards HTTP_DATE headers that contain invalid
    characters.
    """
    def process_request(self, request):
        if 'HTTP_DATE' in request.META:
            try:
                request.META['HTTP_DATE'].decode()
            except UnicodeDecodeError:
                del request.META['HTTP_DATE']


class UsernameInResponseHeaderMiddleware(object):
    """
    Record the authenticated user (if any) in the `X-KoBoNaUt` HTTP header
    """
    def process_response(self, request, response):
        try:
            user = request.user
        except AttributeError:
            return response
        if user.is_authenticated():
            response['X-KoBoNaUt'] = request.user.username
        return response
