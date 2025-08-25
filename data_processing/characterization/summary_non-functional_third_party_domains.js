const fs = require('fs');
const path = require('path');

// Directories to search
const inputDirs = [
  '../round3/results_non-functional_part1',
  '../round3/results_non-functional_part2',
  '../round3/results_non-functional_part3',
  '../round3/results_non-functional_part4'
];
const outputFilePath = './non-functional_cookies_statistics/output_non-functional_third_source_with_domains.json'; // Output file path
const duplicateOutputFilePath = './non-functional_debug/duplicate_domains.json'; // Output file path for duplicates

// Array to store the results
const results = [];
const duplicateResults = [];

// Function to check if a script contains a domain
function containsDomain(script, domain) {
  return script.includes(domain);
}

// Function to read all path.json files and process them
inputDirs.forEach(inputDir => {
  // Read all files in the directory
  fs.readdir(inputDir, (err, files) => {
    if (err) {
      console.error(`Failed to read directory ${inputDir}:`, err);
      return;
    }

    // Filter for all path.json files
    const jsonFiles = files.filter(file => file.endsWith('path.json'));

    // Process each file
    jsonFiles.forEach((file) => {
      const filePath = path.join(inputDir, file);
      const fileData = JSON.parse(fs.readFileSync(filePath, 'utf8'));

      // Extract the domain from the file name (before the first underscore)
      const domain = file.split('_')[0];
      const cookieHead = fileData.cookie.split('=')[0];
      const key = domain + '+' + cookieHead + '+' + fileData.used_scripts.length + '+' + fileData.stack_trace.length;
      console.log(`Processing file: ${file}, Domain: ${domain}`);

      // Check if used_scripts contains a script with the domain
      const usedScripts = fileData.used_scripts || [];
      const noEmptyScripts = usedScripts.filter(script => script !== "");
      const matchingScripts = usedScripts.filter(script => script != "" && !containsDomain(script.split('?')[0], domain));
      if(fileData.used_scripts.length === 0){
        console.warn(`Warning: No used scripts found in ${filePath}, skipping.`);
        return;
      }
      if (matchingScripts.length > 0 && noEmptyScripts.length == matchingScripts.length) {
        // Collect relevant data
        const result = {
          file: file,
          key,
          domain,
          used_scripts: matchingScripts,
          cookie: fileData.cookie,
          scriptCount: matchingScripts.length
        };
        if (results.length === 0 || !results.some(r => r.domain === domain)) {
          // Only add if the file is not already in results
          results.push(result);
        }
      }
    });

    // After processing all files, check for duplicate domains
    console.log(results.length);
    const seenDomains = new Set();
    results.forEach(result => {
      if (seenDomains.has(result.domain)) {
        // If the domain is already seen, add it to duplicateResults
        duplicateResults.push(result);
      } else {
        seenDomains.add(result.domain);
      }
    });

    // Check for results with the same domain and collect them for output
    const duplicateDomainsResults = [];
    const domainCountMap = {};

    results.forEach(result => {
      const domain = result.domain;
      if (!domainCountMap[domain]) {
        domainCountMap[domain] = [];
      }
      domainCountMap[domain].push(result);
    });

    // Filter for domains with more than one result
    for (const domain in domainCountMap) {
      if (domainCountMap[domain].length > 1) {
        duplicateDomainsResults.push(...domainCountMap[domain]);
      }
    }

    // Write the results to the output file
    fs.writeFileSync(outputFilePath, JSON.stringify(results, null, 2));
    console.log(`Processed files and saved results to ${outputFilePath}`);

    // Write the duplicate domain results to another file
    fs.writeFileSync(duplicateOutputFilePath, JSON.stringify(duplicateDomainsResults, null, 2));
    console.log(`Processed duplicate domain results and saved to ${duplicateOutputFilePath}`);
  });
});
