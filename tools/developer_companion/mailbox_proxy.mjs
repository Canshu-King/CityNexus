// DSH's HTTP adapter talks only to this container-local, credential-free proxy.
// There is no network outside the container; the host broker has one fixed route.
import { createServer } from 'node:http';
import { promises as fs } from 'node:fs';
import { randomUUID } from 'node:crypto';

export async function startMailboxProxy(directory, port=19091) {
const maxRequest=8*1024*1024;
const server=createServer(async (req,res) => {
  if(req.method!=='POST'||req.url!=='/v1/chat/completions') {
    res.writeHead(404).end(); return;
  }
  try {
    let size=0; const chunks=[];
    for await(const chunk of req) {
      size+=chunk.length; if(size>maxRequest) throw new Error('REQUEST_TOO_LARGE');
      chunks.push(chunk);
    }
    const id=randomUUID().replaceAll('-','');
    const body=JSON.parse(Buffer.concat(chunks).toString('utf8'));
    // Atomic rename prevents host reads of a partly written request.
    const temp=`${directory}/${id}.tmp`;
    await fs.writeFile(temp,JSON.stringify({method:'POST',path:req.url,body}),{flag:'wx'});
    await fs.rename(temp,`${directory}/req-${id}.json`);
    const deadline=Date.now()+45000;
    while(Date.now()<deadline && !res.destroyed) {
      try {
        const reply=JSON.parse(await fs.readFile(`${directory}/res-${id}.json`,'utf8'));
        res.writeHead(reply.status,{'Content-Type':reply.content_type});
        res.end(Buffer.from(reply.body_base64,'base64')); return;
      } catch(error) {
        if(error.code!=='ENOENT') throw error;
      }
      await new Promise(resolve=>setTimeout(resolve,40));
    }
    res.writeHead(504).end('{"error":{"code":"BROKER_TIMEOUT"}}');
  } catch {
    if(!res.headersSent) res.writeHead(400,{'Content-Type':'application/json'});
    res.end('{"error":{"code":"BROKER_REQUEST_DENIED"}}');
  }
});
await new Promise(resolve=>server.listen(port,'127.0.0.1',resolve));
return server;
}
