"""
画印尼版示意图用的水面和地面贴图（台数和默认不同时，页面用它们现场画俯视图）。
运行（在仓库根目录）：python3 scripts/make_pond_textures.py assets
"""
import asyncio, base64, sys
from pathlib import Path
from playwright.async_api import async_playwright
out = Path(sys.argv[1])
JS = r"""
() => {
  // value noise
  const P = new Uint8Array(512); let seed = 17;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const perm = Array.from({length:256},(_,i)=>i); for(let i=255;i>0;i--){const j=Math.floor(rnd()*(i+1));[perm[i],perm[j]]=[perm[j],perm[i]];}
  for(let i=0;i<512;i++) P[i]=perm[i&255];
  const G = new Float32Array(256); for(let i=0;i<256;i++) G[i]=rnd();
  const fade=t=>t*t*(3-2*t), lerp=(a,b,t)=>a+(b-a)*t;
  const vn=(x,y)=>{const xi=Math.floor(x),yi=Math.floor(y),xf=x-xi,yf=y-yi,u=fade(xf),v=fade(yf),X=xi&255,Y=yi&255;
    const a=G[P[X+P[Y]]],b=G[P[X+1+P[Y]]],c=G[P[X+P[Y+1]]],d=G[P[X+1+P[Y+1]]];return lerp(lerp(a,b,u),lerp(c,d,u),v);};
  const fbm=(x,y,o=5)=>{let s=0,a=.5,f=1;for(let i=0;i<o;i++){s+=a*vn(x*f,y*f);a*=.5;f*=2.03;}return s;};
  const mix=(a,b,t)=>[lerp(a[0],b[0],t),lerp(a[1],b[1],t),lerp(a[2],b[2],t)];
  const clamp=t=>Math.max(0,Math.min(1,t));
  function paint(W,H,fn,q){
    const c=document.createElement('canvas');c.width=W;c.height=H;const x=c.getContext('2d'),im=x.createImageData(W,H),d=im.data;
    for(let j=0;j<H;j++)for(let i=0;i<W;i++){const v=fn(i,j,W,H),k=(j*W+i)*4;d[k]=v[0];d[k+1]=v[1];d[k+2]=v[2];d[k+3]=255;}
    x.putImageData(im,0,0);return c.toDataURL('image/jpeg',q);
  }
  // Water: green shrimp-pond water, with current lines that run round the middle of the pond.
  const water=paint(720,450,(i,j,W,H)=>{
    const cx=W/2,cy=H/2,dx=(i-cx)/W,dy=(j-cy)/H, rr=Math.sqrt(dx*dx*1.1+dy*dy*1.1);
    const ang=rr*5.5, ca=Math.cos(ang), sa=Math.sin(ang);          // swirl the clouds round the centre
    const ux=(dx*ca-dy*sa)*W, uy=(dx*sa+dy*ca)*H;
    const cloud=fbm(ux*.0065+9,uy*.0065+4,5);
    const warp=fbm(i*.006,j*.006,3)*3.2;
    const th=Math.atan2(dy,dx);
    const line=Math.pow(.5+.5*Math.sin(rr*58-th*2+warp*4.4),10)*clamp((rr-.05)*7);   // bright current lines that spiral, none in the very middle
    const fine=fbm(ux*.03,uy*.03,3);
    const foam=Math.pow(clamp((fbm(ux*.016+30,uy*.016+50,4)-.56)*5),2);
    let col=mix([24,92,92],[76,152,128],clamp((cloud-.28)*2.1));
    col=mix(col,[54,126,120],clamp((fine-.45)*.55));
    col=mix(col,[178,226,208],line*.27*clamp(.2+cloud));
    col=mix(col,[226,244,234],foam*.28);
    const glint=vn(i*.42,j*.42)>.93&&vn(i*.13+5,j*.13)>.55?.3:0;
    return mix(col,[240,250,246],glint);
  },.62);
  // Ground: packed soil with patches of grass round the pond.
  const ground=paint(360,225,(i,j)=>{
    const n=fbm(i*.012+3,j*.012+8,5), f=fbm(i*.11,j*.11,3), g=fbm(i*.02+40,j*.02+11,4);
    let col=mix([150,128,92],[196,174,134],clamp((n-.3)*2));
    col=mix(col,[118,146,78],clamp((g-.5)*4.2));
    return mix(col,[92,78,56],clamp((f-.55)*1.3));
  },.62);
  return {water,ground};
}
"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome")
        pg = await b.new_page()
        r = await pg.evaluate(JS)
        for name in ("water", "ground"):
            data = base64.b64decode(r[name].split(",", 1)[1])
            (out / f"pond-{name}.jpg").write_bytes(data)
            print(name, len(data), "bytes")
        await b.close()
asyncio.run(main())
