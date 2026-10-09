const base = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';
let token = localStorage.getItem('krada-token');

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${base}${path}`, { ...options, headers: {'Content-Type':'application/json', ...(token ? {Authorization:`Bearer ${token}`} : {}), ...options.headers} });
  if (!response.ok) throw new Error((await response.json()).detail?.message ?? 'Сервис временно недоступен');
  return response.json() as Promise<T>;
}
export const api = {
  hasSession: () => Boolean(token),
  login: async (name: string) => { const result = await request<{access_token:string}>('/auth/mock',{method:'POST',body:JSON.stringify({display_name:name})}); token=result.access_token; localStorage.setItem('krada-token',token); },
  loginMax: async (initData: string) => { const result = await request<{access_token:string}>('/auth/max',{method:'POST',body:JSON.stringify({init_data:initData})}); token=result.access_token; localStorage.setItem('krada-token',token); },
  me: () => request<Dashboard>('/me'),
  classes: () => request<GameClass[]>('/character-classes'),
  createCharacter: (name:string,class_key:string) => request('/characters',{method:'POST',body:JSON.stringify({name,class_key})}),
  startRaid: () => request<Raid>('/raids',{method:'POST'}),
  answer: (raidId:string,answer:string) => request<Result>(`/raids/${raidId}/answer`,{method:'POST',headers:{'Idempotency-Key':crypto.randomUUID()},body:JSON.stringify({answer})}),
  logout: () => {token=null;localStorage.removeItem('krada-token');}
};
export type Dashboard={display_name:string;school_name:string;class_name:string;embers:number;school_score:number;character:null|{id:string;name:string;class_key:string;level:number;xp:number;visual_seed:number}};
export type GameClass={key:string;title:string;description:string;stats:Record<string,number>};
export type Raid={id:string;state:string;score:number;question:{id:string;text:string;options:string[];subject:string}};
export type Result={correct:boolean;explanation:string;score:number;xp_awarded:number;embers_awarded:number;embers_balance:number};
