import {useEffect,useState} from 'react';
import {LoaderCircle} from 'lucide-react';
export function LoadingStatus({label}:{label:string}){
 const [seconds,setSeconds]=useState(0);
 useEffect(()=>{const started=Date.now();const timer=window.setInterval(()=>setSeconds(Math.floor((Date.now()-started)/1000)),1000);return ()=>window.clearInterval(timer);},[]);
 return <div role="status" className="busy"><LoaderCircle className="spin" size={18}/><div>{label}... {seconds>=3&&<span aria-hidden="true">({seconds}s)</span>}{seconds>=8&&<small style={{display:'block'}}>Still working. Please keep this page open; your saved progress is retained.</small>}</div></div>;
}
