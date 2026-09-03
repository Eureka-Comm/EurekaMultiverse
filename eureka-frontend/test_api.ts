import { CanonicalWorkStateSchema } from './src/domain/canonicalSchema.ts';

async function testApi() {
  const res = await fetch('http://localhost:8000/api/work/intake', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_intent: "Tengo 50,000 pesos y quiero decidir si invertirlos, utilizarlos para vivienda o mantener liquidez." })
  });
  const data = await res.json();
  console.log("Status:", res.status);
  try {
    CanonicalWorkStateSchema.parse(data);
    console.log("PASS: Payload matches schema.");
  } catch (e: any) {
    if (e.errors) {
      console.error("FAIL: Schema validation error:", JSON.stringify(e.errors, null, 2));
    } else {
      console.error("FAIL: Other error", e);
    }
  }
}

testApi();
