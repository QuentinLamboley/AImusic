// Service de génération musical : clé API uniquement en mémoire de la requête.
export const runtime = "nodejs";
export const maxDuration = 300;
export const dynamic = "force-dynamic";

const API = "https://api.acemusic.ai/v1/chat/completions";
const MODEL = "acemusic/acestep-v15-turbo";
const LANG = {fr:"French",en:"English",es:"Spanish",de:"German",it:"Italian",pt:"Portuguese"};
const enc = new TextEncoder();

function looksFrench(text) {
  if (!text || !text.trim()) return false;
  const clean = text.replace(/^\s*\[[^\]]+]\s*$/gm," ");
  if (/[àâçéèêëîïôùûüœ]/i.test(clean)) return true;
  return ((clean.toLowerCase().match(/\b(une|des|les|avec|sans|dans|pour|chanson|musique|voix|guitare|batterie|couplet|refrain|joyeuse|mélancolique|le|la|qui|que|mes|nous|je|notre)\b/g))||[]).length>=2;
}

async function prepare(text,target="en") {
  if (!text?.trim() || target==="fr" || !looksFrench(text))return text;
  const source=text.trim();
  if (source.length>4500)throw Error("Le texte dépasse la longueur autorisée.");
  try {
    const p = new URLSearchParams({client:"gtx",sl:"fr",tl:target,dt:"t",q:source});
    const r = await fetch("https://translate.googleapis.com/translate_a/single?"+p,{cache:"no-store",signal:AbortSignal.timeout(6500)});
    if(!r.ok)throw Error("Premier service indisponible");
    const data=await r.json();
    const candidate = (data[0]||[]).map(x=>x?.[0]||"").join("").trim();
    if(candidate && !looksFrench(candidate))return candidate;
  }catch{}
  if(source.length<=480){
    try {
      const p = new URLSearchParams({q:source,langpair:"fr|"+target});
      const r=await fetch("https://api.mymemory.translated.net/get?"+p,{cache:"no-store",signal:AbortSignal.timeout(4500)});
      if(!r.ok)throw Error("Service indisponible");
      const data=await r.json();
      if(Number(data.responseStatus||200)!==200)throw Error("Limite");
      const candidate=String(data.responseData?.translatedText||"").trim().replaceAll("&quot;",'"').replaceAll("&#39;","'");
      if(candidate && !looksFrench(candidate))return candidate;
    }catch{}
  }
  throw Error("La préparation linguistique n'est pas disponible. Réessaie plus tard.");
}

async function lyricsForLanguage(text,lang) {
  if(lang==="fr"||!looksFrench(text))return text;
  const lines=text.split("\n"), output=[];
  let stanza=[];
  async function flush(){
    if(!stanza.length)return;
    const candidate=await prepare(stanza.join("\n"),lang);
    const rebuilt=candidate.split("\n");
    if(rebuilt.length===stanza.length)output.push(...rebuilt);
    else for(const line of stanza)output.push(await prepare(line,lang));
    stanza=[];
  }
  for(const line of lines){
    if(!line.trim()||/^\s*\[[^\]\n]+]\s*$/.test(line)){
      await flush();output.push(line);
    }else stanza.push(line);
  }
  await flush();
  return output.join("\n");
}

