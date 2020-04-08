# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: helloworld/proto/helloword2.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='helloworld/proto/helloword2.proto',
  package='helloworld2',
  syntax='proto3',
  serialized_options=None,
  serialized_pb=_b('\n!helloworld/proto/helloword2.proto\x12\x0bhelloworld2\"\x1c\n\x0cHelloRequest\x12\x0c\n\x04name\x18\x01 \x01(\t\"\x1d\n\nHelloReply\x12\x0f\n\x07message\x18\x01 \x01(\t2K\n\x07Greeter\x12@\n\x08SayHello\x12\x19.helloworld2.HelloRequest\x1a\x17.helloworld2.HelloReply\"\x00\x62\x06proto3')
)




_HELLOREQUEST = _descriptor.Descriptor(
  name='HelloRequest',
  full_name='helloworld2.HelloRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='name', full_name='helloworld2.HelloRequest.name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=50,
  serialized_end=78,
)


_HELLOREPLY = _descriptor.Descriptor(
  name='HelloReply',
  full_name='helloworld2.HelloReply',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='message', full_name='helloworld2.HelloReply.message', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=80,
  serialized_end=109,
)

DESCRIPTOR.message_types_by_name['HelloRequest'] = _HELLOREQUEST
DESCRIPTOR.message_types_by_name['HelloReply'] = _HELLOREPLY
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

HelloRequest = _reflection.GeneratedProtocolMessageType('HelloRequest', (_message.Message,), dict(
  DESCRIPTOR = _HELLOREQUEST,
  __module__ = 'helloworld.proto.helloword2_pb2'
  # @@protoc_insertion_point(class_scope:helloworld2.HelloRequest)
  ))
_sym_db.RegisterMessage(HelloRequest)

HelloReply = _reflection.GeneratedProtocolMessageType('HelloReply', (_message.Message,), dict(
  DESCRIPTOR = _HELLOREPLY,
  __module__ = 'helloworld.proto.helloword2_pb2'
  # @@protoc_insertion_point(class_scope:helloworld2.HelloReply)
  ))
_sym_db.RegisterMessage(HelloReply)



_GREETER = _descriptor.ServiceDescriptor(
  name='Greeter',
  full_name='helloworld2.Greeter',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  serialized_start=111,
  serialized_end=186,
  methods=[
  _descriptor.MethodDescriptor(
    name='SayHello',
    full_name='helloworld2.Greeter.SayHello',
    index=0,
    containing_service=None,
    input_type=_HELLOREQUEST,
    output_type=_HELLOREPLY,
    serialized_options=None,
  ),
])
_sym_db.RegisterServiceDescriptor(_GREETER)

DESCRIPTOR.services_by_name['Greeter'] = _GREETER

# @@protoc_insertion_point(module_scope)