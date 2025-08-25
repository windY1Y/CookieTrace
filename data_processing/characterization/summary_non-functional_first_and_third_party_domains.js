const fs = require('fs');
const path = require('path');

// Directories to search
const inputDirs = [
  '../round3/results_non-functional_part1',
  '../round3/results_non-functional_part2',
  '../round3/results_non-functional_part3',
  '../round3/results_non-functional_part4'
];
const outputFilePath = './non-functional_cookies_statistics/output_non-functional_first_and_third_source_domains.json'; // Output file path

// Array to store the results
const results = [];

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
      if(fileData.used_scripts.length === 0){
        console.warn(`Warning: No used scripts found in ${filePath}, skipping.`);
        return;
      }
      // Check if used_scripts contains more than one element
      const usedScripts = fileData.used_scripts || [];
      if (usedScripts.length > 1) {
        // Check if at least one script contains a domain and at least one non-empty script does not contain a domain
        const hasDomain = usedScripts.some(script => containsDomain(script.split('?')[0], domain));
        const noDomain = usedScripts.some(script => script !== "" && !containsDomain(script.split('?')[0], domain));

        // If both conditions are met, add the result
        if (hasDomain && noDomain) {
            // Collect relevant data
            const result = {
                file: file,
                key,
                domain,
                used_scripts: usedScripts,
                cookie: fileData.cookie
            };
            if(results.length === 0 || !results.some(r => r.domain === domain)) {
                // Only add if the file is not already in results
                results.push(result);
            }
        }
      }
    });

    // After processing all files, write the results to the output file
    console.log(results.length);
    fs.writeFileSync(outputFilePath, JSON.stringify(results, null, 2));
    console.log(`Processed files and saved results to ${outputFilePath}`);
  });
});
