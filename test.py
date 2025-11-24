from src import LVObject
from src import lvunflatten
from src import LVI32, LVSingle, LVString, LVArray1D, LVU8
from src import lvclass, LVU16, lvflatten


@lvclass(library="Actor Framework", class_name="Message")
class Message:
    pass

@lvclass(library="Serializable Message", class_name="Serializable Msg",
         version=(1, 0, 0, 7))
class SerializableMsg(Message):
    pass

@lvclass(library="Commander", class_name="echo general Msg")
class EchoMsg(SerializableMsg):
    message: str      # → LVString
    code: LVU16      # → U16 (2 bytes)

"""msg = EchoMsg()
msg.message = "Hello World :)"
msg.code = 1
data = lvflatten(msg)

print(msg)
print(data.hex())"""

@lvclass(version=(1,0,0,2))
class Test:
    int32: LVI32
    dbl: LVSingle
    string: LVString
    u8_array: LVArray1D(LVU8)

test = Test()
test.int32 = 123
"""test.dbl = 3.14
test.string = "Test String"
test.u8_array = [1, 2, 3, 4, 5]"""

bytes = lvflatten(test)

print(bytes.hex())

lvobj_dict = lvunflatten(bytes, LVObject())
print(lvobj_dict)