const fs = require('fs');

const inputFilePath = './output_cookies/decode_output_consent.json';
const outputFilePath = './output_cookies/special_feature_all_consent.json';

const consentData = JSON.parse(fs.readFileSync(inputFilePath, 'utf8'));

const specialFeatureStats = {};

const domainsWithPositiveSize = {
  count: 0,
  domains: []
};

consentData.forEach(item => {
  const domain = item.file.split('_')[0];
  const specialFeatures = item.specialFeatureDetails || [];
  const featureSize = item.specialFeatureSize || 0;
  
  if (featureSize > 0) {
    domainsWithPositiveSize.count++;
    if (!domainsWithPositiveSize.domains.includes(domain)) {
      domainsWithPositiveSize.domains.push(domain);
    }
  }
  
  specialFeatures.forEach(featureId => {
    if (!specialFeatureStats[featureId]) {
      specialFeatureStats[featureId] = {
        domains: []
      };
    }
    
    if (!specialFeatureStats[featureId].domains.includes(domain)) {
      specialFeatureStats[featureId].domains.push(domain);
    }
  });
});

const result = {
  specialFeatureStatistics: Object.entries(specialFeatureStats).map(([featureId, data]) => ({
    featureId: featureId,
    domainCount: data.domains.length,
    domains: data.domains
  })),
  positiveSizeDomains: {
    totalCount: domainsWithPositiveSize.count,
    uniqueDomainCount: domainsWithPositiveSize.domains.length,
    domains: domainsWithPositiveSize.domains
  }
};

result.specialFeatureStatistics.sort((a, b) => b.domainCount - a.domainCount);

fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2));

console.log(`Special feature statistics saved to ${outputFilePath}`);
