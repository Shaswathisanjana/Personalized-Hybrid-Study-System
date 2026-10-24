import {test,expect} from '@playwright/test';
test('learning and coding skip research downloads while research still loads and recovers',async({page,request})=>{
 const p=await (await request.post('/api/profiles',{data:{name:'Loading fixture '+Date.now()}})).json();await page.addInitScript(id=>localStorage.setItem('phss-profile',id),p.id);
 const researchRequests:string[]=[];page.on('request',req=>{if(req.method()==='GET'&&new URL(req.url()).pathname.endsWith('/research'))researchRequests.push(req.url());});
 await page.goto('/');await expect(page.getByRole('status').filter({hasText:'Restoring your workspace'})).toHaveCount(0);
 async function start(text:string){await page.getByLabel('What would you like help with today?').fill(text);await page.getByRole('button',{name:'Start',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'Preparing your study activity'})).toHaveCount(0);}
 await start('Teach me recursion');await expect(page.getByText('Handling this activity: Learning Agent')).toBeVisible();
 await page.reload();await expect(page.getByRole('status').filter({hasText:'Restoring your workspace'})).toHaveCount(0);
 expect(researchRequests).toHaveLength(0);
 await start('Give me a coding problem on Arrays');await expect(page.getByRole('button',{name:'Submit & evaluate',exact:true})).toBeVisible();expect(researchRequests).toHaveLength(0);
 await start('Find research papers about agentic AI');await expect(page.getByRole('checkbox',{name:/^Select /})).toHaveCount(7);expect(researchRequests).toHaveLength(1);
 await page.reload();await page.getByRole('button',{name:'Study workspace',exact:true}).click();await expect(page.getByRole('checkbox',{name:/^Select /})).toHaveCount(7);expect(researchRequests).toHaveLength(2);
});
