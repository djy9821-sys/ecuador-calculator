#version 300 es
precision highp float;
out vec4 fragColor;
uniform vec2 uRes;
uniform vec3 uCam, uRight, uUp, uFwd;
uniform float uFocal, uIsRound, uCorner;
uniform vec2 uHalf;
uniform int uCount;
uniform vec4 uAer[32];   // x, z, flow angle (rad), scale

const vec3 SUN = normalize(vec3(-0.58, 0.70, 0.40));
const float BANK = 1.55, RIM = 0.75, GROUND = 0.95;

float hash(vec2 p){ vec3 q=fract(vec3(p.xyx)*0.1031); q+=dot(q,q.yzx+33.33); return fract((q.x+q.y)*q.z); }
float vnoise(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.-2.*f);
  return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y); }
const mat2 ROT = mat2(1.62,1.18,-1.18,1.62);
float fbm3(vec2 p){ float s=0.,a=.5; for(int i=0;i<3;i++){ s+=a*vnoise(p); p=ROT*p; a*=.5; } return s; }
float fbm5(vec2 p){ float s=0.,a=.5; for(int i=0;i<5;i++){ s+=a*vnoise(p); p=ROT*p; a*=.5; } return s; }

float sdPond(vec2 p){
  if(uIsRound>.5) return length(p)-uHalf.x;
  vec2 q=abs(p)-uHalf+uCorner;
  return length(max(q,0.))+min(max(q.x,q.y),0.)-uCorner;
}
float terrain(vec2 p){
  float d=sdPond(p);
  float h=-0.7+(GROUND+0.7)*smoothstep(0.,BANK,d);
  float far=smoothstep(BANK+RIM,BANK+RIM+1.6,d);
  return h+far*((fbm5(p*.42)-.5)*.42+(fbm3(p*3.1)-.5)*.05);
}

float gPhase=0.;
vec2 opU(vec2 a, vec2 b){ return a.x<b.x?a:b; }
float sdBox(vec3 p, vec3 b){ vec3 q=abs(p)-b; return length(max(q,0.))+min(max(q.x,max(q.y,q.z)),0.); }
float sdRBox(vec3 p, vec3 b, float r){ return sdBox(p,b-r)-r; }
float sdCylZ(vec3 p, float r, float h){ vec2 d=abs(vec2(length(p.xy),p.z))-vec2(r,h); return min(max(d.x,d.y),0.)+length(max(d,0.)); }
float sdCylY(vec3 p, float r, float h){ vec2 d=abs(vec2(length(p.xz),p.y))-vec2(r,h); return min(max(d.x,d.y),0.)+length(max(d,0.)); }

