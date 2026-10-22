import {svg,text,rect,C,keyed,mapFrame} from '../shared/draw.mjs';
import {tspCases as cases} from '../shared/tsp-cities.mjs';
// 先頭を出発都市とし、残りN−1都市の並べ方を(N−1)!通りと数える。
function panel({n,count,cities},j){const x0=130+j*480,w=250,h=250,y0=60,at=([u,v])=>[x0+25+u*(w-50),y0+25+v*(h-50)];
 let s=text(x0,40,`都市 ${n}個`,26)+mapFrame(x0,y0,w,h);
 cities.forEach((p,i)=>{const [x,y]=at(p);s+=keyed(`city-${n}-${i}`,i?`<circle cx="${x}" cy="${y}" r="10" fill="${C.B}"/>`:rect(x-12,y-12,24,24,C.accent)+text(x,y+38,'出発',18,C.accent,'middle'));});
 return s+text(x0,375,`(${n}−1)! =`,32,C.muted)+`<text x="${x0+(n<10?140:160)}" y="375" font-size="40" fill="${C.ink}">${count}<tspan dx="10" font-size="24" fill="${C.muted}">通り</tspan></text>`;}
export default {id:'F01',title:'都市数と経路の候補数',steps:['都市数と経路の候補数'],renderStep(){return svg(cases.map(panel).join(''),'都市数と経路の候補数').replace('viewBox="0 0 1100 440"','viewBox="0 0 1100 395"');}};
