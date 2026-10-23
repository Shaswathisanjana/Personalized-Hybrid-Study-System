import Editor,{loader} from '@monaco-editor/react';
import * as monaco from 'monaco-editor/editor/editor.api.js';
import editorWorker from 'monaco-editor/editor/editor.worker.js?worker';
import {language,conf} from 'monaco-editor/languages/definitions/python/python.js';
monaco.languages.register({id:'python'});
monaco.languages.setMonarchTokensProvider('python',language);
monaco.languages.setLanguageConfiguration('python',conf);
self.MonacoEnvironment={getWorker(){return new editorWorker()}};
loader.config({monaco});
export default function CodeEditor({value,onChange}:{value:string;onChange:(v:string)=>void}){return <Editor height="430px" language="python" theme="vs-dark" value={value} onChange={v=>onChange(v||'')} options={{minimap:{enabled:false},fontSize:14,padding:{top:20},scrollBeyondLastLine:false,automaticLayout:true,tabSize:4}}/>}
