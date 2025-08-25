const fs = require('fs');
const path = require('path');


const inputDirs = [
  '../round3/results_consent_part1',
  '../round3/results_consent_part2',
  '../round3/results_consent_part3',
  '../round3/results_consent_part4'
]; 
const outputFilePath = './consent_cookies_statistics/detail_consent_source_script_corresponding_dowain_update.json'; 

const scriptStats = Object.create(null);


inputDirs.forEach(dir => {
  const dirPath = path.resolve(__dirname, dir);
  if (!fs.existsSync(dirPath)) {
    console.warn(`Warning: directory ${dirPath} does not exist, skipping.`);
    return;
  }

  const entries = fs.readdirSync(dirPath);
  entries.forEach(file => {
    if (!file.endsWith('path.json')) {
      return;
    }
    const filePath = path.join(dirPath, file);
    let fileData;
    try {
      fileData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    } catch (err) {
      console.error(`Failed to parse JSON from ${filePath}:`, err);
      return;
    }

    
    const domain = file.split('_')[0];

    
    const usedScripts = Array.isArray(fileData.used_scripts)
      ? fileData.used_scripts.filter(s => s && typeof s === 'string' && s.trim() !== '')
      : [];

    
    usedScripts.forEach(script => {
      
      let scriptPrefix = script.split('?')[0]; 

      
      if (scriptPrefix.startsWith("https:
        scriptPrefix = "https:
      }
      else if (scriptPrefix.startsWith('https:
        scriptPrefix = "https:
      }

      
      if (!scriptStats[scriptPrefix]) {
        scriptStats[scriptPrefix] = {
          script: scriptPrefix,
          domains: new Map(), 
          count: 0
        };
      }

      
      if (!scriptStats[scriptPrefix].domains.has(domain)) {
        scriptStats[scriptPrefix].domains.set(domain, new Set()); 
      }

      
      const domainScripts = scriptStats[scriptPrefix].domains.get(domain);

      
      if (!domainScripts.has(script)) {
        domainScripts.add(script);
        scriptStats[scriptPrefix].count += 1; 
      }
    });
  });
});


let results = Object.values(scriptStats).map(entry => {
  return {
    script: entry.script,
    domains_count: entry.domains.size, 
    domains: Array.from(entry.domains.entries()).map(([domain, scripts]) => ({
      domain: domain,
      scripts: Array.from(scripts) 
    }))
  };
});


results.sort((a, b) => b.domains_count - a.domains_count);


fs.writeFileSync(outputFilePath, JSON.stringify(results, null, 2));
console.log(
  `Script statistics generated for ${results.length} unique scripts.\n` +
  `Output saved to ${outputFilePath}`
);
