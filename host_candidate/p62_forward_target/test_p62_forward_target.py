#!/usr/bin/env python3
import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from p62_forward_target import exact_def,forwarded_reference,callee_structure
n=0
def check(x,why):
 global n
 n+=1
 if not x:raise AssertionError("P62_"+why)
class I:
 def __init__(self,name,out="",rs=()):
  self.name,self.out,self.rs=name,out,list(rs)
 def get_name(self):return self.name
 def get_output(self):return self.out
 def get_operands(self):return self.rs
class M:
 def __init__(self,name,desc,ops):
  self.name,self.desc,self.ops=name,desc,ops
 def get_name(self):return self.name
 def get_descriptor(self):return self.desc
 def get_code(self):return object()
 def get_instructions_idx(self):return iter(self.ops)
class C:
 def __init__(self,name,methods):self.name,self.methods=name,methods
 def get_name(self):return self.name
 def get_methods(self):return self.methods
def r(x):return (0,x)
ref="Lcom/dsh/android/Bridge;->internal(Ljava/lang/Object;)Ljava/util/List;"
args=I("invoke-static","{v0}, "+ref,[r(0),(256,0,ref)])
wrapper=M("access$make","()Ljava/util/List;",
          [(0,args),(2,I("move-result-object",rs=[r(3)])),
           (4,I("return-object",rs=[r(3)]))])
resolved,status=forwarded_reference(wrapper)
check(status=="EXACT_FORWARDING_CALL","forward_status")
check(resolved==("Lcom/dsh/android/Bridge;","internal","Ljava/lang/Object;","Ljava/util/List;"),"ref")
bad=M("access$make","()Ljava/util/List;",
      [(0,args),(2,I("move-result-object",rs=[r(3)])),
       (4,I("return-object",rs=[r(4)]))])
check(forwarded_reference(bad)[1]=="UNKNOWN_RETURN_REGISTER","fail_closed_mismatch")
callee=M("internal","(Ljava/lang/Object;)Ljava/util/List;",
         [(0,I("new-instance","v0, Ljava/util/ArrayList;")),
          (2,I("return-object",rs=[r(0)]))])
cls=C("Lcom/dsh/android/Bridge;",[callee])
check(exact_def([cls],resolved)==[callee],"exact_def")
check(exact_def([cls],("Lcom/dsh/android/Bridge;","internal","I","Ljava/util/List;"))==[],"wrong_params")
s=callee_structure(callee)
check(s["calls_and_allocations"]["ALLOC_ARRAYLIST"]==1,"list_construct")
check(s["calls_and_allocations"]["RETURN_OBJECT"]==1,"object_return")
print("P62_SYNTHETIC_FORWARD_TARGET=PASS assertions="+str(n))
print("P62_SYNTHETIC_ORIGINAL_APK_USED=NO")
