const fs = require('fs');
const path = require('path');

const inputFilePath = './output_cookies/detail_vendor_positive_description_purpose.json';
const outputFilePath = './output_cookies/purpose_positive_with_domains.json';

function readJsonFile(filePath) {
  try {
    if (!fs.existsSync(filePath)) {
      throw new Error(`File does not exist`);
    }
    const fileContent = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(fileContent);
  } catch (err) {
    console.error(`Failed to read file ${filePath}:`, err.message);
    process.exit(1);
  }
}

function PurposeStatic(vendorPurposeData) {
  const purposeDomainMap = {};

  vendorPurposeData.forEach(vendorItem => {
    const currentVendorDomains = vendorItem.domains || [];
    const currentVendorPurposes = vendorItem.vendorPurposesDetail?.purposes || [];

    currentVendorPurposes.forEach(purpose => {
      const purposeIdStr = String(purpose.purposeId);
      const purposeName = purpose.purposeName || 'Unknown Purpose Name';
      const purposeDescription = purpose.purposeDescription || 'No Description Available';

      if (!purposeDomainMap[purposeIdStr]) {
        purposeDomainMap[purposeIdStr] = {
          purposeId: purpose.purposeId,
          purposeName: purposeName,
          purposeDescription: purposeDescription,
          domains: new Set()
        };
      }

      currentVendorDomains.forEach(domain => {
        purposeDomainMap[purposeIdStr].domains.add(domain);
      });
    });
  });

  let finalResult = Object.values(purposeDomainMap).map(purposeItem => ({
    purposeId: purposeItem.purposeId,
    purposeName: purposeItem.purposeName,
    purposeDescription: purposeItem.purposeDescription,
    domainCount: purposeItem.domains.size,
    domains: Array.from(purposeItem.domains).sort()
  }));

  finalResult.sort((a, b) => {
    if (b.domainCount !== a.domainCount) {
      return b.domainCount - a.domainCount;
    }
    return a.purposeId - b.purposeId;
  });

  return finalResult;
}

const outputDir = path.dirname(outputFilePath);
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
  console.log(`Created output directory: ${outputDir}`);
}

try {
  const vendorPurposeData = readJsonFile(inputFilePath);
  console.log(`✅ Loaded input with ${vendorPurposeData.length} vendors`);

  const purposeDomainResult = PurposeStatic(vendorPurposeData);
  console.log(`📊 Processed ${purposeDomainResult.length} distinct purpose IDs`);

  fs.writeFileSync(outputFilePath, JSON.stringify(purposeDomainResult, null, 2));
  console.log(`✅ Statistics saved to:${path.resolve(outputFilePath)}`);

  const totalUniqueDomains = purposeDomainResult.reduce((sum, item) => sum + item.domainCount, 0);
  const avgDomainsPerPurpose = purposeDomainResult.length > 0 
    ? (totalUniqueDomains / purposeDomainResult.length).toFixed(2) 
    : "0.00";
  console.log(`\n📈 Summary:`);
  console.log(`   - Total purpose IDs:${purposeDomainResult.length}`);
  console.log(`   - Distinct domains across purposes:${totalUniqueDomains}`);
  console.log(`   - Average domains per purpose:${avgDomainsPerPurpose}`);

  const top3Purpose = purposeDomainResult.slice(0, 3);
  console.log(`\n🏆 Top three purposes by domain count:`);
  top3Purpose.forEach((item, index) => {
    console.log(`   ${index + 1}. Purpose ${item.purposeId} (${item.purposeName}): ${item.domainCount} domains`);
  });

} catch (err) {
  console.error(`❌ Execution failed:`, err.message);
  process.exit(1);
}
