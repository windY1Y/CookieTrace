const fs = require('fs');

// 输入文件路径
const inputFile = './output_cookies/vendors_legit_statistics_all_consent.json';
let totalPurposeCount = 0;
try {
  // 读取并解析 JSON 文件
  const data = JSON.parse(fs.readFileSync(inputFile, 'utf8'));

  // 遍历所有 vendor，累加 domainCount
  const totalDomainCount = data.reduce((sum, vendor) => {
    totalVendorCount++;
    return sum + (vendor.domainCount || 0);
  }, 0);

  console.log(`所有 vendor 影响的 domainCount 总和为: ${totalDomainCount}`);
    console.log(`所有 vendor 的数量为: ${totalVendorCount}`);
    console.log(`平均每个 vendor 的 domainCount 为: ${(totalDomainCount / totalVendorCount).toFixed(2)}`);
} catch (err) {
  console.error(`读取或解析文件时出错: ${err.message}`);
}
