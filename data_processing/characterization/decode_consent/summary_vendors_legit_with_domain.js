const fs = require('fs');

// Load the input data
const inputFilePath = './output_cookies/decode_output_consent.json'; // Path to your input JSON file
const outputFilePath = './output_cookies/vendors_legit_statistics_all_consent.json'; // Path to save the output
const vendorsList = require('../TCF_Vendors_List.json'); // Your JSON file containing vendor details

// Create a mapping of vendor IDs to vendor names
const vendorIdToName = {};
for (const vendorId in vendorsList.vendors) {
  vendorIdToName[vendorId] = vendorsList.vendors[vendorId].name;
}

// Read the JSON data
const consentData = JSON.parse(fs.readFileSync(inputFilePath, 'utf8'));

// Object to store the vendor statistics (vendor ID -> domains list)
const vendorStats = {};

// Iterate through the consent data
consentData.forEach(item => {
  const vendorsLegit = item.vendorLegitDetails || [];
  const domain = item.file.split('_')[0]; // Get domain from the file name (before the first underscore)
  console.log(`Processing domain: ${domain}, Vendors Legit: ${vendorsLegit}`);
  // Find vendors in legit but not in consent
  vendorsLegit.forEach(vendorId => {
    // Initialize the vendor if not already in the stats
    if (!vendorStats[vendorId]) {
      vendorStats[vendorId] = { name: vendorIdToName[vendorId] || 'Unknown Vendor', domains: [] };
    }
    // Add the domain to the vendor's domain list if it's not already there
    if (!vendorStats[vendorId].domains.includes(domain)) {
      vendorStats[vendorId].domains.push(domain);
    }
  });
});

// Prepare the result to be written to the output file
const result = Object.entries(vendorStats).map(([vendorId, data]) => ({
  vendorId,
  vendorName: data.name,
  domainCount: data.domains.length,
  domains: data.domains
}));
console.log("number of vendors in legit: ", result.length);
// Sort the result by domainCount in descending order
result.sort((a, b) => b.domainCount - a.domainCount);

// Write the result to the output file
fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2));

console.log(`Vendor statistics saved to ${outputFilePath}`);
