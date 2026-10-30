"""Bounded original configureWebView hardening; NOT storage/UID isolation.
Requires exact previous six-method candidate. No APK, no installs, no new IDs.
"""
import struct,hashlib,zlib
from androguard.core.dex import DEX
from patch_deny import sha,invoke
EXPECTED='24e5f4a24da838f306f489eae9ca086da3caa5db481c63080abf0e005d6dce72'
KEY=('Lcom/dsh/android/browser/AiBrowserView;','configureWebView')
def apply_privacy(data):
 if sha(data)!=EXPECTED:raise ValueError('SIX_METHOD_PREIMAGE_MISMATCH')
 d=DEX(data)
 methods={(m.get_class_name(),m.get_name(),m.get_descriptor()):i for i,m in enumerate(d.get_methods())}
 file_ref=methods['Landroid/webkit/WebSettings;','setAllowFileAccess','(Z)V']
 m=next(m for c in d.get_classes() for m in c.get_methods() if (c.get_name(),m.get_name())==KEY)
 co=m.get_code();off=m.get_code_off()
 assert (off,co.get_registers_size(),co.get_ins_size(),co.get_outs_size(),co.get_tries_size(),co.get_insns_size())==(0x345020,11,2,6,0,107)
 body=bytearray();changes=[];removed=[]
 for rel,i in m.get_instructions_idx():
  raw=i.get_raw();name=i.get_name();text=i.get_output()
  assert not name.startswith(('if-','goto','packed-switch','sparse-switch')) and 'payload' not in name
  if rel==78:
   body+=struct.pack('<3H',*invoke(0x6e,file_ref,[0,2]));changes.append('setAllowFileAccess(false) using existing v2=0')
   assert 'setMixedContentMode' in text
   raw=struct.pack('<3H',*invoke(0x6e,i.get_operands()[-1][1],[0,1]));changes.append('MIXED_CONTENT_NEVER_ALLOW via existing v1=1')
  elif rel==144:
   assert 'setAcceptCookie' in text
   raw=b'\0'*6;changes.append('remove global CookieManager.setAcceptCookie mutation; no cookie clearing')
  elif rel==150:
   assert 'setAcceptThirdPartyCookies' in text
   raw=struct.pack('<3H',*invoke(0x6e,i.get_operands()[-1][1],[0,10,6]));changes.append('third-party cookies false using existing v6=0')
  elif rel in (166,186):
   assert name=='check-cast' and ('WebViewClient' in text or 'WebChromeClient' in text)
   removed.append({'offset':rel,'redundant_cast':text});continue
  body+=raw
 assert len(body)==212
 body+=b'\0\0';assert len(body)==214
 out=bytearray(data);out[off+16:off+16+214]=body
 out[12:32]=hashlib.sha1(out[32:]).digest();struct.pack_into('<I',out,8,zlib.adler32(out[12:])&0xffffffff)
 diff=[i for i,(a,b) in enumerate(zip(data,out)) if a!=b]
 assert set(diff)<=set(range(8,32))|set(range(off+16,off+16+214))
 return bytes(out),{'class':KEY[0],'method':KEY[1],'input_sha256':sha(data),'output_sha256':sha(out),
 'instruction_range':[off+16,off+16+214],'before_sha256':sha(data[off+16:off+16+214]),'after_sha256':sha(body),
 'replacement_hex':body.hex(),'changes':changes,'removed_casts':removed,
 'changed_byte_offsets':diff,'code_headers_tries_tables_unchanged':True,'new_refs':0,'ART':'NOT_VERIFIED',
 'limitations':['No storage profile separation','Content access unchanged','No privileged bridge/permission closure',
 'Can change third-party login and local file page behavior; runtime NOT_VERIFIED']}
