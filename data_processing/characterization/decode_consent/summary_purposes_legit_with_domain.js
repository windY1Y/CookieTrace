const fs = require('fs');

// Load the input data
const inputFilePath = './output_cookies/decode_output_consent.json'; // Path to your input JSON file
const outputFilePath = './output_cookies/purposes_legit_statistics_all_consent.json'; // Path to save the output
const purposesList = require('../TCF_Purpose.json'); // Your JSON file containing purpose IDs and their descriptions
// Read the JSON data
const consentData = JSON.parse(fs.readFileSync(inputFilePath, 'utf8'));

// Object to store the purpose statistics (purpose ID -> domains list)
const purposeStats = {};

// Iterate through the consent data
consentData.forEach(item => {
  const purposesLegit = item.purposeLegitDetails || [];
  const domain = item.file.split('_')[0]; // Get domain from the file name (before the first underscore)
  
  // Find purposes in legit but not in consent
  purposesLegit.forEach(purposeId => {
    // Initialize the purpose if not already in the stats
    if (!purposeStats[purposeId]) {
      purposeStats[purposeId] = {
          purposeName: purposesList[purposeId] ? purposesList[purposeId].purpose : 'Unknown Purpose',
          domains: [] 
      };
    }
    // Add the domain to the purpose's domain list if it's not already there
    if (!purposeStats[purposeId].domains.includes(domain)) {
      purposeStats[purposeId].domains.push(domain);
    }
  });
});

// Prepare the result to be written to the output file
const result = Object.entries(purposeStats).map(([purposeId, data]) => ({
  purposeId,
  purposeName: data.purposeName,
  domainCount: data.domains.length,
  domains: data.domains
}));

// Sort the result by domainCount in descending order
result.sort((a, b) => b.domainCount - a.domainCount);

// Write the result to the output file
fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2));

console.log(`Purpose statistics saved to ${outputFilePath}`);
