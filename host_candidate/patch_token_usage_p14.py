#!/usr/bin/env python3
"""P14 Android local/LAN API Token display: honest provider/estimate/unavailable.

Works on the exact P6 browser-tool.zip, changes only its embedded
payload/mobile-ui/lib/client.js. Never manufactures authoritative usage.
No original Android APK changes, uploads, credentials or signing.
"""
import argparse,copy,hashlib,io,json,pathlib,zipfile
P6_BROWSER_SHA256="aedb0a6582619c319ff85d13d6ad6f1a060c12d896fbbf1068575356190e7f37"
TARGET="payload/mobile-ui/lib/client.js"
START="function mpPatchZeroTurnUsage() {"
END="function mpScheduleUsagePatch() {"
def sha(b):return hashlib.sha256(b).hexdigest()

NEW_JS=r"""function mpClassifyTurnUsage(inputText, outputText, estimate) {
            const parse = (value) => {
                const text = mpNormUsageText(value);
                if (!/^(?:[≈~]\s*)?[\d,.]+\s*tok$/i.test(text)) return null;
                const n = Number(text.replace(/[^\d.]/g, ''));
                return Number.isSafeInteger(n) && n >= 0 ? n : null;
            };
            const input = parse(inputText), output = parse(outputText);
            if (input === null || output === null) return {kind:'other'};
            if (input > 0 || output > 0) {
                const estInput = /^[≈~]/.test(mpNormUsageText(inputText));
                const estOutput = /^[≈~]/.test(mpNormUsageText(outputText));
                if (estInput || estOutput) {
                    if (estInput && estOutput)
                        return {kind:'estimate',input,output,total:input+output,source:'visible-estimate'};
                    // Per-field provenance differs. Never promote an
                    // estimated value to authoritative provider usage.
                    return {kind:'mixed',input,output};
                }
                return {kind:'provider',input,output};
            }
            // Zero from a LAN-compatible API can mean "provider did not report
            // usage", not actual zero. Never describe computed values as official.
            if (estimate && Number.isSafeInteger(estimate.inputTokens)
                && Number.isSafeInteger(estimate.outputTokens)
                && estimate.inputTokens >= 0 && estimate.outputTokens > 0
                && Number.isSafeInteger(estimate.totalTokens)
                && estimate.totalTokens >= estimate.inputTokens+estimate.outputTokens)
                return {kind:'estimate',input:estimate.inputTokens,
                    output:estimate.outputTokens,total:estimate.totalTokens,
                    source:estimate.source||'local-heuristic'};
            return {kind:'unavailable'};
        }
        function mpPatchUsageUnknownHeader(panel, label, inputValue, outputValue) {
            if (!panel || !label) return false;
            for(let r=label.parentElement,i=0;r&&i<4;r=r.parentElement,i++){
                if(mpNormUsageText(r.textContent).length>220)break;
                const walker=document.createTreeWalker(r,NodeFilter.SHOW_TEXT), matches=[];
                let text;
                while((text=walker.nextNode())){
                    if(!/^0\s*tok$/i.test(mpNormUsageText(text.nodeValue)))continue;
                    if(label.contains(text)||inputValue?.contains(text)||outputValue?.contains(text))continue;
                    matches.push(text);
                }
                if(matches.length===1){matches[0].nodeValue='— tok';return true;}
                if(matches.length>1)return false;
                if(r===panel)break;
            }
            return false;
        }
        function mpPatchZeroTurnUsage() {
            const panel=mpFindUsagePanel();
            if(!panel)return;
            const totalLabel=mpFindUsageLabel(panel,/^(本轮用量|turn usage)(（估算|未提供）|\s*\((?:estimated|unavailable)\))?$/i);
            const inputLabel=mpFindUsageLabel(panel,/^(未缓存输入|uncached input)$/i);
            const outputLabel=mpFindUsageLabel(panel,/^(输出|output)$/i);
            if(!inputLabel||!outputLabel)return;
            const totalValue=mpFindTokValue(panel,totalLabel);
            const inputValue=mpFindTokValue(panel,inputLabel);
            const outputValue=mpFindTokValue(panel,outputLabel);
            if(!inputValue||!outputValue||inputValue===outputValue)return;
            const first=mpClassifyTurnUsage(inputValue.textContent,outputValue.textContent,null);
            // Keep real provider values, including valid partial zero values.
            if(first.kind==='provider'||first.kind==='other')return;
            if(first.kind==='mixed'){
                // Do not overwrite either side; do not add differently sourced
                // tokens to an apparently authoritative turn total.
                if(totalValue&&totalValue!==inputValue&&totalValue!==outputValue &&
                   /^0\s*tok$/i.test(mpNormUsageText(totalValue.textContent)))
                    totalValue.textContent='— tok';
                mpPatchUsageUnknownHeader(panel,totalLabel,inputValue,outputValue);
                if(totalLabel)totalLabel.textContent=/本轮用量/.test(totalLabel.textContent||'')
                    ?'本轮用量（来源混合）':'Turn usage (mixed sources)';
                panel.dataset.mpUsageEstimate='0';
                panel.dataset.mpUsageEstimateSource='';
                panel.dataset.mpUsageUnavailable='0';
                panel.dataset.mpUsageMixed='1';
                return;
            }
            panel.dataset.mpUsageMixed='0';
            let est=null;
            if(first.kind!=='estimate'){
                est=mpEstimateDisplayableTurnUsage(mpUsageDialogTurn);
                if(!est)est=mpEstimateDisplayableTurnUsage(null);
                if(!est)est=mpUsageDomEstimate();
                if(!est)est=mpUsageFallbackTextEstimate();
            }
            const state=first.kind==='estimate'?first:
                mpClassifyTurnUsage(inputValue.textContent,outputValue.textContent,est);
            if(state.kind==='estimate'){
                if(first.kind!=='estimate'){
                    inputValue.textContent='≈'+state.input.toLocaleString()+' tok';
                    outputValue.textContent='≈'+state.output.toLocaleString()+' tok';
                }
                if(totalValue&&totalValue!==inputValue&&totalValue!==outputValue &&
                   /^0\s*tok$/i.test(mpNormUsageText(totalValue.textContent)))
                    totalValue.textContent='≈'+state.total.toLocaleString()+' tok';
                mpPatchUsageHeaderTotal(panel,totalLabel,inputValue,outputValue,state.total);
                if(totalLabel)totalLabel.textContent=/本轮用量/.test(totalLabel.textContent||'')
                    ?'本轮用量（估算）':'Turn usage (estimated)';
                panel.dataset.mpUsageEstimate='1';
                panel.dataset.mpUsageEstimateSource=state.source;
                panel.dataset.mpUsageUnavailable='0';
                return;
            }
            if(state.kind!=='unavailable')return;
            // Never leave an ambiguous hard-coded "0 tok" when model usage
            // wasn't returned and there is no defensible estimate.
            inputValue.textContent='— tok';
            outputValue.textContent='— tok';
            if(totalValue&&totalValue!==inputValue&&totalValue!==outputValue &&
               /^0\s*tok$/i.test(mpNormUsageText(totalValue.textContent)))
                totalValue.textContent='— tok';
            mpPatchUsageUnknownHeader(panel,totalLabel,inputValue,outputValue);
            if(totalLabel)totalLabel.textContent=/本轮用量/.test(totalLabel.textContent||'')
                ?'本轮用量（未提供）':'Turn usage (unavailable)';
            panel.dataset.mpUsageEstimate='0';
            panel.dataset.mpUsageEstimateSource='';
            panel.dataset.mpUsageUnavailable='1';
        }

        """
