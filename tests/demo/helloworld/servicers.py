from .proto import helloworld_pb2
from .proto import helloworld_pb2_grpc
from .proto import helloword2_pb2
from .proto import helloword2_pb2_grpc

from binwen.servicer import ServicerMeta


class GreeterServicer(helloworld_pb2_grpc.GreeterServicer, metaclass=ServicerMeta):

    def SayHello(self, request, context):
        return helloworld_pb2.HelloReply(message='Hello, %s!' % request.name)


class Helloworld2(helloword2_pb2_grpc.GreeterServicer, metaclass=ServicerMeta):

    def SayHello(self, request, context):
        return helloword2_pb2.HelloReply(message='Hello, %s!' % request.name)
