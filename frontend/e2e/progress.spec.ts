import {test,expect} from '@playwright/test';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
const shots=fileURLToPath(new URL('../../data/web-e2e/screenshots/',import.meta.url));fs.mkdirSync(shots,{recursive:true});
async function profile(page:any,request:any,assess=false){
 const response=await request.post('/api/profiles',{data:{name:'Progress fixture '+Date.now()}});expect(response.ok()).toBeTruthy();const p=await response.json();const base='/api/students/'+p.id;
 if(assess){expect((await request.post(base+'/query',{data:{text:'Teach me recursion'}})).ok()).toBeTruthy();const practice=await request.post(base+'/practice',{data:{count:1}});const s=await practice.json();expect((await request.post(base+'/answer',{data:{answer:'answer',question_id:s.practice.current_question.question_id}})).ok()).toBeTruthy();}
 await page.addInitScript(id=>localStorage.setItem('phss-profile',id),p.id);await page.goto('/');await expect(page.getByRole('status').filter({hasText:'Restoring your workspace'})).toHaveCount(0);await page.getByRole('button',{name:'My progress',exact:true}).click();await expect(page.getByRole('heading',{name:'Your learning story.'})).toBeVisible();return base;
}
test('progress has an honest empty state and responsive dashboard',async({page,request})=>{
 await profile(page,request);
 await expect(page.locator('.mastery-orbit')).toContainText('Ready to begin');
 await expect(page.locator('.assessment-timeline li')).toHaveCount(0);
 await expect(page.locator('.agent-activity')).toHaveCount(3);
 await page.screenshot({path:shots+'/progress-empty.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();await page.screenshot({path:shots+'/progress-mobile.png',fullPage:true});
});
test('assessed progress uses real evidence filters and collapsed details',async({page,request})=>{
 const base=await profile(page,request,true);const state=await (await request.get(base)).json();
 await expect(page.locator('.agent-activity.learning strong')).toHaveText(String(state.evidence.filter((e:any)=>e.source_agent==='learning').length));
 await expect(page.locator('.assessment-timeline li')).toHaveCount(state.evidence.length);
 await expect(page.locator('.assessment-timeline details').first()).not.toHaveAttribute('open');
 await page.locator('.assessment-timeline summary').first().click();await expect(page.locator('.assessment-timeline details').first()).toHaveAttribute('open','');
 await page.locator('.assessment-timeline summary').first().click();
 await page.getByRole('button',{name:'Practised',exact:true}).click();await expect(page.locator('.progress-topic')).toHaveCount(Object.values(state.student.concepts).filter((c:any)=>c.attempts>0).length);
 await page.getByRole('button',{name:'Not assessed',exact:true}).click();await expect(page.locator('.progress-topic')).toHaveCount(Object.values(state.student.concepts).filter((c:any)=>!c.attempts).length);
 await page.getByRole('button',{name:'All topics',exact:true}).click();await page.screenshot({path:shots+'/progress-desktop.png',fullPage:true});
 await page.reload();await page.getByRole('button',{name:'My progress',exact:true}).click();await expect(page.locator('.assessment-timeline li')).toHaveCount(state.evidence.length);await expect(page.locator('.assessment-timeline details').first()).not.toHaveAttribute('open');
});
