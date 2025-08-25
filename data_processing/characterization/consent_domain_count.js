const fs = require('fs');
const path = require('path');

// Directories to search
const inputDirs = [
  '../round3/results_consent_part1',
  '../round3/results_consent_part2',
  '../round3/results_consent_part3',
  '../round3/results_consent_part4'
];
const outputFilePath = './consent_cookies_statistics/unique_consent_domains_count.json'; // Output file path

// Set to store unique domains
const uniqueDomains = new Set();
const uniqueCookies = new Set();

// Map to store stack_trace length per domain
const stackTraceData = {};

// Function to get cookieHead (part before first number)
function getCookieHead(cookie) {
  // Split cookie at the first occurrence of a number
  const match = cookie.match(/^[^0-9]*/);
  return match ? match[0] : '';
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

      // Extract cookieHead (part before first number)
      const cookieHead = getCookieHead(fileData.cookie.split('=')[0]);
      
      const key = domain + '+' + cookieHead;
      if(key === "quotefancy.com+__cmpconsentx") {
        console.log(`${filePath} due to specific key condition quotefancy.com+__cmpconsentx`);
      }
      uniqueCookies.add(key);

      // Process stack_trace length and add to stackTraceData
      if (fileData.stack_trace && Array.isArray(fileData.stack_trace)) {
        const stackTraceLength = fileData.stack_trace.length;
        if (!stackTraceData[stackTraceLength]) {
          stackTraceData[stackTraceLength] = [];
        }
        stackTraceData[stackTraceLength].push({ fileName: file, domain, cookieHead});
      }
    });

    // After processing all files, write the results to the output file
    const result = {
      uniqueDomainCount: uniqueDomains.size,
      uniqueCookiesCount: uniqueCookies.size,
      cookies: Array.from(uniqueCookies),
      domains: Array.from(uniqueDomains),
      stackTraceData: stackTraceData
    };

    // Write the result to the output file
    fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2));
    console.log(`Processed files and saved results to ${outputFilePath}`);
  });
});
