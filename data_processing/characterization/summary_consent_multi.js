const fs = require('fs');
const path = require('path');


const inputDirs = [
  '../round3/results_consent_part1',
  '../round3/results_consent_part2',
  '../round3/results_consent_part3',
  '../round3/results_consent_part4'
];
const outputFilePath = './consent_cookies_statistics/output_consent_multi_source.json';
const results = [];


const outputDir = path.dirname(outputFilePath);
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}


inputDirs.forEach(inputDir => {
  try {
    
    const files = fs.readdirSync(inputDir);
    
    const jsonFiles = files.filter(file => file.endsWith('path.json'));

    console.log(`Processing directory ${inputDir}: ${jsonFiles.length} path.json files`);

    
    jsonFiles.forEach(file => {
      const filePath = path.join(inputDir, file);
      let fileData;

      
      try {
        fileData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
      } catch (parseErr) {
        console.error(`Skipping invalid file ${filePath}: JSON parsing failed`, parseErr.message);
        return;
      }

      
      const domain = file.split('_')[0];
      if (!domain) {
        console.warn(`Skipping file ${file}: cannot extract domain`);
        return;
      }

      
      const usedScripts = Array.isArray(fileData.used_scripts) ? fileData.used_scripts : [];
      
      const nonEmptyScripts = usedScripts.filter(script => typeof script === 'string' && script.trim() !== '');

      
      if (nonEmptyScripts.length > 1) {
        
        const domainExists = results.some(r => r.domain === domain);
        if (!domainExists) {
          const result = {
            file: file,
            domain: domain,
            used_scripts: nonEmptyScripts,
            cookie: fileData.cookie || 'No cookie data', 
            source_dir: inputDir 
          };
          results.push(result);
          console.log(`Adding domain ${domain} from file ${file}`);
        } else {
          console.log(`Skipping duplicate domain ${domain} already in results`);
        }
      } else {
        console.log(`Skipping file ${file}: ${nonEmptyScripts.length} valid scripts (requires >1)`);
      }
    });

  } catch (dirErr) {
    console.error(`Failed to process directory ${inputDir}:`, dirErr.message);
  }
});


fs.writeFileSync(outputFilePath, JSON.stringify(results, null, 2));


console.log(`\n=== Processing complete ===`);
console.log(`Found ${results.length} matching entries`);
console.log(`Results saved to:${path.resolve(outputFilePath)}`);
