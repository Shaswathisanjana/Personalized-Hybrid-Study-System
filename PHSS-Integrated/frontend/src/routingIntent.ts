// Initial navigation mirrors explicit research routing; backend remains authoritative.
export function isResearchRequest(message:string):boolean {
 const q=message.trim().toLowerCase();
 if(/^(?:please\s+)?(?:explain|teach|help me understand|what is|what are)\b/.test(q)&&! /\b(find|search|retrieve)\b.*\b(papers?|literature)\b/.test(q))return false;
 return /\bresearch\s+(?:on|about|into)\b|\b(?:find|search|retrieve|review|summarize)\b.*\b(?:papers?|literature|studies)\b|\b(?:literature review|systematic review|research gaps?|survey papers?|recent papers?|latest papers?)\b/.test(q);
}