def patch(original:bytes):
    if sha(original)!=P6_BROWSER_SHA256:raise ValueError("P6_BROWSER_PREIMAGE_MISMATCH")
    input=zipfile.ZipFile(io.BytesIO(original))
    if input.testzip():raise ValueError("P6_BROWSER_TOOL_ZIP_CRC_FAILURE")
    names=input.namelist()
    if TARGET not in names or len(names)!=len(set(names)):raise ValueError("UNEXPECTED_BROWSER_TOOL_ENTRIES")
    src=input.read(TARGET).decode("utf8")
    if src.count(START)!=1 or src.count(END)!=1:raise ValueError("USAGE_PATCH_SCOPE_MISMATCH")
    start=src.index(START);end=src.index(END,start)
    rewritten=src[:start]+NEW_JS+src[end:]
    if rewritten.count("function mpClassifyTurnUsage(")!=1 or rewritten.count(START)!=1:
        raise ValueError("P14_INJECTION_FAILED")
    dst=io.BytesIO()
    with zipfile.ZipFile(dst,"w") as out:
        out.comment=input.comment
        for entry in input.infolist():
            payload=rewritten.encode("utf8") if entry.filename==TARGET else input.read(entry.filename)
            out.writestr(copy.copy(entry),payload)
    data=dst.getvalue()
    with zipfile.ZipFile(io.BytesIO(data)) as check:
        if check.testzip() or check.namelist()!=names:raise ValueError("P14_ZIP_CORRUPTION")
        for name in names:
            if name!=TARGET and check.read(name)!=input.read(name):
                raise ValueError("OUT_OF_SCOPE_ARCHIVE_ENTRY_CHANGED")
    return data,rewritten

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("input");p.add_argument("--output",required=True)
    p.add_argument("--js-output",required=True);args=p.parse_args()
    raw=pathlib.Path(args.input).read_bytes();data,js=patch(raw)
    pathlib.Path(args.output).write_bytes(data)
    pathlib.Path(args.js_output).write_text(js,encoding="utf8")
    print(json.dumps({"P14_INPUT_SHA256":sha(raw),"P14_OUTPUT_SHA256":sha(data),
        "P14_TOKENS":"PROVIDER_OR_ESTIMATED_OR_UNAVAILABLE",
        "P14_OTHER_BROWSER_CODE":"BYTE_IDENTICAL",
        "P14_ANDROID_RUNTIME":"NOT_VERIFIED",
        "P14_PRODUCTION_APK":"NO"},indent=2))
