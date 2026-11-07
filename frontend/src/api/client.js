export async function api(path, {method='GET', data, signal}={}) {
  const options={method,signal};
  if(data instanceof FormData) options.body=data;
  else if(data!==undefined){
    options.headers={'Content-Type':'application/json'};
    options.body=JSON.stringify(data);
  }
  const response=await fetch('/api'+path,options);
  if(!response.ok){
    const payload=await response.json().catch(()=>({}));
    const message=Array.isArray(payload.detail)?payload.detail.map(row=>row.loc.at(-1)+': '+row.msg).join(' · '):payload.detail;
    throw new Error(message || 'Yêu cầu thất bại ('+response.status+')');
  }
  if(response.headers.get('content-type')?.includes('text/event-stream')) return response;
  return response.json();
}

export async function stream(response, onEvent) {
  const reader=response.body.pipeThrough(new TextDecoderStream()).getReader();
  let pending='';
  for(;;){
    const {value,done}=await reader.read();
    if(done) break;
    pending+=value;
    const events=pending.split('\n\n');
    pending=events.pop();
    for(const event of events){
      const [kind,data]=event.split('\n');
      if(kind?.startsWith('event: ') && data?.startsWith('data: '))
        onEvent(kind.slice(7),JSON.parse(data.slice(6)));
    }
  }
}
