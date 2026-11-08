import {api} from '../api/client.js';

const messages = {
  ready: 'Sẵn sàng',
  speaking: 'Đang đặt câu hỏi',
  listening: 'Đang nghe bạn',
  thinking: 'Đang xử lý',
  finished: 'Đã kết thúc',
};

export const interviewer = `<aside class="interviewer" data-state="ready" aria-label="Người phỏng vấn ảo">
  <svg class="interviewer-art" viewBox="0 0 320 300" aria-hidden="true">
    <defs>
      <linearGradient id="interview-suit" x2="1" y2="1"><stop stop-color="#2f5f9e"/><stop offset="1" stop-color="#16396b"/></linearGradient>
      <linearGradient id="interview-skin" x2="0" y2="1"><stop stop-color="#fac6a6"/><stop offset="1" stop-color="#e99b80"/></linearGradient>
    </defs>
    <circle cx="160" cy="135" r="100" fill="#d6e6fb"/>
    <circle cx="160" cy="135" r="91" fill="none" stroke="#f2f7ff" stroke-width="2"/>
    <path d="M81 257v-37q0-42 36-42h87q36 0 36 42v37" fill="#a9c4e8" stroke="#8fb0dd" stroke-width="3"/>
    <path d="M108 176Q92 118 111 79q16-34 53-32 40 2 51 39 10 34-3 91z" fill="#252f3d"/>
    <path d="M72 255q8-45 37-54l25-10h53l27 11q29 9 37 53" fill="url(#interview-suit)"/>
    <path d="M142 175v25q18 23 37 0v-25" fill="#de8d76"/>
    <path d="M128 196l32 51 32-51-14-8q-18 22-36 0z" fill="#f5eee2"/>
    <path d="M125 198l-13 11 19 12-5 10 34 16m37-49 13 11-19 12 5 10-36 16" fill="none" stroke="#7f9fd0" stroke-width="1.5"/>
    <ellipse cx="110" cy="134" rx="10" ry="15" fill="#e89f85"/>
    <ellipse cx="210" cy="134" rx="10" ry="15" fill="#e89f85"/>
    <path d="M112 103q0-46 48-46t48 46v34q-2 53-48 58-46-5-48-58z" fill="url(#interview-skin)"/>
    <path d="M106 114q-8-62 45-67 52-5 65 46l-4 26q-11-7-17-29-35 18-72 6l-11 22z" fill="#252f3d"/>
    <path d="M115 90q13-34 50-33 23 1 34 16-36 13-77 17" fill="#38455a"/>
    <path d="M126 119q9-6 18-2m32 0q10-4 18 2" fill="none" stroke="#704a43" stroke-width="2.6" stroke-linecap="round"/>
    <g class="interviewer-eyes" fill="#242e3c"><ellipse cx="137" cy="130" rx="3.6" ry="4.5"/><ellipse cx="184" cy="130" rx="3.6" ry="4.5"/></g>
    <path d="m160 133-3 14 6 1" fill="none" stroke="#c78472" stroke-width="2" stroke-linecap="round"/>
    <ellipse cx="125" cy="145" rx="8" ry="4" fill="#d98978" opacity=".4"/>
    <ellipse cx="195" cy="145" rx="8" ry="4" fill="#d98978" opacity=".4"/>
    <path class="interviewer-smile" d="M150 161q10 7 21 0" fill="none" stroke="#984f52" stroke-width="2.4" stroke-linecap="round"/>
    <ellipse class="interviewer-mouth" cx="160" cy="162" rx="9" ry="8" fill="#783b43"/>
    <circle cx="111" cy="148" r="3" fill="#e8c578"/><circle cx="209" cy="148" r="3" fill="#e8c578"/>
    <path d="M106 227q-5 18 4 28m103-28q7 18-3 28" fill="none" stroke="#17355f" stroke-width="2"/>
    <rect x="39" y="252" width="242" height="10" rx="5" fill="#b78e69"/>
    <path d="M53 262h214v15H53z" fill="#dbc1a1"/>
    <rect x="218" y="229" width="28" height="23" rx="5" fill="#f3ebd9"/>
    <path d="M246 233h5q8 0 6 6-1 5-11 5" fill="none" stroke="#f3ebd9" stroke-width="3"/>
  </svg>
  <div class="interviewer-label"><strong>AI Interviewer</strong><span class="interviewer-status" role="status">Sẵn sàng</span></div>
  <div class="interviewer-dots" aria-hidden="true"><i></i><i></i><i></i></div>
</aside>`;

