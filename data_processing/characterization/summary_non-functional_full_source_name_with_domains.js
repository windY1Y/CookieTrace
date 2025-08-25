const fs = require('fs');
const path = require('path');


const inputDirs = [
  '../round3/results_non-functional_part1',
  '../round3/results_non-functional_part2',
  '../round3/results_non-functional_part3',
  '../round3/results_non-functional_part4'
];
const outputFilePath = './non-functional_cookies_statistics/source_script_full_name_corresponding_dowain.json'; 


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
      
      if (!scriptStats[script]) {
        scriptStats[script] = {
          script: script,
          domains: new Map(), 
          count: 0
        };
      }

      
      if (!scriptStats[script].domains.has(domain)) {
        scriptStats[script].domains.set(domain, []);
      }

      
      scriptStats[script].domains.get(domain).push(script);
      scriptStats[script].count += 1; 
    });
  });
});


let results = Object.values(scriptStats).map(entry => {
  return {
    script: entry.script,
    domains_count: entry.domains.size, 
    domains: Array.from(entry.domains.entries()).map(([domain, scripts]) => ({
      domain: domain,
      scripts: scripts
    }))
  };
});


results.sort((a, b) => b.domains_count - a.domains_count);


try {
  fs.writeFileSync(outputFilePath, JSON.stringify(results, null, 2));
  console.log(
    `Script statistics generated for ${results.length} unique scripts.\n` +
    `Output saved to ${outputFilePath}`
  );
} catch (err) {
  console.error(`Failed to write output file ${outputFilePath}:`, err);
}
