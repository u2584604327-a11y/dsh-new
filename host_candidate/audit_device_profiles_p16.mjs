import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
/** P16 only inspects model-visible device-mode presets; it does not
 * manipulate real website verification or claim to replace Android identity.
 */
const src=fs.readFileSync(process.argv[2],"utf8");
const start=src.indexOf("const DEVICE_PROFILES = {");
const end=src.indexOf("\n};",start)+3;
assert.ok(start>=0&&end>start,"device profiles exact source block not found");
const context={};vm.createContext(context);
vm.runInContext(src.slice(start,end).replace(/^const /,"var "),context);
const profiles=context.DEVICE_PROFILES;
assert.ok(profiles&&typeof profiles==="object");
assert.ok(profiles.auto&&profiles.iphone&&profiles.ipad&&profiles.desktop);
const report={};
for(const [mode,p] of Object.entries(profiles)){
  if(mode!=="auto"){
    // CSS-pixel viewport dimensions may be fractional (high-DPR or foldable profiles).
    assert.ok(Number.isFinite(p.width)&&p.width>0&&p.width<10000,mode+": invalid viewport width");
    assert.ok(Number.isFinite(p.height)&&p.height>0&&p.height<10000,mode+": invalid viewport height");
    assert.ok(typeof p.ua==="string"&&p.ua.startsWith("Mozilla/5.0"),mode+": no declared UA");
    assert.ok(Number.isFinite(p.dpr)&&p.dpr>0,mode+": invalid device pixel ratio");
  } else {
    assert.equal(p.ua,null,"native mode must restore Android system UA");
  }
  report[mode]={viewportDeclared:Number.isFinite(p.width),uaDeclared:!!p.ua,
    simulatedPresentation:mode!=="auto",actualPlatform:"Android WebView",
    realHardwareIdentityChanged:false};
}
const nativeDisclaimer=src.includes("The engine remains Android WebView/Chromium");
assert.ok(nativeDisclaimer,"model device tool must disclose underlying Android engine");
assert.ok(src.includes("The native WebView network User-Agent is applied before navigation"),
          "model should explain native UA semantics");
console.log("P16_DEVICE_PRESET_VALIDATION=PASS");
console.log("P16_DEVICE_PRESET_COUNT="+Object.keys(profiles).length);
console.log("P16_AUTO_RESTORE_NATIVE_ANDROID_UA=PASS_SOURCE");
console.log("P16_ANDROID_ENGINE_DISCLOSURE=PASS_SOURCE");
console.log("P16_REAL_IOS_WINDOWS_HARDWARE_IDENTITY=NOT_ACHIEVABLE_FROM_WEBVIEW");
console.log("P16_REMOTE_SITE_FINGERPRINT_CONSISTENCY=NOT_TESTED");
console.log("P16_SEPARATE_BROWSER_UID_AND_WEBVIEW_STORAGE=NOT_VERIFIED");
