"""Two existing host method bodies only. No APK/write/install; requires exact P1 DEX.
Derived replacement, NOT recovered original Kotlin. No new references or headers.
"""
import struct,hashlib,zlib
from androguard.core.dex import DEX
from patch_deny import sha,invoke
EXPECTED_P1='09b76306ec151b910cd9cf08c9b7b6d44c79a943efba5fc02448c76980b7665d'
ACT='Lcom/dsh/android/MainActivity;'
VIEW='Lcom/dsh/android/browser/AiBrowserView;'
HOST='Lcom/dsh/android/MainActivity$installBrowserBridge$1$1;'
BRIDGE='Lcom/dsh/android/browser/BrowserBridge;'
KEYS={(HOST,'browserOrNull'),(BRIDGE,'opOpen$lambda$6')}
def apply_browser(data):
 if sha(data)!=EXPECTED_P1:raise ValueError('P1_PREIMAGE_MISMATCH')
 d=DEX(data);out=bytearray(data)
 refs={(m.get_class_name(),m.get_name(),m.get_descriptor()):i for i,m in enumerate(d.get_methods())}
 ref=lambda c,n,s:refs[c,n,s]
 types={d.get_cm_type(i):i for i in range(struct.unpack_from('<I',data,64)[0])}
 fields={(f.get_class_name(),f.get_name(),f.get_descriptor()):i for i,f in enumerate(d.get_fields())}
 definitions={(c.get_name(),m.get_name()):m for c in d.get_classes() for m in c.get_methods()}
 for key in [(ACT,'access$ensureAiBrowser'),(ACT,'openAiBrowser')]:
  assert definitions[key].get_access_flags()&1,'Host target must remain public'
 field=fields[HOST,'this$0',ACT]
 ensure=ref(ACT,'access$ensureAiBrowser','('+ACT+')'+VIEW)
 getter=[0x3054,field]+invoke(0x71,ensure,[0])+[0x000c,0x0011]
 ctor_class='Lcom/dsh/android/browser/BrowserBridge$$ExternalSyntheticLambda18;'
 open_method=definitions[BRIDGE,'opOpen$lambda$6'];guard_at=open_method.get_code_off()+16+12
 guard=list(struct.unpack_from('<5H',data,guard_at))
 body=guard+invoke(0x6e,ref(VIEW,'getContext','()Landroid/content/Context;'),[2])+[0x000c,0x001f,types[ACT]]
 body+=invoke(0x6e,ref(ACT,'openAiBrowser','(Ljava/lang/String;)V'),[0,1])
 body += [0x0122,types[ctor_class]]+invoke(0x70,ref(ctor_class,'<init>','(Lkotlin/jvm/functions/Function1; '+VIEW+')V'),[1,3,2])
 body += invoke(0x6e,ref(VIEW,'awaitLoad','(Lkotlin/jvm/functions/Function1;)V'),[2,1])
 body += [0x0162,fields['Lkotlin/Unit;','INSTANCE','Lkotlin/Unit;'],0x0111]
 reports=[];allowed=set(range(8,32))
 for key,cu,size,regs,ins,off in [((HOST,'browserOrNull'),getter,14,4,1,0x32b520),((BRIDGE,'opOpen$lambda$6'),body,25,4,3,0x34aee8)]:
  m=definitions[key];code=m.get_code()
  assert (m.get_code_off(),code.get_insns_size(),code.get_registers_size(),code.get_ins_size(),code.get_tries_size())==(off,size,regs,ins,0)
  assert len(cu)<=size
  start=off+16;end=start+size*2
  replacement=struct.pack('<'+'H'*size,*(cu+[0]*(size-len(cu))))
  out[start:end]=replacement;allowed.update(range(start,end))
  reports.append({'class':key[0],'method':key[1],'method_idx':m.get_method_idx(),'instruction_range':[start,end],
   'before_sha256':sha(data[start:end]),'after_sha256':sha(replacement),'replacement_hex':replacement.hex(),
   'active_code_units':len(cu),'total_code_units':size,'tries':0,'headers_unchanged':True})
 out[12:32]=hashlib.sha1(out[32:]).digest();struct.pack_into('<I',out,8,zlib.adler32(out[12:])&0xffffffff)
 changes=[i for i,(a,b) in enumerate(zip(data,out)) if a!=b];assert set(changes)<=allowed and len(data)==len(out)
 return bytes(out),{'input_sha256':sha(data),'output_sha256':sha(out),'changes':changes,'methods':reports,
  'new_method_field_type_string_refs':0,'null_checks':'Original done null check preserved; getContext implicitly checks view; opOpen validates URL before scheduling',
  'scope':'Two original host bodies implemented in candidate bytes; not installed/ART verified',
  'coordinator_requestId_integration':'NOT_IMPLEMENTED','ART':'NOT_VERIFIED'}
