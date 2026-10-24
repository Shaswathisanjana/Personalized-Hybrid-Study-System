import {test,expect} from '@playwright/test';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
const shots=fileURLToPath(new URL('../../data/web-e2e/screenshots/',import.meta.url));fs.mkdirSync(shots,{recursive:true});
async function start(page:any,text:string){await page.getByLabel('What would you like help with today?').fill(text);await page.getByRole('button',{name:'Start',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'Preparing your study activity'})).toHaveCount(0);}
test('learning quiz labels difficulty and follows current topic across refresh',async({page,request})=>{
 const p=await (await request.post('/api/profiles',{data:{name:'Topic quiz fixture '+Date.now()}})).json();const base='/api/students/'+p.id;
 await page.addInitScript(id=>localStorage.setItem('phss-profile',id),p.id);await page.goto('/');await expect(page.getByRole('status').filter({hasText:'Restoring your workspace'})).toHaveCount(0);
 await start(page,'Teach me recursion');await page.getByRole('button',{name:'Start practice',exact:true}).click();
 await expect(page.getByLabel('Question difficulty')).toHaveText('Difficulty: Easy');
 let s=await (await request.get(base)).json();const old=s.practice.current_question.question_id;
 await page.getByLabel('Your answer',{exact:true}).fill('answer');await page.getByRole('button',{name:'Submit answer',exact:true}).click();
 await expect(page.getByRole('status').filter({hasText:'Evaluating your answer'})).toHaveCount(0);
 s=await (await request.get(base)).json();const difficulty=s.practice.current_question.difficulty;
 await expect(page.getByLabel('Question difficulty')).toHaveText('Difficulty: '+difficulty.charAt(0).toUpperCase()+difficulty.slice(1));
 const resume=s.practice.current_question.question_id;
 await start(page,'Teach me arrays');await expect(page.getByRole('button',{name:'Start practice',exact:true})).toBeVisible();await expect(page.getByText('Evaluation and next steps',{exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'Start practice',exact:true}).click();await expect(page.getByText('Topic: Arrays',{exact:true})).toBeVisible();
 s=await (await request.get(base)).json();expect(s.practice.current_question.concept_name).toBe('Arrays');expect(s.practice.current_question.question_id).not.toBe(old);const arrays=s.practice.current_question.question_id;
 await page.reload();await page.getByRole('button',{name:'Study workspace',exact:true}).click();await expect(page.getByText('Topic: Arrays',{exact:true})).toBeVisible();expect((await (await request.get(base)).json()).practice.current_question.question_id).toBe(arrays);
 await start(page,'Teach me recursion');await expect(page.getByText('Topic: Recursion',{exact:true})).toBeVisible();expect((await (await request.get(base)).json()).practice.current_question.question_id).toBe(resume);
 await page.screenshot({path:shots+'/learning-topic-difficulty.png',fullPage:true});
});
