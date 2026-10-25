import { promises as fs } from 'node:fs';
import { spawn } from 'node:child_process';
import { startMailboxProxy } from './mailbox_proxy.mjs';
await fs.mkdir('/workspace/.developer-companion/runtime',{recursive:true});
const server=await startMailboxProxy('/mailbox');
const child=spawn('node',['/opt/dsh/node_modules/@deepseek-ai/dsh/lib/bin.js','--profile','sdk','--patch','/opt/companion/container_profile.yml'],{
  cwd:'/workspace',stdio:'inherit',env:{
    PATH:process.env.PATH,HOME:'/home/runner',DSH_HOME:'/home/runner/.dsh',
    DSH_TELEMETRY_DISABLED:'1',DSH_PERMISSION_MODE:'workspace-write',
    // Capability token for the local mailbox only; it is NOT an upstream key.
    COMPANION_MAILBOX_TOKEN:'container-local-no-upstream-credential',
    GIT_CONFIG_NOSYSTEM:'1',GIT_CONFIG_GLOBAL:'/dev/null',GIT_TERMINAL_PROMPT:'0',
    GIT_DIR:'/taskgit/worktrees/checkout',GIT_WORK_TREE:'/workspace',
  }
});
child.on('exit',code=>{server.close();process.exit(code??1);});
for(const signal of ['SIGTERM','SIGINT']) process.on(signal,()=>child.kill(signal));
