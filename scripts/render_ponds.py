#!/usr/bin/env python3
"""
渲染印尼版 6 种池塘的 3D 效果图。模型在 scripts/pond_scene.glsl 里（水车、水面、防渗膜、地面），不需要任何外部素材，
用本机显卡在无头 Chrome 里跑 WebGL2。池塘大小、台数、圈层要和 indonesia.html 的 PONDS 一致，改了就重新渲染。

准备：pip install playwright，装好 Chrome
运行（在仓库根目录）：python3 scripts/render_ponds.py assets 960 600 2 0.8
也可以只渲染一种：python3 scripts/render_ponds.py assets 960 600 2 0.8 sqM
"""
import asyncio, base64, json, sys, time
from pathlib import Path
from playwright.async_api import async_playwright
here = Path(__file__).parent
FRAG = (here / "pond_scene.glsl").read_text()
out, W, H, SS, Q = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5])
keys = sys.argv[6:]
PONDS = {
  "round": {"r": 95, "rings": [2]},
  "sqS": {"w": 140, "h": 140, "rings": [4, 2]},
  "sqM": {"w": 165, "h": 165, "rings": [6, 4], "shrink": 0.92},
  "rcM": {"w": 285, "h": 171, "rings": [10, 6]},
  "sqL": {"w": 195, "h": 195, "rings": [10, 6], "shrink": 0.8},
  "rcL": {"w": 320, "h": 196, "rings": [12, 8, 4]},
}
JS = r"""
async ({FRAG,W,H,SS,Q,pond,key}) => {
  const RW=W*SS, RH=H*SS;
  const cv=document.createElement('canvas'); cv.width=RW; cv.height=RH;
  const gl=cv.getContext('webgl2',{preserveDrawingBuffer:true,antialias:false});
  if(!gl) return {error:'no webgl2'};
  const dbg=gl.getExtension('WEBGL_debug_renderer_info');
  const renderer=dbg?gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER);
  const sh=(t,s)=>{const o=gl.createShader(t);gl.shaderSource(o,s);gl.compileShader(o);if(!gl.getShaderParameter(o,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(o));return o;};
  const pr=gl.createProgram();
  gl.attachShader(pr,sh(gl.VERTEX_SHADER,'#version 300 es\nin vec2 a;void main(){gl_Position=vec4(a,0.,1.);}'));
  gl.attachShader(pr,sh(gl.FRAGMENT_SHADER,FRAG));gl.linkProgram(pr);
  if(!gl.getProgramParameter(pr,gl.LINK_STATUS)) return {error:gl.getProgramInfoLog(pr)};
  gl.useProgram(pr);
  const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
  const loc=gl.getAttribLocation(pr,'a');gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,2,gl.FLOAT,false,0,0);
  const U=n=>gl.getUniformLocation(pr,n);

  // same placement as the page: rings from the bank inwards, everything driving the water the same way round
  const round=!!pond.r, w=round?2*pond.r:pond.w, h=round?2*pond.r:pond.h, half=Math.min(w,h)/2, rx=round?pond.r:Math.min(w,h)*0.13;
  const band=(half-6)/(pond.rings.length+.35), list=[];
  function loopPoint(L,d){
    const {x,y,w,h,r}=L, sw=w-2*r, sh=h-2*r, arc=Math.PI*r/2, P=2*sw+2*sh+4*arc; let a; d=((d%P)+P)%P;
    if(d<sw/2) return {x:x+w/2+d,y,a:0}; d-=sw/2;
    if(d<arc){a=d/r;return {x:x+w-r+r*Math.sin(a),y:y+r-r*Math.cos(a),a};} d-=arc;
    if(d<sh) return {x:x+w,y:y+r+d,a:Math.PI/2}; d-=sh;
    if(d<arc){a=d/r;return {x:x+w-r+r*Math.cos(a),y:y+h-r+r*Math.sin(a),a:Math.PI/2+a};} d-=arc;
    if(d<sw) return {x:x+w-r-d,y:y+h,a:Math.PI}; d-=sw;
    if(d<arc){a=d/r;return {x:x+r-r*Math.sin(a),y:y+h-r+r*Math.cos(a),a:Math.PI+a};} d-=arc;
    if(d<sh) return {x,y:y+h-r-d,a:Math.PI*1.5}; d-=sh;
    if(d<arc){a=d/r;return {x:x+r-r*Math.cos(a),y:y+r-r*Math.sin(a),a:Math.PI*1.5+a};} d-=arc;
    return {x:x+r+d,y,a:0};
  }
  pond.rings.forEach((n,i)=>{
    const inset=band*(.6+.93*i), lw=w-2*inset, lh=h-2*inset, L={x:-w/2+inset,y:-h/2+inset,w:lw,h:lh,r:round?lw/2:Math.max(10,Math.min(lw,lh)*.3)};
    const P=2*(lw-2*L.r)+2*(lh-2*L.r)+2*Math.PI*L.r, gap=P/n, size=Math.min(50,band*.86,gap*1.05);
    const shift=(round&&n%2===0)?-P/8:(i>0?(n===2?gap/4:gap/2):0);
    for(let j=0;j<n;j++){const p=loopPoint(L,shift+j*gap);list.push([p.x/10,p.y/10,p.a,(size*(pond.shrink||1)/10)/2.3]);}
  });
  gl.uniform4fv(U('uAer'),new Float32Array(list.flat()));
  gl.uniform1i(U('uCount'),list.length);
  gl.uniform1f(U('uIsRound'),round?1:0);
  gl.uniform2f(U('uHalf'),w/20,h/20);
  gl.uniform1f(U('uCorner'),rx/10);
  gl.uniform2f(U('uRes'),RW,RH);

  // camera: a drone off to one side, high enough to read the rings; pulled back until the pond and its bank just fit
  const norm=v=>{const l=Math.hypot(...v);return v.map(x=>x/l);}, cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]], dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
  const az=-14*Math.PI/180, el=60*Math.PI/180, fov=26*Math.PI/180, focal=1/Math.tan(fov/2), aspect=RW/RH;
  const dir=[Math.sin(az)*Math.cos(el),Math.sin(el),Math.cos(az)*Math.cos(el)];
  const fwd=dir.map(x=>-x), right=norm(cross(fwd,[0,1,0])), up=cross(right,fwd);
  const m=2.45, pts=[]; const hx=w/20+m, hz=h/20+m;
  if(round){for(let i=0;i<40;i++){const a=i/40*6.2832;pts.push([Math.cos(a)*hx,0,Math.sin(a)*hz]);}}
  else pts.push([hx,0,hz],[-hx,0,hz],[hx,0,-hz],[-hx,0,-hz]);
  let dist=10;
  for(;dist<400;dist+=.25){const c=dir.map(x=>x*dist);let ok=true;for(const p of pts){const v=[p[0]-c[0],p[1]-c[1],p[2]-c[2]],z=dot(v,fwd),nx=dot(v,right)*focal/z/aspect,ny=dot(v,up)*focal/z;if(Math.abs(nx)>.98||Math.abs(ny)>.97){ok=false;break;}}if(ok)break;}
  const cam=dir.map(x=>x*dist);
  gl.uniform3fv(U('uCam'),cam);gl.uniform3fv(U('uRight'),right);gl.uniform3fv(U('uUp'),up);gl.uniform3fv(U('uFwd'),fwd);gl.uniform1f(U('uFocal'),focal);

  // draw in small tiles so the graphics driver never times out
  gl.viewport(0,0,RW,RH);gl.enable(gl.SCISSOR_TEST);
  const T=96, px=new Uint8Array(4);
  for(let y=0;y<RH;y+=T){for(let x=0;x<RW;x+=T){gl.scissor(x,y,T,T);gl.drawArrays(gl.TRIANGLES,0,3);gl.readPixels(x,y,1,1,gl.RGBA,gl.UNSIGNED_BYTE,px);}await new Promise(r=>setTimeout(r,0));}
  const out=document.createElement('canvas');out.width=W;out.height=H;const c2=out.getContext('2d');c2.imageSmoothingEnabled=true;c2.imageSmoothingQuality='high';c2.drawImage(cv,0,0,W,H);
  return {renderer,count:list.length,dist,data:out.toDataURL('image/jpeg',Q)};
}
"""
async def main():
    out.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome", args=["--use-angle=metal", "--enable-webgl", "--ignore-gpu-blocklist", "--enable-unsafe-webgpu"])
        pg = await b.new_page()
        pg.on("console", lambda m: print("console:", m.text[:300]))
        pg.on("pageerror", lambda e: print("pageerror:", str(e)[:800]))
        await pg.goto("about:blank")
        for k in (keys or PONDS):
            t = time.time()
            r = await pg.evaluate(JS, {"FRAG": FRAG, "W": W, "H": H, "SS": SS, "Q": Q, "pond": PONDS[k], "key": k})
            if r.get("error"):
                print(k, "ERROR", r["error"][:2000]); continue
            data = base64.b64decode(r["data"].split(",", 1)[1])
            (out / f"scene-{k}.jpg").write_bytes(data)
            print(f"{k}: {len(data)//1024} KB, {r['count']} aerators, {time.time()-t:.1f}s, camera {r['dist']:.1f}, GPU: {r['renderer'][:70]}", flush=True)
        await b.close()
asyncio.run(main())
