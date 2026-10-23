import {test,expect} from '@playwright/test';
import fs from 'node:fs';
const shots='../data/web-e2e/screenshots';fs.mkdirSync(shots,{recursive:true});
async function start(page:any,text:string){await page.getByLabel('What would you like help with today?').fill(text);await page.getByRole('button',{name:'Start',exact:true}).click();await expect(page.getByRole('status').filter({hasText:'Preparing your study activity'})).toHaveCount(0,{timeout:90000});}
test.beforeEach(async({page,request})=>{const response=await request.post('/api/profiles',{data:{name:'Browser fixture '+Date.now()}});const p=await response.json();await page.addInitScript(id=>localStorage.setItem('phss-profile',id),p.id);await page.goto('/');await expect(page.getByRole('heading',{name:'Your learning at a glance'})).toBeVisible();await expect(page.getByRole('status').filter({hasText:'Restoring your workspace'})).toHaveCount(0);await expect(page.getByRole('alert')).toHaveCount(0);});
test('professional landing and responsive layout',async({page})=>{await expect(page.getByLabel('What would you like help with today?')).toBeVisible();await expect(page.getByText('Handling this activity:',{exact:false})).toHaveCount(0);await page.screenshot({path:shots+'/home.png',fullPage:true});await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();await page.screenshot({path:shots+'/mobile.png',fullPage:true});});
test('learning real adaptive assessment recovers after reload',async({page})=>{await start(page,'Teach me recursion');await expect(page.getByText('Handling this activity: Learning Agent')).toBeVisible();await page.getByRole('button',{name:'Start practice',exact:true}).click();await expect(page.getByLabel('Your answer',{exact:true})).toBeVisible();await page.getByLabel('Your answer',{exact:true}).fill('answer');await page.getByRole('button',{name:'Submit answer',exact:true}).click();await expect(page.getByText('Controlled feedback',{exact:false}).first()).toBeVisible({timeout:60000});await page.reload();await page.getByRole('button',{name:'Study workspace',exact:true}).click();await expect(page.getByText('Handling this activity: Learning Agent')).toBeVisible();await expect(page.getByText('Controlled feedback',{exact:false}).first()).toBeVisible();await page.screenshot({path:shots+'/learning.png',fullPage:true});});
test('coding actual exercise Monaco draft hint and reload',async({page})=>{await start(page,'Give me a coding problem on linked lists');await expect(page.getByText('Handling this activity: Coding Agent')).toBeVisible();await expect(page.getByRole('heading',{name:'Read a Serialized Linked List'})).toBeVisible({timeout:90000});await expect(page.locator('.monaco-editor').first()).toBeVisible({timeout:30000});await page.getByRole('button',{name:'Save draft',exact:true}).click();await expect(page.getByText('Draft saved.',{exact:false})).toBeVisible();await page.getByRole('button',{name:'Get next hint',exact:true}).click();await expect(page.locator('.hint')).toHaveCount(1);await page.reload();await page.getByRole('button',{name:'Study workspace',exact:true}).click();await expect(page.locator('.hint')).toHaveCount(1);await page.screenshot({path:shots+'/coding.png',fullPage:true});});
test('research search selects seven papers and retains collection',async({page})=>{await start(page,'Find research papers about agentic AI');await expect(page.getByText('Handling this activity: Research Agent')).toBeVisible();const boxes=page.getByRole('checkbox',{name:/^Select /});await expect(boxes).toHaveCount(7);for(const box of await boxes.all())await box.check();await page.getByRole('button',{name:'Add 7 to collection'}).click();await expect(page.getByRole('checkbox',{name:/^Include /})).toHaveCount(7);await page.reload();await page.getByRole('button',{name:'Study workspace',exact:true}).click();await expect(page.getByRole('checkbox',{name:/^Include /})).toHaveCount(7);await page.screenshot({path:shots+'/research.png',fullPage:true});});
test('multi-step learning then coding stays inline',async({page})=>{await start(page,'Teach me recursion and then give me coding practice');await expect(page.getByText('Handling this activity: Learning Agent')).toBeVisible();await page.getByRole('button',{name:'Continue to next activity'}).click();await expect(page.getByText('Handling this activity: Coding Agent')).toBeVisible();await expect(page.locator('.monaco-editor').first()).toBeVisible({timeout:30000});await page.reload();await page.getByRole('button',{name:'Study workspace',exact:true}).click();await expect(page.getByText('Handling this activity: Coding Agent')).toBeVisible();});
test('PDF upload extraction and valid Word download',async({page,request})=>{await start(page,'Compare my uploaded research papers');await page.getByLabel('Upload research PDFs').setInputFiles('../data/web-e2e/fixture.pdf');await expect(page.getByRole('checkbox',{name:/^Include /})).toHaveCount(1);await page.getByRole('button',{name:'Extract / retry PDF batch'}).click();await expect(page.getByText('ready - 0/2 chunks analyzed')).toBeVisible({timeout:90000});await page.getByRole('button',{name:'Analyze / retry selected batch'}).click();await expect(page.getByText('ready - 2/2 chunks analyzed')).toBeVisible({timeout:60000});const event=page.waitForEvent('download');await page.getByRole('button',{name:'Generate Word report'}).click();const download=await event;await download.saveAs('../data/web-e2e/browser-report.docx');expect(fs.readFileSync('../data/web-e2e/browser-report.docx').subarray(0,2).toString()).toBe('PK');});
test('ambiguous input asks contextual clarification',async({page})=>{await start(page,'Can you improve this?');await expect(page.getByText('Which saved work should we improve, and what would you like to change?')).toBeVisible();await expect(page.getByText('Handling this activity:',{exact:false})).toHaveCount(0);await page.reload();await page.getByRole('button',{name:'Study workspace',exact:true}).click();await expect(page.getByText('Which saved work should we improve, and what would you like to change?')).toBeVisible();});

