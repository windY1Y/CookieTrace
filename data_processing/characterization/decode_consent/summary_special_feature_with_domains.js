const fs = require('fs');

// 加载输入数据
const inputFilePath = './output_cookies/decode_output_consent.json'; // 输入JSON文件路径
const outputFilePath = './output_cookies/special_feature_all_consent.json'; // 输出文件路径

// 读取JSON数据
const consentData = JSON.parse(fs.readFileSync(inputFilePath, 'utf8'));

// 存储special feature统计数据 (featureId -> 域名列表)
const specialFeatureStats = {};

// 存储specialFeatureSize大于0的域名信息
const domainsWithPositiveSize = {
  count: 0,
  domains: []
};

// 遍历 consent 数据
consentData.forEach(item => {
  // 从文件名中提取域名（第一个下划线之前的部分）
  const domain = item.file.split('_')[0];
  const specialFeatures = item.specialFeatureDetails || [];
  const featureSize = item.specialFeatureSize || 0;
  
  // 如果specialFeatureSize大于0，记录该域名
  if (featureSize > 0) {
    domainsWithPositiveSize.count++;
    if (!domainsWithPositiveSize.domains.includes(domain)) {
      domainsWithPositiveSize.domains.push(domain);
    }
  }
  
  // 统计每个special feature对应的域名
  specialFeatures.forEach(featureId => {
    // 如果该featureId未初始化，则初始化
    if (!specialFeatureStats[featureId]) {
      specialFeatureStats[featureId] = {
        domains: []
      };
    }
    
    // 如果域名不在该featureId的列表中，则添加
    if (!specialFeatureStats[featureId].domains.includes(domain)) {
      specialFeatureStats[featureId].domains.push(domain);
    }
  });
});

// 准备输出结果
const result = {
  // 每个special feature的统计信息
  specialFeatureStatistics: Object.entries(specialFeatureStats).map(([featureId, data]) => ({
    featureId: featureId,
    domainCount: data.domains.length,
    domains: data.domains
  })),
  // specialFeatureSize大于0的域名统计
  positiveSizeDomains: {
    totalCount: domainsWithPositiveSize.count,
    uniqueDomainCount: domainsWithPositiveSize.domains.length,
    domains: domainsWithPositiveSize.domains
  }
};

// 按domainCount降序排序
result.specialFeatureStatistics.sort((a, b) => b.domainCount - a.domainCount);

// 将结果写入输出文件
fs.writeFileSync(outputFilePath, JSON.stringify(result, null, 2));

console.log(`Special feature statistics saved to ${outputFilePath}`);