// The aerator in its own coordinates: x along the flow, y up, z along the shaft. Materials: 1 float, 2 paddle, 3 steel, 4 motor, 5 black.
vec2 aerator(vec3 q){
  q.z=abs(q.z);
  vec3 fl=q-vec3(0.,.12,.43);
  fl.y+=.10*smoothstep(.5,.9,abs(fl.x));                 // floats rise a little at the ends
  vec2 r=vec2(sdRBox(fl,vec3(.86,.15,.205),.085),1.);
  r=opU(r,vec2(sdBox(vec3(abs(q.x)-.36,q.y-.31,q.z),vec3(.024,.018,.62)),3.));
  r=opU(r,vec2(sdBox(vec3(q.x,q.y-.31,q.z-.42),vec3(.40,.018,.024)),3.));
  r=opU(r,vec2(sdCylZ(q-vec3(0.,.47,0.),.032,1.22),3.));
  r=opU(r,vec2(sdBox(q-vec3(0.,.39,.68),vec3(.06,.10,.035)),5.));
  vec3 w=q-vec3(0.,.47,1.);
  r=opU(r,vec2(sdCylZ(w,.10,.20),2.));
  float a=atan(w.y,w.x)+gPhase, sec=6.2832/8.; a=mod(a+sec*.5,sec)-sec*.5;
  float rad=length(w.xy);
  vec3 pw=vec3(rad*cos(a),rad*sin(a),w.z);
  r=opU(r,vec2(sdBox(vec3(pw.x-.25,pw.y,abs(pw.z)-.12),vec3(.17,.014,.018)),2.));  // two spokes per blade
  r=opU(r,vec2(sdBox(pw-vec3(.43,0.,0.),vec3(.135,.016,.215)),2.));                // wide blade
  r=opU(r,vec2(sdCylZ(q-vec3(0.,.47,0.),.25,.07),3.));
  r=opU(r,vec2(sdCylZ(q-vec3(0.,.47,.11),.055,.05),3.));
  r=opU(r,vec2(sdBox(q-vec3(0.,.285,0.),vec3(.15,.05,.11)),3.));
  r=opU(r,vec2(sdCylY(q-vec3(0.,.83,0.),.175,.12),4.));
  r=opU(r,vec2(sdCylY(q-vec3(0.,.71,0.),.10,.05),3.));
  r=opU(r,vec2(sdCylY(q-vec3(0.,.99,0.),.085,.05),5.));
  return r;
}
vec2 mapAer(vec3 p){
  vec2 res=vec2(1e5,0.);
  for(int i=0;i<uCount;i++){
    vec4 a=uAer[i]; vec3 rel=p-vec3(a.x,0.,a.y);
    float dc=length(rel)-a.w*1.5;
    if(dc>.5){ if(dc<res.x) res=vec2(dc,0.); continue; }
    float c=cos(a.z), s=sin(a.z);
    vec3 q=vec3(c*rel.x+s*rel.z,rel.y,-s*rel.x+c*rel.z)/a.w;
    gPhase=float(i)*.37+step(0.,q.z)*.21;
    vec2 r=aerator(q); r.x*=a.w;
    res=opU(res,r);
  }
  return res;
}
vec3 aerNormal(vec3 p){
  vec2 e=vec2(.004,0.);
  return normalize(vec3(mapAer(p+e.xyy).x-mapAer(p-e.xyy).x,mapAer(p+e.yxy).x-mapAer(p-e.yxy).x,mapAer(p+e.yyx).x-mapAer(p-e.yyx).x));
}
float aerTop(){ float m=0.; for(int i=0;i<uCount;i++) m=max(m,uAer[i].w); return m*1.2; }
float marchAer(vec3 ro, vec3 rd, float t0, float t1, out float id){
  float t=t0; id=-1.;
  for(int i=0;i<110;i++){
    vec2 h=mapAer(ro+rd*t);
    if(h.x<.0025){ if(h.y>0.){ id=h.y; return t; } }
    t+=max(h.x,.0025);
    if(t>t1) break;
  }
  return -1.;
}
float softShadow(vec3 ro){
  float res=1., t=.04;
  for(int i=0;i<26;i++){
    float h=mapAer(ro+SUN*t).x;
    res=min(res,9.*h/t);
    t+=clamp(h,.03,.5);
    if(res<.01||t>7.) break;
  }
  return clamp(res,0.,1.);
}
vec3 sky(vec3 d){
  float y=max(d.y,0.);
  vec3 c=mix(vec3(.88,.92,.96),vec3(.36,.56,.86),pow(y,.55));
  float cloud=smoothstep(.45,.8,fbm5(d.xz/(d.y+.25)*1.4));
  c=mix(c,vec3(1.,1.,1.),cloud*.55);
  return c;
}
vec3 shadeAer(vec3 p, vec3 rd, float id){
  vec3 n=aerNormal(p);
  vec3 alb=vec3(.015,.15,.70); float spec=.28, gloss=40., metal=0.;
  if(id<1.5){ }
  else if(id<2.5){ alb=vec3(.95,.62,.015); spec=.18; gloss=30.; }
  else if(id<3.5){ alb=vec3(.50,.52,.54); spec=.7; gloss=70.; metal=.55; }
  else if(id<4.5){ alb=vec3(.58,.60,.62); spec=.9; gloss=120.; metal=.8; }
  else { alb=vec3(.02,.022,.025); spec=.35; gloss=60.; }
  float sh=softShadow(p+n*.02);
  float dif=max(dot(n,SUN),0.)*sh;
  float amb=.42+.38*n.y;
  vec3 r=reflect(rd,n);
  vec3 col=alb*(vec3(1.25,1.18,1.05)*dif+vec3(.42,.5,.62)*amb);
  col=mix(col,(sky(r)*.72+.06)*alb*(.45+.55*sh),metal);
  float fr=.04+.96*pow(1.-max(dot(-rd,n),0.),5.);
  col+=sky(r)*fr*(metal>0.?.08:.4);
  col+=vec3(1.)*spec*pow(max(dot(r,SUN),0.),gloss)*sh;
  col*=mix(.6,1.,smoothstep(0.,.32,p.y));      // darker where it meets the water
  return col;
}
// Foam thrown ahead of each paddle wheel, in water coordinates.
float wake(vec2 p, out float near){
  float f=0.; near=1e5;
  for(int i=0;i<uCount;i++){
    vec4 a=uAer[i]; vec2 rel=p-a.xy;
    float dd=length(rel); near=min(near,dd/a.w);
    if(dd>a.w*7.) continue;
    float c=cos(a.z), s=sin(a.z);
    vec2 q=vec2(c*rel.x+s*rel.y,-s*rel.x+c*rel.y)/a.w;
    float zz=abs(q.y)-.97;
    float wid=.17+.075*max(q.x,0.);
    float along=smoothstep(-.42,.02,q.x)*exp(-max(q.x,0.)/1.9);
    f=max(f,exp(-zz*zz/(wid*wid))*along);
  }
  return f;
}
float waterH(vec2 p, float turb){
  return fbm3(p*1.9+3.)*.05+fbm3(p*6.2)*.018+turb*fbm3(p*13.)*.06;
}
vec3 shadeWater(vec3 p, vec3 rd){
  float near; float w=wake(p.xz,near);
  float e=.015;
  float h0=waterH(p.xz,w);
  vec3 n=normalize(vec3(h0-waterH(p.xz+vec2(e,0.),w),e,h0-waterH(p.xz+vec2(0.,e),w)));
  float big=max(uHalf.x,uHalf.y);
  vec2 u=p.xz/big;
  float rr=length(u*vec2(.85,1.15)), th=atan(u.y,u.x);
  float warp=fbm5(p.xz*.32+7.);
  float lines=pow(.5+.5*sin(rr*15.-th*2.+warp*9.),3.)*smoothstep(.08,.4,rr)*smoothstep(.34,.66,fbm5(p.xz*.55+vec2(5.,1.)));
  float algae=fbm5(p.xz*.26+vec2(9.,4.));
  vec3 body=mix(vec3(.010,.062,.046),vec3(.034,.135,.088),smoothstep(.30,.74,algae));
  body=mix(body,vec3(.075,.205,.145),lines*.34);
  float edge=sdPond(p.xz);
  body*=mix(.55,1.,smoothstep(0.,1.1,-edge));
  float sh=softShadow(p+vec3(0.,.02,0.));
  float dif=.55+.55*max(dot(n,SUN),0.);
  vec3 col=body*dif*(vec3(1.05,1.02,.95)*mix(.5,1.,sh)+.12);
  float dA=mapAer(p+vec3(0.,.03,0.)).x;
  col*=mix(.62,1.,smoothstep(0.,.55,dA));          // contact shade under the floats
  vec3 r=reflect(rd,n); r.y=abs(r.y);
  float fr=.025+.975*pow(1.-max(dot(-rd,n),0.),5.);
  vec3 refl=sky(r);
  float idR; float tR=marchAer(p+n*.01,r,.02,9.,idR);
  float mirror=0.;
  if(tR>0.){ refl=shadeAer(p+r*tR,r,idR); mirror=.3; }
  col=mix(col,refl,clamp(fr*.9+mirror,0.,1.));
  col+=vec3(1.,.97,.9)*pow(max(dot(r,SUN),0.),520.)*5.*sh;
  // foam
  float tex=fbm5(p.xz*3.4+vec2(2.,5.))*.72+fbm3(p.xz*11.)*.28;
  float foam=smoothstep(.34,.60,tex+w*.62-.24)*clamp(w*1.5,0.,1.);
  foam+=smoothstep(.56,.74,tex)*lines*.07;
  col=mix(col,vec3(.93,.96,.95)*mix(.62,1.08,sh),clamp(foam,0.,.96));
  return col;
}
vec3 terrainN(vec2 p){
  float e=.02, h=terrain(p);
  return normalize(vec3(h-terrain(p+vec2(e,0.)),e,h-terrain(p+vec2(0.,e))));
}
vec3 shadeTerrain(vec3 p, vec3 rd){
  float d=sdPond(p.xz);
  vec3 n=terrainN(p.xz);
  vec3 col;
  if(d<BANK){
    // black liner on the slope, with soft folds
    float along=fbm3(p.xz*vec2(1.5,1.5)+11.);
    float fold=fbm3(p.xz*4.)*.5+along*.5;
    vec3 m=normalize(n+vec3((fold-.5)*.35,0.,(along-.5)*.35));
    vec3 r=reflect(rd,m);
    float fr=.05+.95*pow(1.-max(dot(-rd,m),0.),5.);
    col=vec3(.012,.014,.014)*(.5+1.5*max(dot(m,SUN),0.));
    col+=sky(r)*fr*.16+vec3(.9)*pow(max(dot(r,SUN),0.),50.)*.10;
    col*=mix(.75,1.,smoothstep(0.,.5,d));
  }else if(d<BANK+RIM){
    // packed path along the top of the bank
    float g=fbm5(p.xz*6.);
    col=mix(vec3(.21,.18,.135),vec3(.38,.33,.25),g);
    col*=.62+.62*max(dot(n,SUN),0.);
    col*=mix(.75,1.,smoothstep(0.,.14,d-BANK));
  }else{
    float n1=fbm5(p.xz*.55+3.), n2=fbm5(p.xz*.16+8.), fine=fbm5(p.xz*7.), blade=fbm3(p.xz*24.), mid=fbm5(p.xz*1.9+2.);
    vec3 soil=mix(vec3(.17,.125,.085),vec3(.30,.235,.160),smoothstep(.25,.7,n1));
    soil*=.78+.5*fine;
    float grass=smoothstep(.36,.70,n2+(mid-.5)*.55);
    vec3 g=mix(vec3(.050,.092,.030),vec3(.125,.180,.060),blade*.6+mid*.4);
    g*=.7+.55*fine;
    col=mix(soil,g,grass*smoothstep(0.,.8,d-BANK-RIM));
    col*=.56+.72*max(dot(n,SUN),0.);
  }
  return col;
}
vec3 tone(vec3 x){ x*=1.02; return clamp((x*(2.51*x+.03))/(x*(2.43*x+.59)+.14),0.,1.); }

