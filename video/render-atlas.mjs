import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { spawn, execFileSync } from 'node:child_process';
import { once } from 'node:events';
const root=path.resolve(import.meta.dirname,'..');
const deps=process.env.RUNTIME_NODE_MODULES || 'C:/Users/Vansh/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const require=createRequire(path.join(deps,'_atlas-video.cjs'));
const {createCanvas,loadImage,GlobalFonts}=require('@napi-rs/canvas');
const sharp=require('sharp');
GlobalFonts.registerFromPath('C:/Windows/Fonts/arial.ttf','Arial');
GlobalFonts.registerFromPath('C:/Windows/Fonts/arialbd.ttf','Arial Bold');
const W=1920,H=1080,FPS=30,DURATION=48;
const build=path.join(root,'.video-build'), assets=path.join(root,'video/assets');
await fs.mkdir(build,{recursive:true});await fs.mkdir(assets,{recursive:true});
const html=await fs.readFile(path.join(root,'api/static/maintenance/index.html'),'utf8');
let plane=html.slice(html.indexOf('<svg id="planeSvg"'),html.indexOf('</svg>',html.indexOf('<svg id="planeSvg"'))+6);
plane=plane.replace(/<ellipse cx="500" cy="350"[^>]*\/>/,'');
const planeStyle=`<style>.plane-seg{fill:url(#wingMetal);stroke:#83a69b;stroke-width:1.2}.fuselage-body{fill:url(#aircraftMetal)}.engine-body{fill:url(#engineMetal)}.wing-control{fill:#9fc0b1}.wing-spoiler{fill:#c9ded3}.wing-slat{fill:#e5f2eb}.wing-tip,.rudder-body{fill:#467e6b}.gear-panel{fill:#9eb5ac}.door-panel{fill:#c5d7ce}.aircraft-labels{display:none}.aircraft-decoration{pointer-events:none}</style>`;
const inject=(svg,css)=>svg.replace(/(<svg[^>]*>)/,'$1'+css);
await sharp(Buffer.from(inject(plane,planeStyle))).resize(1500).png().toFile(path.join(assets,'aircraft.png'));
const maskStyle=`<style>.plane-seg{fill:none;stroke:none}.aircraft-decoration,.aircraft-labels{display:none}#seg-engine-l{fill:#ef9c84;stroke:#faac96;stroke-width:3}</style>`;
await sharp(Buffer.from(inject(plane,maskStyle))).resize(1500).png().toFile(path.join(assets,'engine-highlight.png'));
// Reuse the actual engine geometry authored for the Atlas explorer.
const source=(await fs.readFile(path.join(root,'api/static/maintenance/component-explorer.mjs'),'utf8')).replace(/\r/g,'');
const start=source.indexOf('const engine = ')+15,end=source.indexOf(';\n const wing',start);
if(start<15||end<0)throw new Error('Engine illustration was not found');
const engine=Function('return ('+source.slice(start,end)+')')();
const engineSvg=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 330"><style>.ce-shell{fill:#e0eee6;stroke:#739789;stroke-width:2}.ce-metal{fill:#afcdbb;stroke:#719480;stroke-width:2}.ce-flow{fill:none;stroke:#c69c58;stroke-width:6;stroke-dasharray:10 6}.ce-reservoir{fill:#f4dfb5;stroke:#ac8950;stroke-width:2}.ce-bearing{fill:#edf6ee;stroke:#537f68;stroke-width:5}</style>${engine}</svg>`;
await sharp(Buffer.from(engineSvg)).resize(1500).png().toFile(path.join(assets,'engine-cutaway.png'));
const planeImage=await loadImage(path.join(assets,'aircraft.png'));
const engineMask=await loadImage(path.join(assets,'engine-highlight.png'));
const engineImage=await loadImage(path.join(assets,'engine-cutaway.png'));
const C={navy:'#0b2129',ink:'#112f32',mint:'#a1dfc2',muted:'#91aba7',paper:'#f2f8f4',coral:'#efa08a',white:'#f4faf7',amber:'#dbc18f'};
const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const ease=v=>{v=clamp(v);return 1-Math.pow(1-v,3);};
const smooth=v=>{v=clamp(v);return v*v*(3-2*v);};
function font(c,size,weight=400){c.font=`${weight>=600?'bold ':''}${size}px ${weight>=600?'"Arial Bold"':'Arial'}`;}
function tx(c,text,x,y,size=44,color=C.white,weight=400,align='left'){font(c,size,weight);c.fillStyle=color;c.textAlign=align;c.textBaseline='alphabetic';c.fillText(text,x,y);c.textAlign='left';}
function multi(c,lines,x,y,size=90,color=C.white,weight=700,line=1.13){lines.split('\n').forEach((v,i)=>tx(c,v,x,y+i*size*line,size,color,weight));}
function rect(c,x,y,w,h,r=20,fill='#15363c',stroke=null){c.beginPath();c.roundRect(x,y,w,h,r);if(fill){c.fillStyle=fill;c.fill();}if(stroke){c.strokeStyle=stroke;c.lineWidth=2;c.stroke();}}
function line(c,points,color,width=2,dash=[]){c.beginPath();c.moveTo(...points[0]);points.slice(1).forEach(p=>c.lineTo(...p));c.strokeStyle=color;c.lineWidth=width;c.setLineDash(dash);c.stroke();c.setLineDash([]);}
function circle(c,x,y,r,fill){c.beginPath();c.arc(x,y,r,0,Math.PI*2);c.fillStyle=fill;c.fill();}
function background(c,time){const g=c.createLinearGradient(0,0,W,H);g.addColorStop(0,C.navy);g.addColorStop(1,'#143c3d');c.fillStyle=g;c.fillRect(0,0,W,H);c.save();c.globalAlpha=.16;for(let i=0;i<68;i++){const x=(i*337.17+time*(8+i%3))%W;const y=(i*191.53+Math.sin(time*.4+i)*25)%H;circle(c,x,y,1.2+i%2,'#b3d9c5');}c.restore();}
function chrome(c,section,index){tx(c,'atlas',125,93,44,C.white,700);tx(c,'MAINTENANCE COPILOT',255,91,19,C.muted,700);tx(c,section.toUpperCase(),W-125,90,18,C.muted,400,'right');tx(c,String(index+1).padStart(2,'0'),W-125,H-68,20,C.muted,400,'right');}
function headline(c,caption,t){const a=ease(t/.65);c.save();c.globalAlpha=a;multi(c,caption,125,235+(1-a)*36,82,C.white,700,1.14);c.restore();}
function drawPlane(c,x,y,width,angle=0,glow=0,time=0){c.save();c.translate(x,y);c.rotate(angle);const height=width*planeImage.height/planeImage.width;c.drawImage(planeImage,-width/2,-height/2,width,height);if(glow){c.globalAlpha=glow*(.65+.3*Math.sin(time*3));c.shadowColor=C.coral;c.shadowBlur=35;c.drawImage(engineMask,-width/2,-height/2,width,height);}c.restore();}
function label(c,text,x,y,size=23){tx(c,text,x,y,size,C.muted);}
function flowing(c,a,b,p,color=C.mint){line(c,[a,b],color,3);for(let i=0;i<4;i++){const q=(p*.3+i*.25)%1;circle(c,a[0]+(b[0]-a[0])*q,a[1]+(b[1]-a[1])*q,5,color);}}
const scenes=[
 {start:0,end:5,name:'THE PROJECT',draw(c,t){chrome(c,'Historical maintenance, explained',0);headline(c,'Meet Maintenance\nAtlas',t);label(c,'Aviation troubleshooting with traceable evidence',130,485,29);const p=smooth(t/5);drawPlane(c,1450-p*95,630-p*70,920+p*40,.48+Math.sin(t*.5)*.025,0,t);c.save();c.globalAlpha=.18;for(let i=0;i<5;i++){line(c,[[920+i*160+t*45,1050],[1120+i*160+t*45,850]],C.mint,2);}c.restore();label(c,'NexAI 2026 / Problem Statement 1.3',130,938,24);}},
 {start:5,end:10,name:'REPORT THE SYMPTOM',draw(c,t){chrome(c,'Start with what you noticed',1);headline(c,'Describe the fault, naturally',t);const a=ease((t-.4)/.7);c.save();c.globalAlpha=a;const y=435+(1-a)*45;rect(c,170,y,1580,270,25,'#f1f8f3');tx(c,'What did you notice?',225,y+60,27,'#5a8271',700);const q='Oil leaking from engine one';const n=Math.floor(clamp((t-.8)/1.7)*q.length);tx(c,q.slice(0,n),225,y+151,66,'#193f36');if(t<3.7&&Math.sin(t*9)>-.2){c.fillStyle='#4e977a';c.fillRect(229+c.measureText(q.slice(0,n)).width,y+92,4,72);}tx(c,'One place for questions and follow-ups',225,y+226,25,'#79958a');c.restore();label(c,'Plain-language input, before technical detail',170,829,29);}},
 {start:10,end:16,name:'SEARCH THE HISTORY',draw(c,t){chrome(c,'Relevant precedent, original records',2);headline(c,'Search thousands of maintenance records',t);const converge=ease((t-.7)/3.8);for(let i=0;i<98;i++){const ix=150+(i*173)%1600,iy=405+(i*119)%510;const targetX=970+Math.cos(i)*125,targetY=661+Math.sin(i)*115;const q=converge*.72;circle(c,ix*(1-q)+targetX*q,iy*(1-q)+targetY*q,3+i%3,i%7===0?C.coral:'#68a990');}const rows=[['Reported oil loss','Original problem text'],['Similar component symptoms','Recorded maintenance action'],['Relevant historical context','Source record references']];rows.forEach(([a,b],i)=>{const p=ease((t-i*.25-.5)/.7);c.save();c.globalAlpha=p;const x=200+i*510+(1-p)*50,y=530+Math.sin(t*.8+i)*12;rect(c,x,y,450,230,18,'#173a3d','#38645e');tx(c,a,x+28,y+75,29,C.white,700);tx(c,b,x+28,y+135,24,C.muted);tx(c,'Illustrative record preview',x+28,y+190,20,C.mint);c.restore();});label(c,'Search results provide context for investigation',130,964,28);}},
 {start:16,end:22,name:'HYBRID RETRIEVAL',draw(c,t){chrome(c,'BM25 + BGE + rank fusion',3);headline(c,'Keywords and meaning, working together',t);const p=ease((t-.3)/.9);c.save();c.globalAlpha=p;const nodes=[[250,420,535,150,'Exact keyword matches','BM25 lexical retrieval'],[250,690,535,150,'Similar meaning matches','BGE semantic embeddings'],[1130,553,540,150,'Ranked evidence comes together','Reciprocal Rank Fusion']];flowing(c,[785,495],[1130,628],t);flowing(c,[785,765],[1130,628],t+.4);for(const [x,y,w,h,a,b]of nodes){rect(c,x,y,w,h,18,'#16383c','#54877a');tx(c,a,x+25,y+61,31,C.white,700);tx(c,b,x+25,y+110,24,C.mint);}c.restore();label(c,'Component, side and number distinctions matter',250,955,27);}},
 {start:22,end:27,name:'EVIDENCE BEFORE EXPLANATION',draw(c,t){chrome(c,'Original fields stay accessible',4);headline(c,'Every answer carries its evidence',t);const a=ease((t-.3)/.7);c.save();c.globalAlpha=a;rect(c,200,407,1520,460,24,'#f1f8f3');tx(c,'Illustrative demo record only',250,468,25,'#6b887b',700);tx(c,'DEMO-007',250,544,42,'#327359',700);tx(c,'Oil leak reported beneath engine one.',250,627,48,'#193f36',700);tx(c,'Origin not confirmed by this record.',250,697,43,'#193f36');line(c,[[250,741],[1650,741]],'#c1d7c9',2);tx(c,'Inspect the original source field',250,812,29,'#577e6b');const scan=clamp((t-1.1)/1.5);c.globalAlpha=.23;c.fillStyle='#93cdb1';c.fillRect(244,581,1325*scan,69);c.restore();label(c,'Historical actions do not establish repair success',200,968,27);}},
 {start:27,end:32,name:'BOUNDED ANSWERS',draw(c,t){chrome(c,'A refusal is a useful result',5);headline(c,'When evidence is weak, abstain',t);label(c,'Illustrative signals, not measured scores',160,396,25);const bars=[['Component agreement',.84,C.mint],['Symptom agreement',.53,C.amber],['Source specificity',.14,C.coral]];bars.forEach(([name,value,col],i)=>{const y=491+i*130;tx(c,name,160,y-20,25,C.muted);rect(c,160,y,760,28,14,'#24494a');rect(c,160,y,Math.max(28,760*value*ease((t-.3-i*.2)/1)),28,14,col);});const a=ease((t-1.3)/.8);c.save();c.globalAlpha=a;multi(c,'Insufficient evidence\nfor this request',1050,555+(1-a)*30,53,C.coral,700,1.25);label(c,'Missing context stays explicit',1050,759,27);c.restore();}},
 {start:32,end:38,name:'AIRCRAFT EXPLORER',draw(c,t){chrome(c,'Follow the reported location',6);headline(c,'Locate the reported fault',t);drawPlane(c,900+Math.sin(t*.6)*10,668,1060,0,ease((t-.7)/1),t);const a=ease((t-1.1)/.7);c.save();c.globalAlpha=a;line(c,[[695,620],[418,548],[225,548]],C.coral,3);circle(c,695,620,9,C.coral);tx(c,'Engine one oil leak',170,509,35,C.coral,700);tx(c,'Reported location only',1310,601,29,C.mint,700);tx(c,'Internal source unconfirmed',1310,653,25,C.muted);c.restore();label(c,'Illustrative airframe, with selectable regions',130,986,25);}},
 {start:38,end:43,name:'INTERNAL COMPONENTS',draw(c,t){chrome(c,'Geometry explains component context',7);headline(c,'Explore the parts beneath symptoms',t);const a=ease((t-.3)/.7);c.save();c.globalAlpha=a;rect(c,105,436,1130,487,22,'#eef7f1');c.drawImage(engineImage,125,460,1090,450);const x=125+145/800*1090,y=460+174/330*450;c.save();c.translate(x,y);c.scale(.38,1);c.rotate(t*1.65);for(let i=0;i<10;i++){c.rotate(Math.PI/5);c.beginPath();c.moveTo(0,-10);c.quadraticCurveTo(18,-41,8,-64);c.quadraticCurveTo(-10,-39,-3,-11);c.fillStyle='#638c79';c.fill();}circle(c,0,0,9,'#315e4b');c.restore();c.setLineDash([10,7]);c.lineDashOffset=-t*22;line(c,[[483,558],[690,558],[690,610]],'#d29565',4,[10,7]);c.setLineDash([]);const pulse=.5+.3*Math.sin(t*3);c.globalAlpha=pulse;circle(c,690,610,34,'#ef9c84');c.restore();multi(c,'Oil leak source\nremains unknown',1330,522,42,C.white,700,1.3);tx(c,'Storage, supply, seals, return',1330,689,26,C.mint);multi(c,'Possible complications\nstay clearly labeled',1330,782,29,C.muted,400,1.35);label(c,'Unverified educational scenario only',145,987,24);}},
 {start:43,end:48,name:'MAINTENANCE ATLAS',draw(c,t){chrome(c,'Evidence supports human judgment',8);headline(c,'Investigate faster.\nKeep the evidence.',t);const a=ease((t-.5)/1);c.save();c.globalAlpha=a;tx(c,'Maintenance Atlas',130,594,72,C.mint,700);tx(c,'Historical context. Human judgment.',133,690,35,C.muted);tx(c,'Live deployment checks remain pending',133,957,24,C.muted);drawPlane(c,1480+t*35,605-t*15,730,.5,0,t);c.restore();}}
];
const canvas=createCanvas(W,H),ctx=canvas.getContext('2d');
const aCanvas=createCanvas(W,H),aCtx=aCanvas.getContext('2d'),bCanvas=createCanvas(W,H),bCtx=bCanvas.getContext('2d');
function sceneRender(c,scene,t){background(c,scene.start+t);scene.draw(c,t);}
const ffmpeg=process.env.ATLAS_FFMPEG || execFileSync('python',['-c',"import sys;sys.path.insert(0,'.video-build/deps');import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"],{cwd:root,encoding:'utf8'}).trim();
const soundtrack=path.join(build,'soundtrack.wav');
const out=path.join(root,'video/Maintenance-Atlas-Showcase.mp4');
const args=['-y','-f','rawvideo','-pix_fmt','rgba','-s',`${W}x${H}`,'-r',String(FPS),'-i','pipe:0','-i',soundtrack,'-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-threads','4','-c:a','aac','-b:a','160k','-af','afade=t=in:st=0:d=1.5,afade=t=out:st=45:d=3','-t',String(DURATION),'-movflags','+faststart',out];
const child=spawn(ffmpeg,args,{stdio:['pipe','ignore','pipe']});let errorOutput='';child.stderr.on('data',b=>{errorOutput+=b.toString();if(errorOutput.length>15000)errorOutput=errorOutput.slice(-15000);});let broken=null;child.stdin.on('error',e=>broken=e);
const checkpoints=new Set(scenes.map(s=>Math.round((s.start+2.3)*FPS)));let sceneIndex=0;
const started=Date.now();
for(let frame=0;frame<FPS*DURATION;frame++){
 if(broken)throw broken;
 const time=frame/FPS;while(sceneIndex<scenes.length-1&&time>=scenes[sceneIndex].end)sceneIndex++;
 const scene=scenes[sceneIndex];sceneRender(aCtx,scene,time-scene.start);ctx.globalAlpha=1;ctx.drawImage(aCanvas,0,0);
 const blend=smooth((time-(scene.end-.45))/.45);
 if(blend>0&&sceneIndex<scenes.length-1){sceneRender(bCtx,scenes[sceneIndex+1],0);ctx.globalAlpha=blend;ctx.drawImage(bCanvas,0,0);ctx.globalAlpha=1;}
 if(time<.5){ctx.fillStyle=`rgba(4,16,22,${1-smooth(time/.5)})`;ctx.fillRect(0,0,W,H);}
 if(time>DURATION-.7){ctx.fillStyle=`rgba(4,16,22,${smooth((time-DURATION+.7)/.7)})`;ctx.fillRect(0,0,W,H);}
 if(checkpoints.has(frame))await fs.writeFile(path.join(build,`scene-${sceneIndex+1}.png`),canvas.toBuffer('image/png'));
 const pixels=ctx.getImageData(0,0,W,H).data;
 if(!child.stdin.write(Buffer.from(pixels.buffer,pixels.byteOffset,pixels.byteLength)))await once(child.stdin,'drain');
 if(frame%(FPS*6)===0)console.log(`Rendered ${frame/FPS}s / ${DURATION}s (${Math.round((Date.now()-started)/1000)}s elapsed)`);
}
child.stdin.end();const [exit]=await once(child,'close');await fs.writeFile(path.join(build,'encode.log'),errorOutput);if(exit!==0)throw new Error('Video encoder failed: '+errorOutput.slice(-1500));
await fs.copyFile(path.join(build,'scene-1.png'),path.join(root,'video/preview.png'));
const montage=createCanvas(1920,1080),m=montage.getContext('2d');for(let i=0;i<9;i++){const im=await loadImage(path.join(build,`scene-${i+1}.png`));m.drawImage(im,(i%3)*640,Math.floor(i/3)*360,640,360);}await fs.writeFile(path.join(build,'contact-sheet.png'),montage.toBuffer('image/png'));
console.log(JSON.stringify({output:out,duration:DURATION,fps:FPS,width:W,height:H,seconds:Math.round((Date.now()-started)/1000)}));
