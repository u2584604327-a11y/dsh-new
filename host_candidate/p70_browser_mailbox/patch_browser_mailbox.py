#!/usr/bin/env python3
"""P70 fail-closed in-process single-flight patch for exact pinned P6 browser tool.

Original shared command/result files can lose replies on overlapping calls:
each request unlinks the common RESULT_FILE before sending. This patch
serializes by home, correlates replies, classifies timeout as outcome unknown,
and stops further dispatch until a fresh verified native handshake/restart.
Does not add retries, fake success, execute external websites, or touch phones.
"""
import argparse,hashlib,io,pathlib,zipfile,sys
P6_SHA="3af586c2c83d1aea67d119357672559eb09371c77ef4e06900bb697c06d11fd5"
OUTER="output/DSH_V139_P6_ASSET_OVERLAY_NOT_APK.zip"
INNER="assets/browser-tool.zip"
SOURCE="lib/index.js"
START="async function sendCommand(home, id, payload, timeoutMs = WAIT_TIMEOUT_MS) {"
END="function writeJsonAtomic(file, value) {"
NEW= r"""// P70: this transport uses a SINGLE command and result file per DSH home.
// Enforce in-process single flight. A missing reply leaves side effects unknown.
const P70_MAILBOX_BY_HOME = new Map();
async function sendCommand(home, id, payload, timeoutMs = WAIT_TIMEOUT_MS) {
  const key = path.resolve(String(home));
  let lane = P70_MAILBOX_BY_HOME.get(key);
  if (!lane) {
    lane = { tail: Promise.resolve(), needsResync: false };
    P70_MAILBOX_BY_HOME.set(key, lane);
  }
  const previous = lane.tail;
  let finish;
  const next = new Promise((resolve) => { finish = resolve; });
  lane.tail = next;
  const queuedAt = Date.now();
  try {
    await previous;
    if (lane.needsResync) {
      return { ok: false, error: "Browser executor requires session resynchronization after missing reply",
        code: "BROWSER_MAILBOX_NEEDS_RESYNC", outcomeUnknown: true, retrySafe: false };
    }
    const budget = Number(timeoutMs);
    if (!Number.isFinite(budget) || budget <= 0 || budget > 60000) {
      return { ok: false, error: "Invalid browser tool timeout", code: "BROWSER_INVALID_TIMEOUT" };
    }
    const remaining = budget - (Date.now() - queuedAt);
    if (remaining <= 0) {
      return { ok: false, error: "Browser operation expired in local queue without being dispatched",
        code: "BROWSER_QUEUE_TIMEOUT", dispatched: false, retrySafe: true };
    }
    if (typeof id !== "string" && typeof id !== "number") {
      return { ok: false, error: "Invalid request id", code: "BROWSER_BAD_REQUEST_ID", dispatched: false };
    }
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      return { ok: false, error: "Invalid browser request body",
        code: "BROWSER_BAD_REQUEST", dispatched: false };
    }
    const cmdPath = path.join(home, CMD_FILE);
    const resPath = path.join(home, RESULT_FILE);
    try {
      try { fs.unlinkSync(resPath); } catch (error) {
        if (error?.code !== "ENOENT") throw error;
      }
      // The host, not the model-supplied request body, owns the correlation id.
      writeJsonAtomic(cmdPath, { ...payload, id });
    } catch (error) {
      return { ok: false, error: "Browser mailbox could not accept command",
        code: "BROWSER_MAILBOX_WRITE_FAILED", dispatched: false };
    }
    const deadline = Date.now() + remaining;
    while (Date.now() < deadline) {
      await sleep(POLL_INTERVAL_MS);
      const reply = readJson(resPath);
      if (reply === null || typeof reply !== "object" ||
          (typeof reply.id !== "string" && typeof reply.id !== "number") ||
          String(reply.id) !== String(id)) continue;
      return reply;
    }
    // Command might have been executed despite a missing result. Never retry
    // a click, post, payment, or message blindly; quarantine this mailbox.
    lane.needsResync = true;
    return { ok: false, error: "Browser executor did not return a matching reply; execution outcome unknown",
      code: "BROWSER_NO_REPLY_OUTCOME_UNKNOWN", outcomeUnknown: true, retrySafe: false };
  } finally {
    finish();
    if (lane.tail === next && !lane.needsResync)
      P70_MAILBOX_BY_HOME.delete(key);
  }
}
"""
def sha(data):return hashlib.sha256(data).hexdigest()
def checked_zip(data):
 with zipfile.ZipFile(io.BytesIO(data)) as z:
  if z.testzip() is not None:raise ValueError("ZIP_CRC_FAILURE")
  return z
