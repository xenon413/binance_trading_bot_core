import io, math, struct, wave, winsound
import math
import struct
import wave
import winsound

class Alarm:
    def __init__(self, frq:int=880, dur_ms:int=300, vol:float=0.2, rate:int=44100):
        self._frq = frq
        self._dur_ms = dur_ms
        self._vol = vol
        self._rate = rate
        self._if_on = False
        self._thread = None

    def tone(self):
        n = int(self._dur_ms/1000*self._rate)
        # 16-bit PCM
        frames = bytearray()
        for i in range(n):
            s = self._vol * math.sin(2*math.pi*self._frq*i/self._rate)
            val = max(-1.0, min(1.0, s))
            frames += struct.pack('<h', int(val * 32767))
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self._rate)
            w.writeframes(frames)
        winsound.PlaySound(buf.getvalue(), winsound.SND_MEMORY)

if __name__ == "__main__":
    while True:
        Alarm().tone()