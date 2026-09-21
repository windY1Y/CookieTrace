const fs = require('fs');
const path = require('path');

const vendorPositiveStatsPath = './output_cookies/vendors_positive_statistics_all_consent.json';
const vendorListPath = './vendor-list.json';
const outputFilePath = './output_cookies/detail_vendor_positive_description_purpose.json';

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

const vendorPositiveStats = readJsonFile(vendorPositiveStatsPath);
const vendorList = readJsonFile(vendorListPath);

const vendorIdToDetailMap = {};
for (const vendorId in vendorList.vendors) {
  vendorIdToDetailMap[vendorId] = vendorList.vendors[vendorId];
}

const purposeIdToDetailMap = {};
for (const purposeId in vendorList.purposes) {
  purposeIdToDetailMap[purposeId] = vendorList.purposes[purposeId];
}

const result = vendorPositiveStats.map(positiveItem => {
  const vendorId = positiveItem.vendorPositiveId;
  const vendorDetail = vendorIdToDetailMap[vendorId] || null;
  const vendorPurposes = vendorDetail ? vendorDetail.purposes || [] : [];

  const matchedPurposes = vendorPurposes.map(purposeId => {
    const purposeDetail = purposeIdToDetailMap[String(purposeId)] || null;
    return purposeDetail
      ? {
          purposeId: purposeDetail.id,
          purposeName: purposeDetail.name,
          purposeDescription: purposeDetail.description,
          purposeIllustrations: purposeDetail.illustrations || []
        }
      : {
          purposeId: purposeId,
          status: "Unknown Purpose",
          message: `Purpose ${purposeId} was not found in vendor-list.json`
        };
  });

  return {
    vendorPositiveId: vendorId,
    vendorName: positiveItem.vendorName,
    domainCount: positiveItem.domainCount,
    domains: positiveItem.domains,

    vendorBasicInfo: vendorDetail
      ? {
          gvlId: vendorDetail.id,
          fullName: vendorDetail.name,
          usesCookies: vendorDetail.usesCookies,
          cookieMaxAgeSeconds: vendorDetail.cookieMaxAgeSeconds
        }
      : {
          status: "Unknown Vendor",
          message: `Vendor ${vendorId} was not found in vendor-list.json`
        },

    vendorPurposesDetail: {
      totalPurposeCount: matchedPurposes.length,
      purposes: matchedPurposes
    }
  };
});

const outputDir = path.dirname(outputFilePath);
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
  console.log(`Created output directory: ${outputDir}`);
}

try {
  fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2));
  
  const validVendorCount = result.filter(item => item.vendorBasicInfo.status !== "Unknown Vendor").length;
  const totalVendorCount = result.length;
  const avgPurposePerVendor = totalVendorCount > 0 
    ? (result.reduce((sum, item) => sum + item.vendorPurposesDetail.totalPurposeCount, 0) / totalVendorCount).toFixed(2)
    : "0.00";

  console.log(`✅ Results saved to:${path.resolve(outputFilePath)}`);
  console.log(`📊 Summary:`);
  console.log(`   - Total vendors:${totalVendorCount}`);
} catch (err) {
  console.error(`❌ Failed to write output file:`, err.message);
  process.exit(1);
}
