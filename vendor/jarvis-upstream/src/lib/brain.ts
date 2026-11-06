import type { Blade, Panel } from '../store'
export type Msg = { role: 'user' | 'assistant'; content: string }
export type AskHandlers = { onText: (delta: string) => void; onTool: (name: string) => void }
export type ConnectionState = 'connected' | 'connecting' | 'lost' | 'reconnected'
export type CaptureRequest = { mode: 'watch' | 'capture'; when?: 'past' | 'now'; reason?: string; seconds?: number }
export type CaptureResult = { dataUrl?: string; mimeType?: string; error?: string }
export const usingBridge = false
let connected = false
let everConnected = false
let active: AbortController | null = null
const connectionListeners = new Set<(state: ConnectionState) => void>()
const serverListeners = new Set<(servers: string[]) => void>()
function setConnected(value: boolean) {
 const changed = connected !== value
 connected = value
 if (!changed) return
 for (const fn of serverListeners) fn(value ? ['REX AI CORE','OPENROUTER'] : [])
 const state: ConnectionState = value ? (everConnected ? 'reconnected' : 'connected') : 'lost'
 if (value) everConnected = true
 for (const fn of connectionListeners) fn(state)
}
export async function ask(prompt:string,history:Msg[],handlers:AskHandlers):Promise<{text:string;tools:string[]}> {
 active?.abort()
 const controller=new AbortController(); active=controller
 const response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,history:history.slice(-16)}),signal:controller.signal})
 if(!response.ok){const data=await response.json().catch(()=>({})) as {error?:string};throw new Error(data.error||`REX service returned HTTP ${response.status}`)}
 const data=await response.json() as {text?:string};const text=(data.text||'').trim()
 if(!text)throw new Error('REX received an empty response from its AI provider.')
 setConnected(true);handlers.onText(text);return {text,tools:[]}
}
export async function warm():Promise<void>{try{const r=await fetch('/api/health',{cache:'no-store'});setConnected(r.ok)}catch{setConnected(false)}}
export function interrupt():void{active?.abort();active=null}
export function cancel():void{interrupt()}
export function isConnected():boolean{return connected}
export function watchConnection(fn:(state:ConnectionState)=>void):void{connectionListeners.add(fn);fn(connected?'connected':'connecting')}
export function watchServers(fn:(servers:string[])=>void):void{serverListeners.add(fn);fn(connected?['REX AI CORE','OPENROUTER']:[])}
export function watchPanels(_fn:(panel:Panel)=>void):void{}
export function watchBlades(_fn:(blade:Blade)=>void):void{}
export function watchUi(_fn:(op:string,args:unknown)=>void):void{}
export function watchCapture(_fn:(req:CaptureRequest)=>Promise<CaptureResult>):void{}
export function connectedLabels():string[]{return connected?['REX AI CORE','OPENROUTER']:[]}
