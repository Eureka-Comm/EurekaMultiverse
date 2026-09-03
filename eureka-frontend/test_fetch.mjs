import { fetch, FormData, File } from 'undici';
import fs from 'fs';

async function run() {
  try {
    const formData = new FormData();
    const fileBuffer = fs.readFileSync('evidence_sample.txt');
    const file = new File([fileBuffer], 'evidence_sample.txt', { type: 'text/plain' });
    formData.append('file', file);

    console.log("Sending request...");
    const res = await fetch('http://localhost:8000/api/evidence', {
      method: 'POST',
      body: formData,
    });
    
    console.log("Status:", res.status);
    const text = await res.text();
    console.log("Response:", text);
  } catch (err) {
    console.error("Fetch Error:", err);
  }
}
run();
