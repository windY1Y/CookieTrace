const fs = require('fs');

// Load the JSON data
const decodeOutputConsent = require('./output_cookies/decode_output_consent.json'); // Your JSON file

// Function to get statistics for each cmpId
function getCmpIdDomainStats(decodeOutputConsent) {
  // Create an object to store domain counts per cmpId
  let cmpIdStats = {};

  // Loop through decodeOutputConsent data
  decodeOutputConsent.forEach(entry => {
    const cmpId = entry.cmpId; // Extract cmpId
    const domain = entry.file.split('_')[0]; // Get domain from the file name (before the first underscore)

    // Initialize the cmpId entry if not present
    if (!cmpIdStats[cmpId]) {
      cmpIdStats[cmpId] = {
        domainCount: 0,
        domains: new Set(),
      };
    }

    // Add domain to the corresponding cmpId
    cmpIdStats[cmpId].domains.add(domain);
    cmpIdStats[cmpId].domainCount = cmpIdStats[cmpId].domains.size;
  });

  // Now, format the result into an output structure
  let output = [];
  for (let cmpId in cmpIdStats) {
    output.push({
      cmpId: cmpId,
      domainCount: cmpIdStats[cmpId].domainCount,
      domains: Array.from(cmpIdStats[cmpId].domains)
    });
  }

  // Sort the output array by domainCount in descending order
  output.sort((a, b) => b.domainCount - a.domainCount);

  // Save the output to a file
  fs.writeFileSync('./output_cookies/output_cmpId.json', JSON.stringify(output, null, 2));
  console.log("Output saved to output_cmpId.json");
}

// Call the function
getCmpIdDomainStats(decodeOutputConsent);