void main(){
  vec2 uv=(2.*gl_FragCoord.xy-uRes)/uRes.y;
  vec3 rd=normalize(uv.x*uRight+uv.y*uUp+uFocal*uFwd), ro=uCam;
  float tW=-ro.y/rd.y;                  // water level y=0
  float top=aerTop();
  float t0=(top-ro.y)/rd.y;
  // terrain first: step down from just above the ground
  float tT=-1.;
  {
    float t=(GROUND+.5-ro.y)/rd.y, dt=(tW-t)/64.;
    float prev=0.;
    for(int i=0;i<65;i++){
      vec3 p=ro+rd*t;
      float h=p.y-terrain(p.xz);
      if(h<0.){ float a=t-dt, b=t; for(int k=0;k<7;k++){ float m=.5*(a+b); vec3 q=ro+rd*m; if(q.y-terrain(q.xz)<0.) b=m; else a=m; } tT=b; break; }
      t+=dt;
    }
  }
  float tEnd=tT>0.?min(tT,tW):tW;
  float id; float tA=marchAer(ro,rd,t0,tEnd,id);
  vec3 col;
  if(tA>0.) col=shadeAer(ro+rd*tA,rd,id);
  else if(tT>0.&&tT<tW) col=shadeTerrain(ro+rd*tT,rd);
  else col=shadeWater(ro+rd*tW,rd);
  float v=length(uv*vec2(.62,.8));
  col*=1.-.16*v*v;
  col=tone(col);
  fragColor=vec4(pow(col,vec3(1./2.2)),1.);
}
