
from src import LVDouble
from src import LVObject
from src import lvunflatten
from src import LVI32, LVSingle, LVString, LVArray, LVU8, LVArrayType
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

@lvclass(version=(1,0,0,5))
class Test:
    int32: LVI32
    dbl: LVDouble
    string: LVString
    u8_array: LVArray(LVU8)
    str_array: LVArray(LVString)

test = Test()
#test.int32 = 614
#test.dbl = 1.618
test.string = "Había uña vez..."
#test.u8_array = [123, 234, 45, 67, 89]
test.str_array = ["Hello", "World", "from", "LabVIEW"]

bytes = lvflatten(test)

print(bytes.hex())

#lvobj_dict = lvunflatten(bytes, LVObject())
#print(lvobj_dict)
