const fs = require('fs');

const inputFile = './output_cookies/vendors_legit_statistics_all_consent.json';
let totalPurposeCount = 0;
try {
  const data = JSON.parse(fs.readFileSync(inputFile, 'utf8'));

  const totalDomainCount = data.reduce((sum, vendor) => {
    totalVendorCount++;
    return sum + (vendor.domainCount || 0);
  }, 0);

  console.log(`Sum of domainCount across vendors: ${totalDomainCount}`);
    console.log(`Total vendor count: ${totalVendorCount}`);
    console.log(`Average domainCount per vendor: ${(totalDomainCount / totalVendorCount).toFixed(2)}`);
} catch (err) {
  console.error(`Error reading or parsing file: ${err.message}`);
}