export async function POST(request) {
  let p;
  try{p=await request.json()}catch{return Response.json({error:"Requête incorrecte."},{status:400})}
  const key=typeof p.apiKey==="string"?p.apiKey.trim():"";
  if(!key||key.length>1024)return Response.json({error:"Ajoutez votre clé ACE Music."},{status:400});
  const mode=p.mode==="custom"?"custom":"simple";
  const language=LANG[p.language]?p.language:"fr";
  const prompt=typeof p.prompt==="string"?p.prompt.trim():"";
  const lyrics=typeof p.lyrics==="string"?p.lyrics.trim():"";
  if(!prompt||prompt.length>4500||lyrics.length>23000)return Response.json({error:"Description vide ou trop longue."},{status:400});
  const duration=Math.max(20,Math.min(360,Number(p.duration)||60));
  const format=["mp3","wav","flac"].includes(p.format)?p.format:"mp3";
  const instrumental=!!p.instrumental;
  if(mode==="custom"&&!instrumental&&!lyrics)return Response.json({error:"Ajoutez des paroles en mode Personnalisé."},{status:400});

  const stream=new ReadableStream({
    async start(controller){
      let closed=false;
      const send=(data,type="message")=>{
        if(closed)return;
        try{controller.enqueue(enc.encode("event: "+type+"\ndata: "+JSON.stringify(data)+"\n\n"))}catch{closed=true}
      };
      const ping=setInterval(()=>{if(!closed)try{controller.enqueue(enc.encode(": ping\n\n"))}catch{closed=true}},8000);
      try{
        send({stage:"prepare",text:"Préparation de votre création…"},"status");
        const musicalPrompt=(typeof p.pretranslatedPrompt==="string" && !looksFrench(p.pretranslatedPrompt))?
          p.pretranslatedPrompt.slice(0,4500):await prepare(prompt,"en");
        let finalLyrics=mode==="custom"?await lyricsForLanguage(lyrics,language):"";
        let content=musicalPrompt;
        if(mode==="simple"&&!instrumental)
          content+=" Write and sing expressive, natural original lyrics in "+LANG[language]+".";
        if(mode==="custom")
          content="<prompt>"+musicalPrompt.replaceAll("</prompt>","")+"</prompt>\n<lyrics>"+
            (instrumental?"[Instrumental]":finalLyrics.replaceAll("</lyrics>",""))+"</lyrics>";
        const audio_config={duration,format,vocal_language:language,instrumental};
        if(p.setBpm && Number(p.bpm)>=45 && Number(p.bpm)<=220)audio_config.bpm=Math.round(Number(p.bpm));
        if(p.keyScale)audio_config.key_scale=String(p.keyScale).slice(0,32);
        if(p.timeSignature)audio_config.time_signature=String(p.timeSignature).slice(0,16);
        const body={
          model:MODEL,messages:[{role:"user",content}],
          stream:true,sample_mode:mode==="simple",thinking:!!p.thinking,
          use_format:!!p.useFormat&&mode==="custom",
          use_cot_caption:false,use_cot_language:false,use_cot_metas:false,
          vocal_language:language,batch_size:1,audio_config
        };
        send({stage:"compose",text:"Votre musique prend forme…"},"status");
        const r=await fetch(API,{
          method:"POST",
          headers:{Authorization:"Bearer "+key,"Content-Type":"application/json",Accept:"text/event-stream, application/json"},
          body:JSON.stringify(body),cache:"no-store",signal:AbortSignal.timeout(235000)
        });
        if(!r.ok){
          const msg=r.status===401||r.status===403?"La clé API a été refusée.":
            r.status===429?"Le service limite les demandes pour le moment.":
            "ACE Music ne répond pas correctement (HTTP "+r.status+").";
          send({message:msg},"error");return;
        }
        if(r.headers.get("content-type")?.includes("text/event-stream") && r.body){
          const reader=r.body.getReader();
          while(true){
            const {done,value}=await reader.read();
            if(done)break;
            if(!closed)controller.enqueue(value);
          }
        }else{
          const data=await r.json();
          send(data,"music");
        }
        send({ok:true},"finish");
      }catch(e){
        const msg=e?.name==="TimeoutError"?"ACE Music n'a pas répondu à temps.":
          e?.message?.startsWith("La préparation")?e.message:
          "Le service de génération est momentanément indisponible.";
        send({message:msg},"error");
      }finally{
        clearInterval(ping);closed=true;
        try{controller.close()}catch{}
      }
    }
  });
  return new Response(stream,{headers:{
    "Content-Type":"text/event-stream; charset=utf-8",
    "Cache-Control":"no-cache, no-transform","X-Accel-Buffering":"no",
  }});
}
