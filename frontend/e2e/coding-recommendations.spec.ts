import {test,expect} from '@playwright/test';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
const shots=fileURLToPath(new URL('../../data/web-e2e/screenshots/',import.meta.url));

test('evaluated coding leads to actual next practice and recovers after refresh',async({page,request})=>{
 const p=await (await request.post('/api/profiles',{data:{name:'Next practice fixture '+Date.now()}})).json();const base='/api/students/'+p.id;
 await page.addInitScript(id=>localStorage.setItem('phss-profile',id),p.id);await page.goto('/');
 await expect(page.getByRole('status').filter({hasText:'Restoring your workspace'})).toHaveCount(0);
 await page.getByLabel('What would you like help with today?').fill('Give me a coding problem on Arrays');await page.getByRole('button',{name:'Start',exact:true}).click();
 await expect(page.locator('.monaco-editor')).toBeVisible({timeout:30000});
 await expect(page.getByRole('heading',{name:'Practise this next',exact:true})).toHaveCount(0);
 const code='def find_max(nums):\n    largest = nums[0]\n    for value in nums[1:]:\n        if value > largest:\n            largest = value\n    return largest\n';
 await page.context().grantPermissions(['clipboard-read','clipboard-write']);await page.evaluate(value=>navigator.clipboard.writeText(value),code);
 await page.getByRole('textbox',{name:'Editor content',exact:true}).focus();await page.keyboard.press('Control+A');await page.keyboard.press('Control+V');
 await page.getByRole('button',{name:'Submit & evaluate',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Practise this next',exact:true})).toBeVisible({timeout:60000});
 const assessed=await (await request.get(base)).json();expect(assessed.code).toBe(code);expect(assessed.evidence.length).toBe(1);
 expect(assessed.coding_recommendation.passed_tests).toBe(assessed.coding_recommendation.total_tests);
 await page.reload();await page.getByRole('button',{name:'Study workspace',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Practise this next',exact:true})).toBeVisible();
 fs.mkdirSync(shots,{recursive:true});await page.evaluate(()=>document.fonts.ready);await expect(page.locator('.monaco-editor')).toBeVisible();await page.screenshot({path:shots+'coding-recommendation-card.png',fullPage:true});
 await page.getByRole('button',{name:'Start recommended practice',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Practice focus',exact:true})).toBeVisible();
 const next=await (await request.get(base)).json();expect(next.exercise.task.title).not.toBe(assessed.exercise.task.title);
 expect(next.exercise.task.difficulty).toBe(assessed.coding_recommendation.difficulty);expect(next.student).toEqual(assessed.student);expect(next.evidence).toEqual(assessed.evidence);
 expect(next.coding_saved_drafts.arrays.code).toBe(code);expect(next.coding_result).toBeNull();
 await page.reload();await page.getByRole('button',{name:'Study workspace',exact:true}).click();await expect(page.getByRole('heading',{name:'Practice focus',exact:true})).toBeVisible();
 const restored=await (await request.get(base)).json();expect(restored.exercise).toEqual(next.exercise);expect(restored.coding_practice_focus).toEqual(next.coding_practice_focus);
 await expect(page.locator('.monaco-editor')).toBeVisible();await page.evaluate(()=>document.fonts.ready);await page.screenshot({path:shots+'coding-next-practice.png',fullPage:true});
});


test('typed next problem continues assessed coding instead of resetting it',async({page,request})=>{
 const p=await (await request.post('/api/profiles',{data:{name:'Typed coding follow-up '+Date.now()}})).json();const base='/api/students/'+p.id;
 await request.post(base+'/query',{data:{text:'Give me a coding problem on Arrays'}});
 const code='def find_max(nums):\n    largest = nums[0]\n    for value in nums[1:]:\n        if value > largest:\n            largest = value\n    return largest\n';
 const response=await request.post(base+'/code',{data:{code}});expect(response.ok()).toBeTruthy();const assessed=await response.json();
 await page.addInitScript(id=>localStorage.setItem('phss-profile',id),p.id);await page.goto('/');
 await expect(page.getByRole('status').filter({hasText:'Restoring your workspace'})).toHaveCount(0);await page.getByRole('button',{name:'Study workspace',exact:true}).click();
 await page.getByLabel('What would you like help with today?').fill('Give me the next problem');await page.getByRole('button',{name:'Start',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Practice focus',exact:true})).toBeVisible();
 const next=await (await request.get(base)).json();expect(next.exercise.task.title).not.toBe(assessed.exercise.task.title);expect(next.plan.request_id).toBe(assessed.plan.request_id);expect(next.evidence).toEqual(assessed.evidence);
 await page.getByRole('button',{name:'Start',exact:true}).click();await expect(page.locator('.error-banner[role=alert]')).toContainText('Submit and evaluate');
 expect((await (await request.get(base)).json()).exercise).toEqual(next.exercise);
});

test('an incorrect submission clearly offers revision of the same exercise',async({page,request})=>{
 const p=await (await request.post('/api/profiles',{data:{name:'Coding revision label '+Date.now()}})).json();const base='/api/students/'+p.id;
 const prepared=await (await request.post(base+'/query',{data:{text:'Give me a coding problem on Arrays'}})).json();
 const assessment=await request.post(base+'/code',{data:{code:prepared.exercise.task.starter_code}});expect(assessment.ok()).toBeTruthy();
 await page.addInitScript(id=>localStorage.setItem('phss-profile',id),p.id);await page.goto('/');await expect(page.getByRole('status').filter({hasText:'Restoring your workspace'})).toHaveCount(0);await page.getByRole('button',{name:'Study workspace',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Revise this exercise',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Start recommended practice',exact:true})).toHaveCount(0);
 await page.getByRole('button',{name:'Revise this exercise',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Practice focus',exact:true})).toBeVisible();
 const restored=await (await request.get(base)).json();expect(restored.exercise).toEqual(prepared.exercise);expect(restored.evidence.length).toBe(1);
});
