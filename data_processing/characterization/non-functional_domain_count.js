const fs = require('fs');
const path = require('path');

// Directories to search
const inputDirs = [
  '../round3/results_non-functional_part1',
  '../round3/results_non-functional_part2',
  '../round3/results_non-functional_part3',
  '../round3/results_non-functional_part4'
];
const outputFilePath = './non-functional_cookies_statistics/unique_non-functional_domains_count.json'; // Output file path

// Set to store unique domains
const uniqueDomains = new Set();
const uniqueCookies = new Set();
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
      let fileData;
      try {
        fileData = JSON.parse(fs.readFileSync(filePath, 'utf8'));
      } catch (err) {
        console.error(`Failed to parse JSON from ${filePath}:`, err);
        return;
      }

      // Extract domain from the file name (before the first underscore)
      const domain = file.split('_')[0];

      // Add domain to the set (duplicates will automatically be ignored)
      uniqueDomains.add(domain);
      console.log(`Processing file: ${filePath}, Domain: ${domain}`);
      // Extract cookieHead and construct a unique key using domain and cookieHead
      const cookieHead = fileData.cookie.split('=')[0];
      console.log(`Processing file: ${filePath}, Domain: ${domain}, Cookie Head: ${cookieHead}`);
      const key = domain + '+' + cookieHead + '+' + fileData.used_scripts.length + '+' + fileData.stack_trace.length;
      if (fileData.used_scripts && fileData.used_scripts.length > 0) {
        uniqueCookies.add(key);
      }
    });

    // After processing all files, write the results to the output file
    const result = {
      uniqueDomainCount: uniqueDomains.size,
      uniqueCookiesCount: uniqueCookies.size,
      cookies: Array.from(uniqueCookies),
      domains: Array.from(uniqueDomains)
    };

    // Write the result to the output file
    fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2));
    console.log(`Processed files and saved results to ${outputFilePath}`);
  });
});
