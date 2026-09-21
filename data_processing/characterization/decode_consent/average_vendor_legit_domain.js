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
let totalDomainCount = 0;
let totalVendorCount = 0;
let totalPurposeCount = 0;
// Iterate through the consent data
consentData.forEach(item => {
  const vendorsLegitSize = item.vendorLegitSize;
  const purposeLegitSize = item.purposeLegitSize;
  const domain = item.file.split('_')[0]; // Get domain from the file name (before the first underscore)
    console.log(`Processing domain: ${domain}, Vendors Legit Size: ${vendorsLegitSize}`);
    totalVendorCount += vendorsLegitSize;
    totalPurposeCount += purposeLegitSize;
  totalDomainCount ++;
});

console.log(`Sum of domainCount: ${totalDomainCount}`);
console.log(`Total vendor count: ${totalVendorCount}`);
console.log(`Average activated vendors per domain: ${(totalVendorCount / totalDomainCount).toFixed(2)}`);
console.log(`Average activated purposes per domain: ${(totalPurposeCount / totalDomainCount).toFixed(2)}`);
