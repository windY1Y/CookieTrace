const fs = require('fs');
const path = require('path');

const inputFilePath = './output_cookies/decode_output_consent.json';
const outputFilePath = './output_cookies/multi_legit_all_consent.json';

const consentData = JSON.parse(fs.readFileSync(inputFilePath, 'utf8'));

const qualifiedDomains = new Set();

consentData.forEach(item => {
  const domain = item.file.split('_')[0];
  if (!domain) {
    console.warn(`Warning: Cannot extract a domain from "${item.file}"; skipping entry`);
    return;
  }

  const vendorLegitSize = item.vendorLegitSize || 0;
  const purposeLegitSize = item.purposeLegitSize || 0;

  if (vendorLegitSize > 1 || purposeLegitSize > 1) {
    qualifiedDomains.add(domain);
  }
});

const result = {
  totalQualifiedDomainCount: qualifiedDomains.size,
  qualifiedDomainList: Array.from(qualifiedDomains)
};

const outputDir = path.dirname(outputFilePath);
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
  console.log(`Info: Created output directory "${outputDir}"`);
}

fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2));

console.log('=== Domain filtering complete ===');
console.log(`Matching domain count:${qualifiedDomains.size}`);
console.log(`Deduplicated domain list saved to:${path.resolve(outputFilePath)}`);
