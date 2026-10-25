import { loadPyodide } from './runtime/pyodide.mjs';

let pyodide;
try {
  pyodide = await loadPyodide({ indexURL: new URL('./runtime/', import.meta.url).href });
  const response = await fetch(new URL('./harness.py', import.meta.url));
  if (!response.ok) throw new Error('Python harness is missing. Download the offline pack again.');
  await pyodide.runPythonAsync(await response.text());
  postMessage({ type: 'ready' });
} catch (error) {
  postMessage({ type: 'engine_error', message: error.message });
}
onmessage = async ({ data }) => {
  if (data.type !== 'run' || !pyodide) return;
  try {
    // JSON is a value, never interpolated into Python source.
    pyodide.globals.set('_payload_json', JSON.stringify(data.payload));
    const result = await pyodide.runPythonAsync('_json.dumps(execute(_json.loads(_payload_json)), allow_nan=False)');
    postMessage({ type: 'result', raw: JSON.parse(result) });
  } catch (error) {
    postMessage({ type: 'engine_error', message: error.message });
  }
};
