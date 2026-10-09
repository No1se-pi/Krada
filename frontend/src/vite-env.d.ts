/// <reference types="vite/client" />
interface Window { WebApp?: { initData: string; ready?: () => void; expand?: () => void; getViewportSize?: () => Promise<{height:string;width:string}> } }
