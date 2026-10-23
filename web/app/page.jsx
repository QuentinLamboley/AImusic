"use client";

import {useEffect,useRef,useState} from "react";

const LANGUAGES=[
  ["fr","Français"],["en","Anglais"],["es","Espagnol"],
  ["de","Allemand"],["it","Italien"],["pt","Portugais"]
];
const CATEGORIES=[
  ["country","country authentique","authentic country","guitares acoustiques, pedal steel et basse chaleureuse","acoustic guitars, pedal steel and warm bass"],
  ["soul","soul rétro","vintage soul","piano électrique, cuivres et basse groovy","electric piano, brass and groovy bass"],
  ["jazz","jazz intimiste","intimate jazz","piano feutré, contrebasse et batterie aux balais","soft piano, double bass and brushed drums"],
  ["rock","rock indépendant","indie rock","guitares électriques cristallines et batterie live","jangly electric guitars and live drums"],
  ["folk","folk acoustique","acoustic folk","guitare fingerstyle, violon et percussions légères","fingerstyle guitar, violin and gentle percussion"],
  ["disco","disco dansant","disco","basse sautillante, cordes rythmiques et batterie disco","dancing bass, rhythm strings and disco drums"],
  ["electro","électro contemplative","downtempo electronica","synthétiseurs doux et percussions électroniques","warm synthesizers and subtle electronic percussion"],
  ["cinema","musique cinématique","cinematic orchestral","cordes majestueuses, piano et cors","lush strings, grand piano and French horns"],
  ["blues","blues du Delta","Delta blues","guitare acoustique et slide guitar","fingerpicked acoustic and slide guitars"],
  ["reggae","reggae roots","roots reggae","guitare en contretemps et basse profonde","offbeat guitars and deep bass"]
];
const MOODS=[
  ["nostalgique et chaleureuse","nostalgic and warm"],["joyeuse et entraînante","joyful and uplifting"],
  ["douce et romantique","gentle and romantic"],["mystérieuse et aérienne","mysterious and ethereal"],
  ["épique et pleine d'espoir","epic and hopeful"],["lumineuse et festive","bright and celebratory"]
];
const STORIES=[
  ["un atelier rempli de machines anciennes","a workshop full of vintage machines"],
  ["les plus beaux souvenirs d'enfance","beautiful childhood memories"],
  ["un voyage en voiture à travers les montagnes","a road trip through the mountains"],
  ["la beauté des soirées d'été","the beauty of summer evenings"],
  ["un amour qui traverse les années","a love that lasts through the years"],
  ["les retrouvailles après une longue absence","a reunion after a long separation"],
  ["un vieux village à la tombée de la nuit","an old village at nightfall"],
  ["le courage de recommencer","the courage to begin again"]
];
const VOCALS=[
  ["voix masculine grave","deep male vocals"],["voix féminine expressive","expressive female vocals"],
  ["voix douce et intimiste","soft intimate vocals"],["harmonies vocales chaleureuses","warm vocal harmonies"]
];
const DEFAULT_COUNTRY={
  prompt:"Une chanson country chaleureuse et entraînante, avec une guitare acoustique, une pedal steel guitar, une basse ronde et une voix masculine grave. Une ambiance de route au coucher du soleil, naturelle et nostalgique.",
  lyrics:"[Intro]\n\n[Verse 1]\nLe vieux moteur gronde au petit matin\nSur la route qui traverse les sapins\nLe soleil embrase les collines\nEt le vent me souffle une mélodie\n\n[Verse 2]\nJ'ai laissé la ville et ses lumières\nPour retrouver le goût de la poussière\nUn café chaud sur le tableau de bord\nEt mille kilomètres à rêver encore\n\n[Chorus]\nSur la route, le cœur en liberté\nJe laisse les soucis s'envoler\nSous le grand ciel et les étoiles\nJe trace ma route, je mets les voiles\n\n[Outro]\nLa musique jusqu'à demain"
};
const pick=values=>values[Math.floor(Math.random()*values.length)];
function createIdea(){
  const style=pick(CATEGORIES),mood=pick(MOODS),story=pick(STORIES),voice=pick(VOCALS);
  return {
    title:"Surprise "+style[1],
    prompt:"Une chanson "+style[1]+", "+mood[0]+", avec "+style[3]+", "+voice[0]+". Les paroles parlent de "+story[0]+". Production soignée, ambiance immersive.",
    english:"An original "+style[2]+" song, "+mood[1]+", featuring "+style[4]+" with "+voice[1]+". The lyrics tell a story about "+story[1]+". Rich and immersive musical production."
  };
}
function parseLyrics(text){
  if(!text)return "";
  const wrapped=text.match(/<lyrics>([\s\S]*?)<\/lyrics>/i);
  if(wrapped)return wrapped[1].trim();
  const headline=text.match(/#{1,4}\s*(lyrics|paroles)\s*:?\s*\n/i);
  if(headline)return text.slice(headline.index+headline[0].length).split(/\n#{1,4}\s+/)[0].trim();
  const first=text.match(/\[(verse|chorus|intro|outro|bridge|couplet|refrain)[^\]]*\]/i);
  return first?text.slice(first.index).trim():"";
}
function extractAudio(obj){
  const m=obj?.choices?.[0]?.delta||obj?.choices?.[0]?.message||obj?.message||obj;
  const text=typeof m?.content==="string"?m.content:"";
  const samples=m?.audio||m?.audio_data||m?.audio_base64||[];
  const items=Array.isArray(samples)?samples:[samples];
  for(const item of items){
    if(typeof item==="string"&&item.startsWith("data:audio/"))return {audio:item,content:text};
    const source=item?.audio_url?.url||item?.audio_url||item?.url||item?.data||item?.b64_json;
    if(typeof source==="string"&&source.startsWith("data:audio/"))return {audio:source,content:text};
  }
  return {audio:null,content:text};
}
function blobFromAudio(source){
  const pos=source.indexOf(",");
  if(!source.startsWith("data:audio/")||pos<0)throw Error("Format audio renvoyé non reconnu.");
  const mime=(source.slice(5,pos).split(";")[0])||"audio/mpeg";
  const encoded=source.slice(pos+1).replace(/\s/g,"");
  const decoded=atob(encoded);
  const chunks=[];
  for(let i=0;i<decoded.length;i+=65536){
    const chars=decoded.slice(i,i+65536);
    const bytes=new Uint8Array(chars.length);
    for(let k=0;k<chars.length;k++)bytes[k]=chars.charCodeAt(k);
    chunks.push(bytes);
  }
  return new Blob(chunks,{type:mime});
}
function downloadData(blob,name){
  const url=URL.createObjectURL(blob),link=document.createElement("a");
  link.href=url;link.download=name;document.body.appendChild(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function slug(str){return String(str||"chanson").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[^a-z0-9_-]+/g,"-").slice(0,60)||"musique"}
function Button({children,onClick,primary=false,disabled=false,className=""}){
  return <button type="button" onClick={onClick} disabled={disabled} className={(primary?"primary":"secondary")+" "+className}>{children}</button>;
}
function Field({label,children,hint}){return <div className="control"><label>{label}</label>{children}{hint&&<small>{hint}</small>}</div>}
function TrackCard({track}){
  return <div className="card">
    <div className="breadcrumb">♫ Votre composition</div>
    <h3>{track.title}</h3>
    <div className="track-meta">{track.created} · {track.format.toUpperCase()} · {track.mode} · {track.language}</div>
    <audio controls preload="metadata" src={track.url}/>
    <div className="actions">
      <Button onClick={()=>downloadData(track.blob,slug(track.title)+"."+track.format)}>↓ Télécharger {track.format.toUpperCase()}</Button>
      <Button onClick={()=>downloadData(new Blob([track.title+"\n\nDESCRIPTION MUSICALE\n"+track.prompt+"\n\nPAROLES\n"+(track.lyrics||track.writtenLyrics||"")],{type:"text/plain;charset=utf-8"}),slug(track.title)+"-paroles.txt")}>↓ Paroles TXT</Button>
    </div>
    {track.lyrics&&<details className="details"><summary>Voir les paroles obtenues</summary><pre style={{whiteSpace:"pre-wrap",lineHeight:1.8,color:"#dddafa"}}>{track.lyrics}</pre></details>}
  </div>;
}

export default function Studio(){
  const [tab,setTab]=useState("compose"),[mode,setMode]=useState("simple"),[apiKey,setApiKey]=useState("");
  const [prompt,setPrompt]=useState(""),[lyrics,setLyrics]=useState(""),[title,setTitle]=useState("");
  const [lang,setLang]=useState("fr"),[length,setLength]=useState(60),[format,setFormat]=useState("mp3");
  const [instrumental,setInstrumental]=useState(false),[customTempo,setCustomTempo]=useState(false),[bpm,setBpm]=useState(120);
  const [thinking,setThinking]=useState(false),[randomIdea,setRandomIdea]=useState(()=>createIdea());
  const [brief,setBrief]=useState(""),[mood,setMood]=useState("Nostalgique"),[draft,setDraft]=useState("");
  const [tracks,setTracks]=useState([]),[status,setStatus]=useState(""),[error,setError]=useState(""),[busy,setBusy]=useState(false);
  const current=useRef(null);
  useEffect(()=>()=>{tracks.forEach(t=>URL.revokeObjectURL(t.url))},[]);

  function customTemplate(){
    const theme=(brief||"la vie et ses souvenirs").trim();
    const poetic=mood==="Joyeux"?
      ["Le soleil éclaire notre chemin","Les rires traversent le jardin","On invente encore demain","Tout nous paraît possible ce matin"]:
      ["Le silence habille notre histoire","Les heures retrouvent la mémoire","Au loin s'effacent les chemins","Et nos rêves reviennent enfin"];
    setDraft("[Intro]\n\n[Verse 1]\n"+poetic[0]+"\n"+poetic[1]+"\nJe pense à "+theme.toLowerCase()+"\n\n[Verse 2]\n"+poetic[2]+"\n"+poetic[3]+"\nUn peu de lumière dans nos mains\n\n[Chorus]\nMême quand le monde tourne à l'envers\nOn garde une étoile dans l'univers\nNos voix se retrouvent sur le chemin\nEt cette chanson nous appartient\n\n[Outro]\nUn nouveau matin");
  }
  function structureDraft(){
    if(!draft.trim()){setError("Ajoutez d'abord quelques paroles.");return;}
    if(/^\s*\[(intro|verse|chorus|bridge|outro)/im.test(draft)){setStatus("Les paroles sont déjà structurées.");return;}
    const parts=draft.trim().split(/\n\s*\n/);
    const kinds=["Verse 1","Chorus","Verse 2","Chorus","Bridge","Outro"];
    setDraft(parts.map((v,i)=>"["+kinds[Math.min(i,kinds.length-1)]+"]\n"+v.trim()).join("\n\n"));
  }

  async function generate(override=null){
    if(busy)return;
    setError("");setStatus("");
    if(!apiKey.trim()){setError("Saisissez votre clé API ACE Music dans la colonne de gauche.");return;}
    const actualPrompt=override?.prompt|| (mode==="random"?randomIdea.prompt:mode==="custom"?prompt:prompt);
    if(!actualPrompt?.trim()){setError("Décrivez la chanson souhaitée.");return;}
    const actualMode=override?.mode|| (mode==="custom"?"custom":"simple");
    const actualTitle=override?.title||title|| (mode==="random"?randomIdea.title:"Ma composition");
    setBusy(true);
    const aborter=new AbortController();
    current.current=aborter;
    let content="",audioData=null,receivedError=null;
    try{
      const response=await fetch("/api/generate",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          apiKey,mode:actualMode,prompt:actualPrompt,lyrics:override?.lyrics||lyrics,
          pretranslatedPrompt:override?.english||(mode==="random"?randomIdea.english:undefined),
          language:lang,duration:override?.duration||length,format:override?.format||format,
          instrumental:override?.instrumental??instrumental,
          thinking,setBpm:customTempo,bpm
        }),signal:aborter.signal,cache:"no-store"
      });
      if(!response.ok){
        const err=await response.json().catch(()=>({}));
        throw Error(err.error||"Le service n'a pas accepté la demande.");
      }
      if(!response.body)throw Error("Aucune réponse du service.");
      setStatus("La création a commencé…");
      const reader=response.body.getReader(),decoder=new TextDecoder();
      let buffer="",processed=0;
      function handle(piece){
        const lines=piece.split("\n"),typeline=lines.find(x=>x.startsWith("event:")),typ=typeline?.slice(6).trim();
        const raw=lines.filter(x=>x.startsWith("data:")).map(x=>x.slice(5).trimStart()).join("\n");
        if(!raw||raw==="[DONE]")return;
        let data;try{data=JSON.parse(raw)}catch{return}
        if(typ==="status"){setStatus(data.text||"Création en cours…");return;}
        if(typ==="error"){receivedError=data.message||"La génération n'a pas abouti.";return;}
        const result=extractAudio(data);
        if(result.content && result.content!=="."){content+=result.content;}
        if(result.audio)audioData=result.audio;
        if(processed++%90===0)setStatus("Le morceau est en cours de composition…");
      }
      while(true){
        const {done,value}=await reader.read();
        if(done)break;
        buffer+=decoder.decode(value,{stream:true}).replaceAll("\r\n","\n");
        let idx;
        while((idx=buffer.indexOf("\n\n"))>=0){
          const frame=buffer.slice(0,idx);buffer=buffer.slice(idx+2);handle(frame);
        }
        if(buffer.length>80000000)throw Error("La réponse musicale dépasse la taille autorisée.");
      }
      if(buffer.trim())handle(buffer);
      if(receivedError)throw Error(receivedError);
      if(!audioData)throw Error("ACE Music a répondu sans fichier musical exploitable.");
      const blob=blobFromAudio(audioData);
      const mime=blob.type,extension=mime.includes("wav")?"wav":mime.includes("flac")?"flac":"mp3";
      const track={
        id:Date.now().toString(),title:actualTitle,created:new Date().toLocaleString("fr-FR"),
        mode:override?"Atelier":mode==="random"?"Aléatoire":mode==="custom"?"Personnalisé":"Simple",
        language:LANGUAGES.find(l=>l[0]===lang)?.[1]||"Français",format:extension,
        blob,url:URL.createObjectURL(blob),lyrics:parseLyrics(content),
        prompt:actualPrompt,writtenLyrics:override?.lyrics||lyrics
      };
      setTracks(previous=>{
        const list=[track,...previous];
        for(const old of list.slice(6))URL.revokeObjectURL(old.url);
        return list.slice(0,6);
      });
      if(override?.writer && track.lyrics)setDraft(track.lyrics);
      setStatus("Votre musique est prête !");
    }catch(err){
      setStatus("");
      setError(err.name==="AbortError"?"Création interrompue.":err.message||"Une erreur est survenue.");
    }finally{
      setBusy(false);current.current=null;
    }
  }
  function useDraft(){
    if(!draft.trim()){setError("Le brouillon est vide.");return;}
    setLyrics(draft.trim());setMode("custom");setTab("compose");setError("");window.scrollTo({top:0,behavior:"smooth"});
  }

  return <div className="page">
    <aside className="sidebar">
      <div><div className="logo"><span className="mark">♫</span>MÉLODIA</div><div className="slogan">Votre studio de création musicale</div></div>
      <div className="side-section">
        <label className="label" htmlFor="key">🔑 Votre clé personnelle</label>
        <input className="field" id="key" type="password" autoComplete="off"
          value={apiKey} onChange={e=>setApiKey(e.target.value)} placeholder="Collez votre clé ici…"/>
        <div style={{marginTop:11,fontSize:12,color:apiKey?"#b4e4d0":"#a3acca"}}>{apiKey?"✓ Clé renseignée":"Une clé est nécessaire pour composer"}</div>
        <p className="hint">Votre clé reste temporairement dans cet onglet. Elle est transmise uniquement au service de génération.</p>
        <a className="link" href="https://acemusic.ai/api-key" target="_blank" rel="noopener noreferrer">Obtenir ma clé ↗</a>
        {apiKey&&<div style={{marginTop:14}}><Button className="action-full compact" onClick={()=>setApiKey("")}>Oublier cette clé</Button></div>}
      </div>
      <div className="side-bottom">Écrivez votre musique en français. Explorez vos idées, écoutez et conservez vos créations.</div>
    </aside>
    <main className="main">
      <div className="hero">
        <div className="eyebrow">Votre studio musical personnel</div>
        <h1>Imaginez. Composez.<br/><em>Écoutez.</em></h1>
        <p>Décrivez la chanson dont vous rêvez, personnalisez les paroles ou laissez le hasard vous inspirer. Votre musique, à votre façon.</p>
      </div>
      <nav className="nav">
        {[["compose","🎹 Composer"],["writer","✍️ Atelier de paroles"],["library","🎧 Mes créations"]].map(([id,label])=>
          <button key={id} className={"navbtn "+(tab===id?"active":"")} onClick={()=>{setTab(id);setError("");setStatus("")}}>{label}</button>)}
      </nav>

      {tab==="compose"&&<>
        <h2>Créez votre prochain morceau</h2>
        <div className="mode-row">
          {[["simple","✨ Simple","Décrivez votre idée, nous faisons le reste."],
            ["custom","🎛️ Personnalisé","Choisissez la musique et écrivez les paroles."],
            ["random","🎲 Aléatoire","Laissez une inspiration vous surprendre."]]
            .map(([id,name,desc])=><button key={id} className={"mode "+(mode===id?"selected":"")} onClick={()=>setMode(id)}>
              <strong>{name}</strong><span>{desc}</span>
            </button>)}
        </div>
        <div className="panel">
          <div className="step"><span className="num">01</span>{mode==="simple"?"Décrivez votre idée":mode==="custom"?"Dirigez votre composition":"Laissez-vous surprendre"}</div>
          <p className="subtext">{mode==="simple"?"Racontez en quelques mots la chanson que vous aimeriez écouter.":mode==="custom"?"Décrivez le style musical, puis écrivez les paroles en respectant les sections.":"Une nouvelle idée complète, avec un style, une ambiance et une histoire."}</p>
          {mode==="random"?
            <div style={{marginTop:18}}><Field label="Votre inspiration musicale"><textarea className="field" value={randomIdea.prompt} disabled readOnly/></Field>
              <div style={{marginTop:12}}><Button onClick={()=>setRandomIdea(createIdea())}>🎲 Une autre inspiration</Button></div>
            </div>:
            <div className="inputs" style={{marginTop:18}}>
              <Field label={mode==="simple"?"La chanson que vous imaginez":"Description musicale (style, instruments, voix)"}>
                <textarea className="field" value={prompt} onChange={e=>setPrompt(e.target.value)}
                  placeholder={mode==="simple"?"Une chanson pop entraînante avec une voix grave et une mélodie qui reste en tête, sur les joies de la vie…":"Un morceau country chaleureux avec guitare acoustique, pedal steel et voix grave…"}/>
              </Field>
              {mode==="custom"&&<>
                <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:12,flexWrap:"wrap"}}>
                  <strong>Paroles structurées</strong>
                  <Button className="compact" onClick={()=>{setPrompt(DEFAULT_COUNTRY.prompt);setLyrics(DEFAULT_COUNTRY.lyrics);setTitle("La route et le vent")}}>Charger l’exemple country</Button>
                </div>
                <div className="tags">{["Intro","Verse 1","Verse 2","Chorus","Bridge","Outro"].map(tag=>
                  <button key={tag} onClick={()=>setLyrics(v=>(v.trimEnd()?v.trimEnd()+"\n\n":"")+"["+tag+"]\n")}>+ {tag}</button>)}</div>
                <textarea className="field large" value={lyrics} onChange={e=>setLyrics(e.target.value)}
                  placeholder={"[Intro]\n\n[Verse 1]\nPremier vers de votre chanson\n\n[Chorus]\nLe refrain de votre choix\n\n[Outro]\nDernier vers"}/>
              </>}
            </div>}
        </div>
        <div className="panel">
          <div className="step"><span className="num">02</span>Choisissez vos réglages</div>
          <div className="inputs" style={{marginTop:18}}>
            <Field label="Titre de votre chanson (facultatif)">
              <input className="field" value={title} onChange={e=>setTitle(e.target.value)} placeholder="Une nuit inoubliable"/>
            </Field>
            <div className="formgrid">
              <Field label="Langue des paroles"><select className="field" value={lang} onChange={e=>setLang(e.target.value)}>{LANGUAGES.map(([v,l])=><option value={v} key={v}>{l}</option>)}</select></Field>
              <Field label="Format audio"><select className="field" value={format} onChange={e=>setFormat(e.target.value)}>{["mp3","wav","flac"].map(v=><option key={v} value={v}>{v.toUpperCase()}</option>)}</select></Field>
              <Field label={"Durée : "+length+" secondes"}><input type="range" min="20" max="240" step="10" value={length} onChange={e=>setLength(Number(e.target.value))}/></Field>
            </div>
            <label className="check"><input type="checkbox" checked={instrumental} onChange={e=>setInstrumental(e.target.checked)}/>Instrumental, sans chant</label>
            <details className="details"><summary>Réglages avancés</summary>
              <div className="formgrid">
                <label className="check"><input type="checkbox" checked={customTempo} onChange={e=>setCustomTempo(e.target.checked)}/>Tempo personnalisé</label>
                <Field label="BPM"><input type="number" className="field" min={45} max={220} disabled={!customTempo} value={bpm} onChange={e=>setBpm(Number(e.target.value))}/></Field>
                <label className="check"><input type="checkbox" checked={thinking} onChange={e=>setThinking(e.target.checked)}/>Composition enrichie</label>
              </div>
            </details>
          </div>
        </div>
        <div className="panel">
          <div className="step"><span className="num">03</span>Écoutez votre création</div>
          <p className="subtext">La génération utilise votre clé ACE Music. Elle peut prendre quelques minutes selon la disponibilité du service.</p>
          <div style={{marginTop:18}}><Button primary className="action-full" disabled={busy} onClick={()=>generate()}>{busy?"♫ Composition en cours…":"✦ Créer ma musique"}</Button></div>
          {busy&&<div style={{marginTop:11}}><Button className="action-full compact" onClick={()=>current.current?.abort()}>Annuler l'attente</Button></div>}
        </div>
        {tracks.length>0&&<><h2>Votre dernière création</h2><TrackCard track={tracks[0]}/></>}
      </>}

      {tab==="writer"&&<>
        <h2>Atelier de paroles</h2>
        <p className="subtext">Imaginez un sujet. Préparez un brouillon ou demandez à ACE Music de créer une chanson complète à partir de votre idée.</p>
        <div className="panel">
          <Field label="De quoi doit parler votre chanson ?"><textarea className="field" value={brief} onChange={e=>setBrief(e.target.value)}
            placeholder="Une chanson pour mon père, passionné de vieilles mécaniques, qui invente toujours quelque chose de nouveau…"/></Field>
          <div className="two-cols" style={{marginTop:18}}>
            <div><Field label="Ambiance"><select className="field" value={mood} onChange={e=>setMood(e.target.value)}>{["Nostalgique","Joyeux"].map(v=><option key={v}>{v}</option>)}</select></Field>
              <div style={{marginTop:13}}><Button className="action-full" onClick={customTemplate}>Créer une ébauche sans API</Button></div></div>
            <div><strong>Écriture par ACE Music</strong><p className="hint">Cette option génère également une courte démo musicale.</p>
              <Button primary className="action-full" disabled={busy} onClick={()=>{
                if(!brief.trim()){setError("Décrivez le thème de la chanson.");return;}
                generate({writer:true,mode:"simple",title:"Ébauche : "+brief.slice(0,35),prompt:"Écris une chanson expressive et originale sur ce sujet : "+brief+". Structure la chanson avec des couplets et un refrain.",duration:45,format:"mp3",instrumental:false})
              }}>✨ Créer avec ACE Music</Button></div>
          </div>
          <div style={{marginTop:25}}>
            <Field label="Brouillon modifiable"><textarea className="field large" value={draft} onChange={e=>setDraft(e.target.value)}
              placeholder={"[Verse 1]\n\n[Chorus]\n…"}/></Field>
          </div>
          <div className="actions" style={{marginTop:14}}><Button onClick={structureDraft}>Structurer les paroles</Button>
            <Button primary onClick={useDraft}>Utiliser en mode Personnalisé ↗</Button></div>
        </div>
      </>}

      {tab==="library"&&<>
        <h2>Mes créations</h2>
        <p className="subtext">Vos six dernières chansons restent accessibles tant que cette page est ouverte. Téléchargez-les pour les conserver.</p>
        {tracks.length?tracks.map(t=><TrackCard key={t.id} track={t}/>):
          <div className="empty"><div className="music-note">♫</div><h3>Votre bibliothèque est prête</h3><p>Vos premières compositions apparaîtront ici.</p></div>}
      </>}

      {busy&&<div className="status"><span className="dot"/>{status||"Préparation de votre musique…"}</div>}
      {!busy&&status&&<div className="notice ok">{status}</div>}
      {error&&<div className="notice error">{error}</div>}
      <footer>MÉLODIA · Studio de musique personnel · Pensez à télécharger vos créations avant de fermer la page.</footer>
    </main>
  </div>;
}
