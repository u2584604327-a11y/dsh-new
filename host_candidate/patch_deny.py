"""Bounded P1 default-deny DEX candidate. RAM only; NO APK/sign/install/network.
All grants remain disabled in this candidate. Does not claim per-bundle sending UI.
"""
from pathlib import Path
import hashlib,json,struct,zlib,zipfile
from loguru import logger
logger.disable('androguard')
from androguard.core.dex import DEX
ROOT=Path(__file__).resolve().parent
EXPECTED_APK='3ca56655d79afc57431636e340823e7071bc830615ca615c485b0b9a30b6e3e5'
EXPECTED_DEX='7abe21ceb6d10ae962ef4f05f46252d05c1d2b70747e94f9fb7e74ae1a398794'
SPECS={('Lcom/dsh/android/log/LogUploader;','doUpload'):'pair',
 ('Lcom/dsh/android/log/LogUploader;','retryPending'):'void',
 ('Lcom/dsh/android/log/LogUploader;','upload'):'callback',
 ('Lcom/dsh/android/LogViewerActivity;','upload$lambda$49'):'void'}
def sha(b):return hashlib.sha256(b).hexdigest()
def invoke(op,idx,regs):
 assert len(regs)<=5 and all(0<=x<16 for x in regs)
 rr=regs+[0]*(5-len(regs))
 return [op|(rr[4]<<8)|(len(regs)<<12),idx,rr[0]|rr[1]<<4|rr[2]<<8|rr[3]<<12]
def apply(original):
 if sha(original)!=EXPECTED_DEX:raise ValueError('BASELINE_DEX_MISMATCH')
 d=DEX(original);out=bytearray(original)
 types={d.get_cm_type(i):i for i in range(struct.unpack_from('<I',original,64)[0])}
 methods={(m.get_class_name(),m.get_name(),m.get_descriptor()):i for i,m in enumerate(d.get_methods())}
 ref=lambda c,n,s:methods[c,n,s]
 ctor=ref('Ljava/lang/String;','<init>','([C)V')
 log=ref('Lcom/dsh/android/log/DshLog;','w','(Ljava/lang/String; Ljava/lang/String;)I')
 box=ref('Ljava/lang/Boolean;','valueOf','(Z)Ljava/lang/Boolean;')
 pair=ref('Lkotlin/Pair;','<init>','(Ljava/lang/Object; Ljava/lang/Object;)V')
 cb=ref('Lkotlin/jvm/functions/Function2;','invoke','(Ljava/lang/Object; Ljava/lang/Object;)Ljava/lang/Object;')
 tag=d.get_strings().index('DSH');assert tag<=65535
 reports=[];allowed=set(range(8,32))
 for c in d.get_classes():
  for m in c.get_methods():
   key=(c.get_name(),m.get_name())
   if key not in SPECS:continue
   kind=SPECS[key];code=m.get_code();size=code.get_insns_size();start=m.get_code_off()+16
   label='manual' if '$lambda' in key[1] else key[1]
   message='P1_DENY '+label+' NO_AUTH n=1'
   cu=[0x0113,len(message),0x1123,types['[C']]
   fill=len(cu);cu += [0x0126,0,0,0x0022,types['Ljava/lang/String;']]
   cu += invoke(0x70,ctor,[0,1])+[0x011a,tag]+invoke(0x71,log,[1,0])
   if kind in ('pair','callback'):
    cu += [0x0212]+invoke(0x71,box,[2])+[0x020c]
   if kind=='pair':cu += [0x0322,types['Lkotlin/Pair;']]+invoke(0x70,pair,[3,2,0])+[0x0311]
   elif kind=='callback':
    callback=code.get_registers_size()-1
    cu += invoke(0x72,cb,[callback,2,0])+[0x000e]
   else:cu += [0x000e]
   handlers=[]
   if code.get_handlers():
    for h in code.get_handlers().get_list():
     handlers += [x.get_addr() for x in h.get_handlers()]
     if h.get_size()<=0:handlers.append(h.get_catch_all_addr())
   handlers=sorted(set(handlers))
   assert all(h>=len(cu) and h+2<=size for h in handlers),'handler overlap with prefix'
   payload=[0x0300,2,len(message),0]+[ord(x) for x in message]
   payload_at=next((p for p in range((len(cu)+1)//2*2,size-len(payload)+1,2)
     if all(p+len(payload)<=h or p>=h+2 for h in handlers)),None)
   assert payload_at is not None,'no bounded space'
   delta=payload_at-fill;cu[fill+1]=delta&65535;cu[fill+2]=(delta>>16)&65535
   body=[0]*size;body[:len(cu)]=cu;body[payload_at:payload_at+len(payload)]=payload
   for h in handlers:body[h:h+2]=[0x000d,0x0027]
   out[start:start+size*2]=struct.pack('<'+'H'*size,*body)
   allowed.update(range(start,start+size*2))
   reports.append({'class':key[0],'method':key[1],'method_idx':m.get_method_idx(),
    'code_off':hex(m.get_code_off()),'instruction_range':[hex(start),hex(start+size*2)],
    'prefix_code_units':len(cu),'payload_cu':payload_at,'message':message,'legacy_handler_cu':handlers,
    'registers':code.get_registers_size(),'ins':code.get_ins_size(),'outs':code.get_outs_size(),'tries':code.get_tries_size(),
    'before_instructions_sha256':sha(original[start:start+size*2]),'after_instructions_sha256':sha(out[start:start+size*2])})
 assert len(reports)==4
 out[12:32]=hashlib.sha1(out[32:]).digest();struct.pack_into('<I',out,8,zlib.adler32(out[12:])&0xffffffff)
 changes=[i for i,(a,b) in enumerate(zip(original,out)) if a!=b]
 assert len(original)==len(out) and set(changes)<=allowed
 assert original[0x301bb2:0x301bb8]==out[0x301bb2:0x301bb8]==b'\0'*6
 return bytes(out),{'status':'BOUNDED_SOURCE_CANDIDATE_NOT_ART_VERIFIED','input_sha256':sha(original),
  'candidate_sha256':sha(out),'byte_diff_count':len(changes),'byte_diff_offsets':[hex(i) for i in changes],
  'allowed_header_range':['0x8','0x20'],'methods':reports,'code_headers_and_try_handlers_unchanged':True,
  'candidate_saved':False,'grant_enabled':False,'ART':'NOT_RUN','apk_signed':False}
