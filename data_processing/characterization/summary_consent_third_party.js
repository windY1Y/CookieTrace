const fs = require('fs');
const path = require('path');

// Directories to search
const inputDirs = [
  '../round3/results_consent_part1',
  '../round3/results_consent_part2',
  '../round3/results_consent_part3',
  '../round3/results_consent_part4'
];
const outputFilePath = './consent_cookies_statistics/output_consent_third_source.json'; // Output file path

// Array to store the results
const results = [];

// Function to get cookieHead (part before first number)
function getCookieHead(cookie) {
  // Split cookie at the first occurrence of a number
  const match = cookie.match(/^[^0-9]*/);
  return match ? match[0] : '';
}

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
      const cookieHead = getCookieHead(fileData.cookie.split('=')[0]);
      const key = domain + '+' + cookieHead;
      console.log(`Processing file: ${file}, Domain: ${domain}`);

      // Check if used_scripts contains a script with the domain
      const usedScripts = fileData.used_scripts || [];
      const noEmptyScripts = usedScripts.filter(script => script !== "");
      const matchingScripts = usedScripts.filter(script => script != "" && !containsDomain(script.split('?')[0], domain));

      if (matchingScripts.length > 0 && noEmptyScripts.length == matchingScripts.length) {
        // Collect relevant data
        const result = {
          file: file,
          domain,
          key,
          used_scripts: matchingScripts,
          cookie: fileData.cookie,
          scriptCount: matchingScripts.length
        };
        if(results.length === 0 || !results.some(r => r.key === key)) {
          results.push(result);
        }
      }
    });
    console.log(results.length, 'results found');
    // After processing all files, write the results to the output file
    fs.writeFileSync(outputFilePath, JSON.stringify(results, null, 2));
    console.log(`Processed files and saved results to ${outputFilePath}`);
  });
});
