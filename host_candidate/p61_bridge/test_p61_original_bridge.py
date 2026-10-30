#!/usr/bin/env python3
import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from p61_original_bridge import ref,arity,flags,range_data,producer_index
n=0
def check(x,label):
 global n
 n+=1
 if not x:raise AssertionError("P61_TEST_"+label)
class I:
 def __init__(self,name,out="",rr=(),delta=None,count=None):
  self.name,self.out,self.rr,self.delta,self.count=name,out,list(rr),delta,count
 def get_name(self):return self.name
 def get_output(self):return self.out
 def get_operands(self):return self.rr
 def get_ref_off(self):return self.delta
 def get_AA(self):return self.count
def R(v):return (0,v)
target="Lcom/dsh/android/Probe;->access$make(Ljava/lang/Object;I)Ljava/util/List;"
call=I("invoke-static/range","{v3 .. v4}, "+target,[R(3),R(4),(256,0,target)],count=2)
check(ref(call)==("Lcom/dsh/android/Probe;","access$make","Ljava/lang/Object;I","Ljava/util/List;"),"reference")
check(arity("Ljava/lang/Object;I")==2,"arity")
check(arity("Ljava/lang/Object; I")==2,"arity_with_dex_whitespace")
check(arity("Ljava/lang/Object")==None,"bad_descriptor")
check(flags(0x1048)=={"synthetic":True,"bridge":True,"static":True},"flags")
check(range_data(call)["interval_validated"],"range")
bad=I("invoke-static/range","{v3 .. v5}, "+target,[R(3),R(5),(256,0,target)],count=2)
check(not range_data(bad)["interval_validated"],"range_not_contiguous")
ops=[(0,call),(2,I("move-result-object",rr=[R(7)])),
     (4,I("move-object",rr=[R(8),R(7)])),
     (6,I("invoke-direct","test",rr=[R(1),R(8)]))]
check(producer_index(ops,3,8)==0,"local_chain")
branched=[(0,call),(2,I("move-result-object",rr=[R(7)])),
          (4,I("if-eqz",rr=[R(0)],delta=2)),
          (6,I("move-object",rr=[R(8),R(7)])),
          (8,I("invoke-direct","test",rr=[R(1),R(8)]))]
check(producer_index(branched,4,8) is None,"branch_barrier")
print("P61_SYNTHETIC_EXACT_METHOD=PASS assertions="+str(n))
print("P61_SYNTHETIC_NO_ORIGINAL_APK=YES")