def patch_source(data):
 text=data.decode("utf-8")
 if text.count(START)!=1 or text.count(END)!=1:
  raise ValueError("ORIGINAL_SENDCOMMAND_ANCHOR_DRIFT")
 left=text.index(START)
 right=text.index(END,left)
 old=text[left:right]
 for token in ["const cmdPath = path.join(home, CMD_FILE)",
               "const resPath = path.join(home, RESULT_FILE)",
               "fs.unlinkSync(resPath)","writeJsonAtomic(cmdPath, { id, ...payload })",
               "reply.id !== id","await sleep(POLL_INTERVAL_MS)",
               "return reply"]:
  if token not in old:raise ValueError("ORIGINAL_SHARED_MAILBOX_SHAPE_CHANGED")
 if old.count("async function sendCommand")!=1:
  raise ValueError("MULTIPLE_SENDERS_IN_ANCHOR")
 candidate=text[:left]+NEW+"\n"+text[right:]
 if candidate.count("async function sendCommand")!=1:
  raise ValueError("WRAPPER_DRIFT")
 if "function writeJsonAtomic(file, value)" not in candidate:
  raise ValueError("JSON_WRITE_HELPER_DROPPED")
 return candidate.encode("utf-8")
def rebuild_zip(blob,replace_path,new):
 src=io.BytesIO(blob);out=io.BytesIO()
 with zipfile.ZipFile(src) as source,zipfile.ZipFile(out,"w") as dest:
  if source.testzip() is not None:raise ValueError("BAD_SOURCE_ZIP_CRC")
  dest.comment=source.comment
  seen=0
  for info in source.infolist():
   raw=source.read(info.filename)
   if info.filename==replace_path:
    raw=new;seen+=1
   dest.writestr(info,raw)
  if seen!=1:raise ValueError("TARGET_FILE_NOT_UNIQUE")
 patched=out.getvalue()
 with zipfile.ZipFile(io.BytesIO(patched)) as z:
  if z.testzip() is not None:raise ValueError("PATCHED_ZIP_CRC_FAIL")
  for name in source_names(blob):
   if name!=replace_path:
    with zipfile.ZipFile(io.BytesIO(blob)) as original:
     if z.read(name)!=original.read(name):
      raise ValueError("UNAUTHORIZED_ENTRY_MUTATION")
 return patched
def source_names(blob):
 with zipfile.ZipFile(io.BytesIO(blob)) as z:return [x.filename for x in z.infolist()]
def patch(p6):
 if sha(p6)!=P6_SHA:raise ValueError("UNPINNED_P6_BASELINE")
 with zipfile.ZipFile(io.BytesIO(p6)) as outer:
  if outer.testzip() is not None:raise ValueError("P6_OUTER_CRC")
  overlay=outer.read(OUTER)
 with zipfile.ZipFile(io.BytesIO(overlay)) as stage:
  if stage.testzip() is not None:raise ValueError("P6_STAGE_CRC")
  browser=stage.read(INNER)
 with zipfile.ZipFile(io.BytesIO(browser)) as inside:
  if inside.testzip() is not None:raise ValueError("BROWSER_ASSET_CRC")
  before=inside.read(SOURCE)
 after=patch_source(before)
 fixed=rebuild_zip(browser,SOURCE,after)
 return fixed,after,before
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--p6",required=True)
 p.add_argument("--output-browser-zip",required=True)
 p.add_argument("--output-js",required=True)
 args=p.parse_args()
 fixed,new,old=patch(pathlib.Path(args.p6).read_bytes())
 pathlib.Path(args.output_browser_zip).write_bytes(fixed)
 pathlib.Path(args.output_js).write_bytes(new)
 print("P70_PINNED_P6_BROWSER_SOURCE=PASS")
 print("P70_EXACT_SHARED_MAILBOX_RACE_PATCHED=YES")
 print("P70_ORIGINAL_BROWSER_OTHER_ENTRIES_UNCHANGED=YES")
 print("P70_SOURCE_BYTES_BEFORE="+str(len(old)))
 print("P70_SOURCE_BYTES_AFTER="+str(len(new)))
 print("P70_PATCHED_BROWSER_ASSET_SHA256="+sha(fixed))
 print("P70_FIXED_SIGNATURE_APK=NOT_BUILT")
 print("P70_INSTALLED_DSH=UNCHANGED")
if __name__=="__main__":main()
