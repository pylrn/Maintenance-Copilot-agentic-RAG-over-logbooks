"""Original, synthesized ambient score. No sampled or third-party music."""
from pathlib import Path
import wave
import numpy as np
root=Path(__file__).resolve().parents[1]
rate=44100; duration=48; count=rate*duration
score=np.zeros(count,dtype=np.float32)
rng=np.random.default_rng(42)
chords=[[146.83,174.61,220.0],[130.81,164.81,196.0],[116.54,146.83,174.61],[130.81,174.61,220.0]]
for start in np.arange(0,duration,5.3333333):
 length=min(6.1,duration-start);t=np.arange(int(length*rate),dtype=np.float32)/rate
 envelope=np.minimum(t/1.1,1)*np.minimum((length-t)/1.4,1)
 tone=np.zeros_like(t)
 for f in chords[int(start/5.3333333)%4]:
  tone+=.025*np.sin(2*np.pi*f*t)+.009*np.sin(2*np.pi*(f*1.002)*t)+.004*np.sin(2*np.pi*f*2*t)
 i=int(start*rate);score[i:i+len(t)]+=tone*envelope
beat=60/108
for i,start in enumerate(np.arange(0,duration,beat)):
 n=min(int(.3*rate),count-int(start*rate));t=np.arange(n,dtype=np.float32)/rate
 kick=.095*np.sin(2*np.pi*(47*t+30*.034*(1-np.exp(-t/.034))))*np.exp(-t*23)
 if i%2: kick*=.45
 pos=int(start*rate);score[pos:pos+n]+=kick
 if i%2:
  noise=rng.normal(0,1,n).astype(np.float32);noise=np.concatenate([[0],np.diff(noise)])
  score[pos:pos+n]+=.009*noise*np.exp(-t*65)
 if i%4==2:
  f=[440,523.25,587.33,659.25][(i//4)%4]
  score[pos:pos+n]+=.022*np.sin(2*np.pi*f*t)*np.exp(-t*9)*np.minimum(t/.008,1)
for start in [5,10,16,22,27,32,38,43]:
 n=int(.5*rate);t=np.arange(n,dtype=np.float32)/rate
 sweep=.023*np.sin(2*np.pi*(550*t+650*t*t))*np.sin(np.pi*t/.5)**2
 pos=int((start-.23)*rate);score[pos:pos+n]+=sweep
score*=.32/max(float(np.max(np.abs(score))),.32)
left=score;right=.96*score+.04*np.roll(score,333)
stereo=np.column_stack([left,right]);pcm=(np.clip(stereo,-1,1)*32767).astype('<i2')
output=root/'.video-build/soundtrack.wav'
with wave.open(str(output),'wb') as out:
 out.setnchannels(2);out.setsampwidth(2);out.setframerate(rate);out.writeframes(pcm.tobytes())
print(f'Original soundtrack: {duration}s, stereo, {rate}Hz')
