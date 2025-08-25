const fs = require('fs');

// Load the input data
const inputFilePath = './output_cookies/decode_output_consent.json'; // Path to your input JSON file
const outputFilePath = './output_cookies/count_vendors_purposes_positive.json'; // Path to save the output


// Read the JSON data
const consentData = JSON.parse(fs.readFileSync(inputFilePath, 'utf8'));

// Set to store unique vendor IDs and purpose IDs
const uniqueVendors = new Set();
const uniquePurposes = new Set();
const uniqueVendorPositiveDomains = new Set();
const uniquePurposePositiveDomains = new Set();
// Iterate over the data and extract vendor and purpose IDs
consentData.forEach(item => {
    // Extract vendor and purpose consent details
    const vendorConsents = item.vendorConsentDetails || [];
    const purposeConsents = item.purposeConsentDetails || [];
    if (item.vendorConsentsSize > 0) {
        const domain = item.file.split('_')[0]; // Get domain from the file name (before the first underscore)
        uniqueVendorPositiveDomains.add(domain);
    }
    if (item.purposeConsentsSize > 0) {
        const domain = item.file.split('_')[0]; // Get domain from the file name (before the first underscore)
        uniquePurposePositiveDomains.add(domain);
    }
    // Add the vendor IDs and purpose IDs to the respective sets
    vendorConsents.forEach(vendorId => uniqueVendors.add(vendorId));
    purposeConsents.forEach(purposeId => uniquePurposes.add(purposeId));
});

// Prepare the result to be written to the output file
const result = {
    uniqueVendorPositiveDomainCount: uniqueVendorPositiveDomains.size,
    uniqueVendorPositiveDomains,
    uniquePurposePositiveDomainCount: uniquePurposePositiveDomains.size,
    uniquePurposePositiveDomains,
    uniqueVendorsCount: uniqueVendors.size,
    vendors: Array.from(uniqueVendors),
    uniquePurposesCount: uniquePurposes.size,
    purposes: Array.from(uniquePurposes)
};

// Write the result to the output file
fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2));

console.log(`Count of vendors and purposes saved to ${outputFilePath}`);