export function interviewMedia(avatar, {endpoint, mode, signal, onTranscript, onError, onState}) {
  let state = 'ready', speech, recognition, recorder, stream, timer, audio, source, analyser, frame, playback = 0;
  const status = avatar.querySelector('.interviewer-status');
  function set(next, label = messages[next]) {
    state = next;
    avatar.dataset.state = next;
    status.textContent = label;
    onState(next);
  }
  function stopSpeech() {
    playback++;
    cancelAnimationFrame(frame);
    if (speech) window.speechSynthesis.cancel();
    speech = null;
    if (source) {
      source.onended = null;
      source.stop();
      source.disconnect();
      source = null;
    }
    analyser?.disconnect();
    analyser = null;
    avatar.classList.remove('has-audio');
    avatar.style.removeProperty('--mouth');
  }
  function finishSpeech(id) {
    if (id !== playback || signal.aborted) return;
    stopSpeech();
    set('ready');
  }
  function sayInBrowser(text, id) {
    if (!window.speechSynthesis || !window.SpeechSynthesisUtterance) throw new Error('Trình duyệt chưa hỗ trợ đọc câu hỏi.');
    speech = new SpeechSynthesisUtterance(text);
    speech.lang = 'vi-VN';
    speech.onstart = () => { if (id === playback) set('speaking'); };
    speech.onend = () => finishSpeech(id);
    speech.onerror = event => {
      if (id !== playback) return;
      finishSpeech(id);
      if (!['canceled', 'interrupted', 'not-allowed'].includes(event.error)) onError('Không phát được giọng đọc.');
    };
    window.speechSynthesis.speak(speech);
  }
  async function play(text) {
    if (!text || signal.aborted || ['listening','thinking'].includes(state)) return;
    stopSpeech();
    const id = playback;
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (mode === 'openai' && AudioContext) {
      try {
        audio ||= new AudioContext();
        if (audio.state === 'suspended') {
          // Attempt resume during a user gesture and retain the browser voice fallback.
          await Promise.race([audio.resume(), new Promise(resolve => setTimeout(resolve, 350))]);
        }
        if (audio.state !== 'running') throw new Error('AudioContext suspended');
        if (id !== playback || signal.aborted) return;
        set('thinking', 'Đang chuẩn bị giọng đọc');
        const response = await fetch('/api'+endpoint+'/speech', {signal, cache:'no-store'});
        if (!response.ok) throw new Error('TTS unavailable');
        const buffer = await audio.decodeAudioData(await response.arrayBuffer());
        if (id !== playback || signal.aborted) return;
        analyser = audio.createAnalyser();
        analyser.fftSize = 256;
        source = audio.createBufferSource();
        source.buffer = buffer;
        source.connect(analyser);
        analyser.connect(audio.destination);
        const data = new Uint8Array(analyser.fftSize);
        const draw = () => {
          analyser.getByteTimeDomainData(data);
          const rms = Math.sqrt(data.reduce((sum, value) => sum + ((value-128)/128)**2, 0)/data.length);
          avatar.style.setProperty('--mouth', Math.min(1, 0.12+rms*5));
          frame = requestAnimationFrame(draw);
        };
        source.onended = () => finishSpeech(id);
        source.start();
        avatar.classList.add('has-audio');
        set('speaking');
        draw();
        return;
      } catch {
        if (id !== playback || signal.aborted) return;
      }
    }
    try {
      set('ready');
      sayInBrowser(text,id);
    } catch(error) {onError(error.message);}
  }
  function releaseMic() {
    clearTimeout(timer);
    stream?.getTracks().forEach(track => track.stop());
    stream = null;
  }
  async function transcribe(data) {
    if (signal.aborted) return;
    set('thinking', 'Đang chuyển âm thanh thành văn bản');
    try {
      const result = await api(endpoint+'/transcribe', {method:'POST',data,signal});
      if (!signal.aborted) onTranscript(result.transcript);
    } finally {
      if (!signal.aborted) set('ready');
    }
  }
  async function record() {
    if (!confirm('Cho phép gửi bản ghi câu trả lời tới dịch vụ nhận diện giọng nói OpenAI?')) return;
    set('thinking', 'Đang mở micro');
    try {
      stream = await navigator.mediaDevices.getUserMedia({audio:true});
      if (signal.aborted) { releaseMic(); return; }
      const chunks = [];
      let size = 0;
      const maximum = 8*1024*1024;
      recorder = new MediaRecorder(stream);
      recorder.ondataavailable = event => {
        if (event.data.size) chunks.push(event.data);
        size += event.data.size;
        if (size > maximum && recorder?.state === 'recording') recorder.stop();
      };
      recorder.onstop = async () => {
        const type = (recorder?.mimeType || chunks[0]?.type || 'audio/webm').split(';')[0];
        recorder = null;
        releaseMic();
        if (signal.aborted) return;
        if (!size || size > maximum) {
          set('ready');
          onError(size ? 'Bản ghi vượt 8 MB. Hãy thử lại ngắn hơn.' : 'Micro chưa thu được âm thanh.');
          return;
        }
        const data = new FormData();
        data.append('file',new Blob(chunks,{type}),'answer.'+(type.split('/')[1] || 'webm'));
        data.append('consent','true');
        try { await transcribe(data); } catch(error) { if (!signal.aborted) onError(error.message); }
      };
      recorder.onerror = () => {
        recorder.onstop = null;
        recorder = null;
        releaseMic();
        if (!signal.aborted) {set('ready');onError('Không ghi được âm thanh.');}
      };
      recorder.start(1000);
      timer = setTimeout(() => {if (recorder?.state === 'recording') recorder.stop();},120000);
      set('listening');
    } catch {
      releaseMic();
      if (!signal.aborted) {set('ready');onError('Không mở được micro. Bạn vẫn có thể nhập câu trả lời.');}
    }
  }
  function recognize() {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) {onError('Trình duyệt chưa hỗ trợ nhận giọng nói. Bạn có thể nhập chữ.');return;}
    if (!confirm('Cho phép trình duyệt nhận giọng nói? Dịch vụ nhận diện phụ thuộc trình duyệt.')) return;
    recognition = new Recognition();
    recognition.lang = 'vi-VN';
    recognition.continuous = true;
    recognition.onresult = event => {
      const text = Array.from(event.results).filter(result=>result.isFinal).map(result=>result[0].transcript).join(' ');
      if (text && !signal.aborted) onTranscript(text);
    };
    recognition.onend = () => {recognition = null;if (!signal.aborted) set('ready');};
    recognition.onerror = event => {
      if (!signal.aborted && event.error !== 'aborted') onError('Không nhận được giọng nói. Hãy thử lại hoặc nhập chữ.');
    };
    try {recognition.start();set('listening');}
    catch {recognition=null;onError('Không mở được micro.');}
  }
  async function listen() {
    if (signal.aborted || state === 'thinking') return;
    if (recorder?.state === 'recording') {recorder.stop();return;}
    if (recognition) {recognition.stop();return;}
    stopSpeech();
    set('ready');
    if (mode === 'openai' && navigator.mediaDevices?.getUserMedia && window.MediaRecorder) await record();
    else recognize();
  }
  function dispose() {
    stopSpeech();
    if (recorder?.state === 'recording') recorder.stop();
    if (recognition) recognition.abort();
    releaseMic();
    if (audio && audio.state !== 'closed') audio.close().catch(()=>{});
  }
  signal.addEventListener('abort',dispose,{once:true});
  return {play,listen,transcribe,stopSpeech,set};
}
