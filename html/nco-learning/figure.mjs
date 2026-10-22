import {svg,text,line,C,keyed} from '../shared/draw.mjs';
import {tspCases} from '../shared/tsp-cities.mjs';
import {rng,dist,tourLength,optimalTour,edgesOf} from '../shared/tsp-methods.mjs';
// NCOの学習と推論。問題・経路は固定した乱数で作る説明用の例で、学習済みモデルの出力ではない。
// 学習の経路は距離の近い都市ほど選ばれやすい確率で作り、推論の経路は全列挙した最適経路を描く。
const n=5,city=r=>[...Array(n)].map(()=>[+(.1+.8*r()).toFixed(2),+(.1+.8*r()).toFixed(2)]);
function sample(P,r,tau=.15){const route=[0];while(route.length<n){const c=route.at(-1),cand=[...Array(n).keys()].filter(j=>!route.includes(j)),w=cand.map(j=>Math.exp(-dist(P,c,j)/tau));let u=r()*w.reduce((a,b)=>a+b),k=0;while(k<cand.length-1&&u>w[k])u-=w[k++];route.push(cand[k]);}return [...route,0];}
// 学習の問題は、小さな地図で都市が重ならないよう、都市どうしが0.2以上離れるまで引き直す。
const spread=r=>{for(;;){const P=city(r);if(P.every((p,i)=>P.every((q,j)=>j<=i||dist(P,i,j)>=.2)))return P;}};
const r0=rng(7);
export const train=[...Array(4)].map(()=>{const P=spread(r0);return {P,route:sample(P,r0)};}).map(t=>({...t,length:tourLength(t.P,t.route)}));
export const query=tspCases[0].cities;
export const answer=optimalTour(query,0);
const steps=['同じ種類の問題を多数用意する','経路を作り、目的関数から損失を作ってモデルを更新する','新しい問題を学習済みモデルに通す'];

// 小さな地図。route を count 本まで描く。
function thumb(key,P,{x,y,s=100,route=null,count=n,opacity=1,start=true}){
 const at=([u,v])=>[+(x+u*s).toFixed(1),+(y+v*s).toFixed(1)];let b=`<rect x="${x}" y="${y}" width="${s}" height="${s}" fill="${C.paper}" stroke="#98a5b1" stroke-width="1.5"/>`;
 if(route)edgesOf(route).slice(0,count).forEach(([a,c],j)=>{const [x1,y1]=at(P[a]),[x2,y2]=at(P[c]);b+=keyed(`${key}-e${j}`,line(x1,y1,x2,y2,C.accent,false,3));});
 P.forEach((p,i)=>{const [cx,cy]=at(p);b+=i===0&&start?`<rect x="${cx-6}" y="${cy-6}" width="12" height="12" fill="${C.ink}"/>`:`<circle cx="${cx}" cy="${cy}" r="5.5" fill="${C.ink}"/>`;});
 return keyed(key,b,`opacity="${opacity}"`);}
const arrow=(key,x1,y1,x2,y2,color=C.ink,opacity=1)=>{const a=Math.atan2(y2-y1,x2-x1),h=12,p=(t)=>`${(x2-h*Math.cos(a+t)).toFixed(1)},${(y2-h*Math.sin(a+t)).toFixed(1)}`;
 return keyed(key,line(x1,y1,x2,y2,color,false,2.5)+`<polygon points="${x2},${y2} ${p(.45)} ${p(-.45)}" fill="${color}"/>`,`opacity="${opacity}"`);};
const model=(key,x,y,w,h,opacity=1)=>keyed(key,`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="10" fill="${C.B}"/>`+text(x+w/2,y+h/2+9,'モデル',25,C.paper,'middle'),`opacity="${opacity}"`);
const frame=(key,x,w,title,opacity=1)=>keyed(key,`<rect x="${x}" y="22" width="${w}" height="404" rx="8" fill="none" stroke="#b5c0ca" stroke-width="2"/>`+text(x+20,60,title,26,C.ink),`opacity="${opacity}"`);
const tx=j=>40+j*118,ty=88,M={x:205,y:330,w:150,h:70},Mi={x:780,y:190,w:120,h:70};

// k：段階。count：学習の経路を何本目まで描いたか。copy：推論側のモデルが学習側から出る途中。
function scene(k,{count=n,copy=false}={}){
 let s='';
 if(k<=2){const o=1;
  s+=frame('frame-train',16,540,'学習',o);
  train.forEach((t,j)=>{s+=thumb(`train-${j}`,t.P,{x:tx(j),y:ty,route:k>=1?t.route:null,count,opacity:o});
   if(k>=1)s+=keyed(`train-len-${j}`,text(tx(j)+50,ty+132,t.length.toFixed(2),20,C.ink,'middle'),`opacity="${count===n?o:0}"`);});
  s+=keyed('train-more',text(536,ty+58,'…',30,C.muted,'end'),`opacity="${o}"`);
  if(k>=1){s+=model('model',M.x,M.y,M.w,M.h,o);
   s+=arrow('arrow-make',M.x+30,M.y-8,M.x+30,ty+150,C.ink,count===n?o:0)+keyed('label-make',text(M.x+18,282,'経路を作る',20,C.ink,'end'),`opacity="${count===n?o:0}"`);
   s+=arrow('arrow-update',M.x+M.w-30,ty+150,M.x+M.w-30,M.y-8,C.accent,count===n?o:0)+keyed('label-update',text(M.x+M.w-18,258,'目的関数から',20,C.accent)+text(M.x+M.w-18,282,'損失を作って',20,C.accent)+text(M.x+M.w-18,306,'更新',20,C.accent),`opacity="${count===n?o:0}"`);}
  if(k>=2){s+=frame('frame-infer',578,506,'推論',o);
   s+=thumb('query',query,{x:604,y:170,s:110,opacity:copy?0:o});
   s+=model('model-inf',...(copy?[M.x,M.y,M.w,M.h]:[Mi.x,Mi.y,Mi.w,Mi.h]),copy?0:1);
   s+=arrow('arrow-in',722,225,Mi.x-8,225,C.ink,copy?0:o);
   if(!copy){s+=arrow('arrow-out',Mi.x+Mi.w+8,225,958,225,C.ink,o);s+=thumb('answer',query,{x:966,y:170,s:110,route:answer.route,opacity:o});}}}

 return svg(s,'NCOは同じ種類の問題で経路の作り方を学習し、新しい問題では学習済みモデルを1回使って経路を作る');}

export default {id:'F24',title:'NCOの学習と推論',steps,
 renderStep(k){return scene(k);},
 transition(from,to){if(to!==from+1)return null;
  if(to===1)return [{markup:scene(1,{count:0}),duration:500},...Array.from({length:n},(_,i)=>({markup:scene(1,{count:i+1}),duration:220})),{markup:scene(1),duration:500}];
  if(to===2)return [{markup:scene(2,{copy:true}),duration:350},{markup:scene(2),duration:900}];
  return null;}};