test('pasted existing code opens standalone review and recovers after refresh',async({page})=>{
 const query='Please check this code and suggest a correction.\n```python\ndef fibonacci(n):\n    return n + 1\n```';
 await start(page,query);
 await expect(page.getByText('Handling this activity: Coding Agent')).toBeVisible();
 await expect(page.getByRole('heading',{name:'Check my code',exact:true})).toBeVisible();
 await expect(page.locator('.coding-grid')).toHaveCount(0);
 await expect(page.locator('.monaco-editor').first()).toBeVisible({timeout:30000});
 await expect(page.getByRole('heading',{name:'Code review feedback'})).toBeVisible();
 await expect(page.getByRole('heading',{name:'Suggested corrected code'})).toBeVisible();
 await expect(page.getByText('No behavioral tests were supplied for this standalone review.',{exact:false})).toBeVisible();
 await page.getByLabel('What should this code do? Include expected input/output if available.').fill('Return the nth Fibonacci number.');
 await page.getByRole('button',{name:'Check my code',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Code review feedback'})).toBeVisible();
 await page.reload();await page.getByRole('button',{name:'Study workspace',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Check my code',exact:true})).toBeVisible();
 await expect(page.getByLabel('What should this code do? Include expected input/output if available.')).toHaveValue('Return the nth Fibonacci number.');
 await expect(page.getByRole('heading',{name:'Suggested corrected code'})).toBeVisible();
 await page.screenshot({path:shots+'/standalone-code-review.png',fullPage:true});
});

test('research report requires actual analysis and recovers ready after refresh',async({page})=>{
 await start(page,'Find research papers about agentic AI');
 const boxes=page.getByRole('checkbox',{name:/^Select /});
 for(const box of (await boxes.all()).slice(0,3))await box.check();
 await page.getByRole('button',{name:'Add 3 to collection'}).click();
 await expect(page.getByRole('button',{name:'Generate Word report'})).toBeDisabled();
 await expect(page.getByText('No selected source has been analyzed.',{exact:false})).toBeVisible();
 await page.getByRole('button',{name:'Prepare next report batch'}).click();
 await expect(page.getByRole('button',{name:'Generate Word report'})).toBeEnabled({timeout:60000});
 await page.getByRole('button',{name:'Select all report sections'}).click();
 await page.reload();await page.getByRole('button',{name:'Study workspace',exact:true}).click();
 await expect(page.getByRole('button',{name:'Generate Word report'})).toBeEnabled();
 const event=page.waitForEvent('download');await page.getByRole('button',{name:'Generate Word report'}).click();
 const download=await event;await download.saveAs('../data/web-e2e/prepared-research-report.docx');
 expect(fs.readFileSync('../data/web-e2e/prepared-research-report.docx').subarray(0,2).toString()).toBe('PK');
 await page.screenshot({path:shots+'/research-report-ready.png',fullPage:true});
});
