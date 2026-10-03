self.onmessage = async function(e) {
  const { seed, difficulty } = e.data;
  
  if (!seed || difficulty === undefined) {
    return;
  }

  const targetPrefix = '0'.repeat(difficulty);
  let nonce = 0;
  const startTime = Date.now();
  const encoder = new TextEncoder();

  while (true) {
    const data = encoder.encode(seed + nonce.toString());
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

    if (hashHex.startsWith(targetPrefix)) {
      const timeSpentMs = Date.now() - startTime;
      self.postMessage({
        type: 'SUCCESS',
        nonce: nonce.toString(),
        hash: hashHex,
        timeSpentMs: timeSpentMs
      });
      break;
    }

    nonce++;
    
    if (nonce % 5000 === 0) {
      self.postMessage({
        type: 'PROGRESS',
        iterations: nonce
      });
      
      // Yield to the event loop occasionally to process other messages if needed,
      // though Web Workers generally run uninterrupted, a small delay isn't strictly necessary 
      // but good practice in long blocking loops if using async.
      await new Promise(resolve => setTimeout(resolve, 0));
    }
  }
};
