import grpc
import pendulum


from binwen import exceptions
from binwen.pb2 import default_pb2


class MiddlewareMixin:
    def __init__(self, app, handler, origin_handler):
        self.app = app
        self.handler = handler
        self.origin_handler = origin_handler

    def __call__(self, servicer, request, context):
        request, context = self.before_handler(servicer, request, context)
        response = self.handler(servicer, request, context)
        return self.after_handler(servicer, response)

    def before_handler(self, servicer, request, context):
        return request, context

    def after_handler(self, servicer, response):
        return response


class GuardMiddleware(MiddlewareMixin):
    def __call__(self, servicer, request, context):
        try:
            return self.handler(servicer, request, context)
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            print("exc>>>>", e)
            self.app.logger.exception(str(e), exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details('Internal Error Occured')
            return default_pb2.Empty()


class RpcErrorMiddleware(MiddlewareMixin):
    def __call__(self, servicer, request, context):
        try:
            return self.handler(servicer, request, context)
        except exceptions.RpcException as e:
            context.set_code(e.code)
            context.set_details(e.details)
            return default_pb2.Empty()


class ServiceLogMiddleware(MiddlewareMixin):
    def __call__(self, servicer, request, context):
        start_at = pendulum.now(self.app.tz)
        response = self.handler(servicer, request, context)
        finish_at = pendulum.now(self.app.tz)
        delta = finish_at - start_at
        self.app.logger.info(
            '[{}] {}.{} Called. Processed in {}s'.format(
                start_at.isoformat(),
                servicer.__class__.__name__,
                self.origin_handler.__name__,
                delta.total_seconds()
            )
        )
        return response
