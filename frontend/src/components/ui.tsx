import type {ButtonHTMLAttributes,ReactNode} from 'react';
import * as Progress from '@radix-ui/react-progress';
import clsx from 'clsx';
export function Button({className,variant='primary',...props}:ButtonHTMLAttributes<HTMLButtonElement>&{variant?:'primary'|'secondary'|'ghost'}){return <button className={clsx('button',variant,className)} {...props}/>}
export function Card({children,className=''}:{children:ReactNode;className?:string}){return <section className={'card '+className}>{children}</section>}
export function Meter({value,label}:{value:number;label:string}){return <Progress.Root className="meter" value={value} aria-label={label}><Progress.Indicator className="meter-fill" style={{transform:`translateX(-${100-value}%)`}}/></Progress.Root>}
